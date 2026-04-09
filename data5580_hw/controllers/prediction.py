import logging

from flask import jsonify, request
from pydantic import ValidationError

from sqlalchemy.exc import IntegrityError

from data5580_hw.services.database.database_client import db
from data5580_hw.gateways.mlflow_gateway import mlflow_gateway
from data5580_hw.gateways.arize_gateway import arize_gateway
from data5580_hw.services.database.user_model import UserSQL
from data5580_hw.models.user import User

from data5580_hw.models.prediction import Prediction, Model
from data5580_hw.services.model_service import model_service
from data5580_hw.services.umap_service import umap_embedding_service
from data5580_hw.services.explainer_service import explainer_service
from data5580_hw.services.database.prediction import PredictionSQL, ModelSql, ExplanationSql


logger = logging.getLogger(__name__)


def _should_log_arize_request() -> bool:
    """Honor ?arize_log=false or X-Arize-Log: false when global Arize is enabled."""
    if request.args.get("arize_log", "true").lower() in ("0", "false", "no"):
        return False
    if request.headers.get("X-Arize-Log", "").lower() in ("0", "false", "no"):
        return False
    return True


class PredictionController:

    @staticmethod
    def create_prediction(model_name: str, model_version: str) -> tuple[str, int]:

        # Load model
        try:
            model: Model = mlflow_gateway.get_model(model_name, model_version)
        except KeyError:
            return (
                jsonify(
                    {
                        "error": f"Model '{model_name}' version '{model_version}' not found."
                    }
                ),
                404,
            )

        # Parse and validate input payload
        try:
            data = request.get_json(force=True) or {}
            prediction = Prediction.model_validate(data)
        except ValidationError as e:
            return (
                jsonify(
                    {
                        "error": "Invalid input data.",
                        "details": [err.get("msg") for err in e.errors()],
                    }
                ),
                400,
            )

        prediction.model = model

        # Create prediction (regression)
        try:
            label = model_service.create_inference(model, prediction=prediction)
        except ValueError as e:
            return jsonify({"error": f"Invalid input data: {str(e)}"}), 400
        except Exception:
            logger.exception("Error during prediction")
            return jsonify({"error": "Internal error during prediction."}), 500

        prediction.label = label
        # Create UMAP embeddings only when the service can fit/transform safely.
        try:
            inputs_df = prediction.get_pandas_frame_of_inputs()
            X = inputs_df.to_numpy(dtype=float)
            prediction.embeddings = umap_embedding_service.compute_embeddings(
                X, umap_params=prediction.umap_params
            )
        except Exception:
            logger.exception("UMAP embedding calculation failed")
            prediction.embeddings = None
        

        # Create explanation
        if prediction.model._explainer:
            explanations = explainer_service.create_explanation(model, prediction=prediction)
            prediction.explanations = explanations

        # Create database objects and store
        model_sql = ModelSql.from_model(model)
        prediction_sql = PredictionSQL.from_prediction(prediction, model_sql)

        if prediction.explanations:
            explanations_sql = ExplanationSql.from_prediction(prediction)
            db.session.add_all(explanations_sql)

        db.session.add(prediction_sql)
        db.session.commit()

        # Read from database and return
        prediction_sql: PredictionSQL = db.session.query(PredictionSQL).filter(PredictionSQL.id == prediction.id).first()
        prediction = prediction_sql.to_prediction()

        if _should_log_arize_request() and prediction.model:
            arize_gateway.log_inference(prediction.model, prediction)

        return jsonify(prediction.model_dump()), 200

    @staticmethod
    def get_prediction_by_id(prediction_id: str) -> tuple[str, int]:

        logger.debug(f'Got prediction_id {prediction_id}')

        prediction_sql: PredictionSQL = db.session.query(PredictionSQL).filter(PredictionSQL.id == prediction_id).first()

        prediction = prediction_sql.to_prediction()

        return jsonify(prediction.model_dump()), 200

    # NOTE: This project originally contained stub methods for additional
    # features (e.g., updating actual values). They were accidentally
    # duplicating names and overwriting the real DB-backed implementations.
    # The actual endpoints were not implemented in this assignment.


prediction_controller = PredictionController()
