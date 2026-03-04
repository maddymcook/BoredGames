import logging

from flask import jsonify, request
from pydantic import ValidationError

from sqlalchemy.exc import IntegrityError

from data5580_hw.services.database.database_client import db
from data5580_hw.gateways.mlflow_gateway import mlflow_gateway
from data5580_hw.services.database.user_model import UserSQL
from data5580_hw.models.user import User

from data5580_hw.models.prediction import Prediction, Model
from data5580_hw.services.model_service import model_service
from data5580_hw.services.database.prediction import PredictionSQL, ModelSql


logger = logging.getLogger(__name__)


class PredictionController:

    @staticmethod
    def create_prediction(model_name: str, model_version: str) -> tuple[str, int]:

        # Get the model
        model: Model = mlflow_gateway.get_model(model_name, model_version)
        prediction = Prediction.model_validate(request.get_json(force=True))
        prediction.model = model

        # Create prediction
        label = model_service.create_inference(model, prediction=prediction)
        prediction.label = label

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

        return prediction.model_dump_json(), 200

    @staticmethod
    def get_prediction_by_id(prediction_id: str) -> tuple[str, int]:

        logger.debug(f'Got prediction_id {prediction_id}')

        prediction_sql: PredictionSQL = db.session.query(PredictionSQL).filter(PredictionSQL.id == prediction_id).first()

        prediction = prediction_sql.to_prediction()

        return prediction.model_dump_json(), 200
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

        # Load model (REGRESSION)
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

        # Run inference on regression model
        try:
            label = model_service.create_inference(model, prediction=prediction)
        except ValueError as e:
            # Typical for bad feature shape / incompatible input
            logger.warning(
                "Prediction input mismatch for regression model",
                extra={"model_name": model.name, "model_version": model.version},
            )
            return (
                jsonify({"error": f"Invalid input data: {str(e)}"}),
                400,
            )
        except Exception:
            logger.exception("Error during regression prediction")
            return jsonify({"error": "Internal error during prediction."}), 500

        prediction.label = label

        # Persist prediction for auditing
        model_sql = ModelSql.from_model(model)
        prediction_sql = PredictionSQL.from_prediction(prediction, model_sql)

        db.session.add(prediction_sql)
        db.session.commit()

        prediction_sql: PredictionSQL = (
            db.session.query(PredictionSQL)
            .filter(PredictionSQL.id == prediction.id)
            .first()
        )

        prediction = prediction_sql.to_prediction()

        logger.info(
            "Prediction completed",
            extra={
                "prediction_id": prediction.id,
                "model_name": prediction.model.name if prediction.model else None,
                "model_version": prediction.model.version if prediction.model else None,
                "label": prediction.label,
            },
        )

        return prediction.model_dump_json(), 200

    @staticmethod
    def get_prediction_by_id(prediction: str) -> tuple[str, int]:
        ...
        # logger.debug(f'Got user_id {user_id}')
        #
        # user_sql = db.session.query(UserSQL).filter(UserSQL.id == user_id).first()
        #
        # user = User.model_validate(user_sql, from_attributes=True)
        #
        # if not user:
        #     return jsonify({}), 404
        #
        # logging.info(f"user created, {user.id} for {user.email}")
        #
        # return user.model_dump_json(), 200

    @staticmethod
    def update_actual(prediction_id: str) -> tuple[str, int]:
        ...
        #
        # user = User.model_validate(request.get_json(force=True))
        #
        # user_sql = db.session.query(UserSQL).filter(UserSQL.id == user_id).first()
        #
        # user_sql.name = user.name
        # user_sql.email = user.email
        #
        # db.session.commit()
        #
        # return user.model_dump_json(), 200


prediction_controller = PredictionController()
