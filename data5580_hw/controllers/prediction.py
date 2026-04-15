import logging

from flask import jsonify, request
from pydantic import ValidationError

from data5580_hw.services.database.database_client import db
from data5580_hw.gateways.mlflow_gateway import mlflow_gateway
from data5580_hw.models.prediction import Prediction, Model
from data5580_hw.services.model_service import model_service
from data5580_hw.services.database.prediction import PredictionSQL, ModelSql, ExplanationSql
from data5580_hw.services.explainer_service import explainer_service
from data5580_hw.gateways.arize_gateway import arize_gateway
from data5580_hw.services.umap_service import umap_embedding_service


logger = logging.getLogger(__name__)


def _should_log_arize_request() -> bool:
    """
    Allow callers to opt out of Arize logging per request.

    Query param `arize_log=false` or header `X-Arize-Log: false`
    disables logging; everything else defaults to enabled.
    """
    q = request.args.get("arize_log")
    h = request.headers.get("X-Arize-Log")

    def _is_false(value):
        return isinstance(value, str) and value.strip().lower() in {
            "0",
            "false",
            "no",
            "off",
        }

    return not (_is_false(q) or _is_false(h))


class PredictionController:

    @staticmethod
    def create_prediction(model_name: str, model_version: str) -> tuple[str, int]:
        """
        POST /<model_name>/version/<model_version>/predict

        Expects JSON body with at least:
        {
          "features": { ... },
          "tags": { ... }   # optional
        }
        """
        logger.info(
            "Prediction request received",
            extra={"model_name": model_name, "model_version": model_version},
        )

        # Load model
        try:
            model: Model = mlflow_gateway.get_model(model_name, model_version)
        except KeyError:
            logger.warning(
                "Requested model not found",
                extra={"model_name": model_name, "model_version": model_version},
            )
            return (
                jsonify(
                    {
                        "error": f"Model '{model_name}' version '{model_version}' not found."
                    }
                ),
                404,
            )
        except Exception:
            logger.exception("Error loading model for prediction")
            return jsonify({"error": "Internal error loading model."}), 500

        # Parse and validate input payload
        try:
            data = request.get_json(force=True) or {}
            prediction = Prediction.model_validate(data)
        except ValidationError as e:
            logger.warning(
                "Invalid prediction input",
                extra={"errors": e.errors()},
            )
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

        # Run inference
        try:
            label = model_service.create_inference(model, prediction=prediction)
        except ValueError as e:
            logger.warning(
                "Prediction input mismatch",
                extra={"model_name": model.name, "model_version": model.version},
            )
            return (
                jsonify({"error": f"Invalid input data: {str(e)}"}),
                400,
            )
        except Exception:
            logger.exception("Error during prediction")
            return jsonify({"error": "Internal error during prediction."}), 500

        prediction.label = label
        # Create UMAP embeddings from inputs using a persisted UMAP model cache.
        try:
            inputs_df = prediction.get_pandas_frame_of_inputs()
            X = inputs_df.to_numpy(dtype=float)
            prediction.embeddings = umap_embedding_service.compute_embeddings(
                X, umap_params=prediction.umap_params
            )
        except Exception as e:
            logger.exception("UMAP embedding calculation failed")
            error_text = str(e).lower()
            # Graceful degradation for warm-up and known runtime/JIT instability
            # paths (seen in CI with numba/umap transform compilation).
            if (
                "not fitted yet" in error_text
                or isinstance(e, AssertionError)
                or "numba" in error_text
            ):
                prediction.embeddings = None
            else:
                return (
                    jsonify(
                        {
                            "error": "UMAP embedding calculation failed.",
                            "details": str(e),
                        }
                    ),
                    400,
                )

        # Create explanation
        if prediction.model._explainer:
            explanations = explainer_service.create_explanation(model, prediction=prediction)
            prediction.explanations = explanations

        # Persist prediction
        model_sql = ModelSql.from_model(model)
        prediction_sql = PredictionSQL.from_prediction(prediction, model_sql)
        db.session.add(prediction_sql)
        if prediction.explanations and prediction.explanations.explanations:
            for explanation_sql in ExplanationSql.from_prediction(prediction):
                db.session.add(explanation_sql)
        db.session.commit()

        # Read back from database and return
        prediction_sql: PredictionSQL = (
            db.session.query(PredictionSQL)
            .filter(PredictionSQL.id == prediction.id)
            .first()
        )
        prediction = prediction_sql.to_prediction()

        # Log to Arize (non-blocking; errors are caught inside the gateway)
        if _should_log_arize_request():
            arize_gateway.log_inference(
                prediction_id=prediction.id,
                model_name=model.name,
                model_version=model.version,
                model_type=model.type,
                features=prediction.features,
                prediction_label=prediction.label,
                actual_label=prediction.actual,
                timestamp=prediction.created,
                tags=prediction.tags or None,
            )

        logger.info(
            "Prediction completed",
            extra={
                "prediction_id": prediction.id,
                "model_name": prediction.model.name if prediction.model else None,
                "model_version": prediction.model.version if prediction.model else None,
                "label": prediction.label,
            },
        )

        return jsonify(prediction.model_dump()), 200

    @staticmethod
    def get_prediction_by_id(prediction_id: str) -> tuple[str, int]:
        logger.debug(f'Got prediction_id {prediction_id}')

        prediction_sql: PredictionSQL = (
            db.session.query(PredictionSQL)
            .filter(PredictionSQL.id == prediction_id)
            .first()
        )

        prediction = prediction_sql.to_prediction()

        return jsonify(prediction.model_dump()), 200

    @staticmethod
    def update_actual(prediction_id: str) -> tuple[str, int]:
        ...


prediction_controller = PredictionController()
