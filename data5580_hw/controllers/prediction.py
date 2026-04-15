import json
import logging
import math
from typing import Any

from flask import jsonify, request
from pydantic import ValidationError

from data5580_hw.gateways.llm_gateway import llm_gateway
from data5580_hw.gateways.mlflow_gateway import mlflow_gateway
from data5580_hw.models.prediction import Prediction, Model
from data5580_hw.services.database.database_client import db
from data5580_hw.services.database.prediction import PredictionSQL, ModelSql
from data5580_hw.services.model_service import model_service


logger = logging.getLogger(__name__)


def _numeric_embedding_from_features(features: dict[str, Any]) -> list[float]:
    """
    Deterministic embedding fallback from numeric feature values.
    This supports nearest-prediction lookup even without external embedding models.
    """
    out: list[float] = []
    for key in sorted(features.keys()):
        value = features[key]
        if isinstance(value, bool):
            out.append(float(int(value)))
        elif isinstance(value, (int, float)):
            out.append(float(value))
    return out


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return -1.0
    dot = sum(a * b for a, b in zip(v1, v2))
    n1 = math.sqrt(sum(a * a for a in v1))
    n2 = math.sqrt(sum(b * b for b in v2))
    if n1 == 0.0 or n2 == 0.0:
        return -1.0
    return dot / (n1 * n2)


class PredictionController:
    @staticmethod
    def create_prediction(model_name: str, model_version: str):
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
        except Exception:
            logger.exception("Error loading model for prediction")
            return jsonify({"error": "Internal error loading model."}), 500

        try:
            payload = request.get_json(force=True) or {}
            prediction = Prediction.model_validate(payload)
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
        try:
            prediction.label = model_service.create_inference(model, prediction=prediction)
        except ValueError as e:
            return jsonify({"error": f"Invalid input data: {str(e)}"}), 400
        except Exception:
            logger.exception("Error during prediction")
            return jsonify({"error": "Internal error during prediction."}), 500

        vector = _numeric_embedding_from_features(prediction.features)
        prediction.embeddings = [vector] if vector else None

        model_sql = ModelSql.from_model(model)
        prediction_sql = PredictionSQL.from_prediction(prediction, model_sql)
        db.session.add(prediction_sql)
        db.session.commit()

        stored = (
            db.session.query(PredictionSQL)
            .filter(PredictionSQL.id == prediction.id)
            .first()
        )
        return jsonify(stored.to_prediction().model_dump()), 200

    @staticmethod
    def get_prediction_by_id(prediction_id: str):
        prediction_sql = (
            db.session.query(PredictionSQL)
            .filter(PredictionSQL.id == prediction_id)
            .first()
        )
        if not prediction_sql:
            return jsonify({"error": "Prediction not found"}), 404
        return jsonify(prediction_sql.to_prediction().model_dump()), 200

    @staticmethod
    def get_prediction_explainer(prediction_id: str):
        prediction_sql = (
            db.session.query(PredictionSQL)
            .filter(PredictionSQL.id == prediction_id)
            .first()
        )
        if not prediction_sql:
            return jsonify({"error": "Prediction not found"}), 404

        prediction = prediction_sql.to_prediction()
        target_vec = (
            prediction.embeddings[0]
            if prediction.embeddings and len(prediction.embeddings) > 0
            else []
        )

        peers = (
            db.session.query(PredictionSQL)
            .filter(PredictionSQL.model_id == prediction_sql.model_id)
            .filter(PredictionSQL.id != prediction_id)
            .all()
        )

        scored: list[tuple[float, Prediction]] = []
        for peer_sql in peers:
            peer = peer_sql.to_prediction()
            peer_vec = (
                peer.embeddings[0]
                if peer.embeddings and len(peer.embeddings) > 0
                else []
            )
            score = _cosine_similarity(target_vec, peer_vec)
            if score >= 0:
                scored.append((score, peer))

        scored.sort(key=lambda x: x[0], reverse=True)
        nearest = scored[:3]

        base_payload = prediction.model_dump()
        if not nearest:
            base_payload["nearest_predictions"] = []
            base_payload["key_differences"] = [
                "No relevant similar predictions were found for comparison."
            ]
            base_payload["summary"] = (
                "No similar predictions were available, so no comparative LLM summary "
                "could be generated."
            )
            return jsonify(base_payload), 200

        nearest_payload = []
        differences = []
        for similarity, peer in nearest:
            nearest_payload.append(
                {
                    "prediction_id": peer.id,
                    "similarity": round(float(similarity), 4),
                    "label": peer.label,
                    "actual": peer.actual,
                    "tags": peer.tags,
                }
            )
            differences.append(
                f"Prediction {peer.id} has label={peer.label}, actual={peer.actual}, "
                f"similarity={similarity:.4f}"
            )

        prompt = (
            "You are helping explain model predictions.\n"
            "Current prediction:\n"
            f"{json.dumps(base_payload, default=str)}\n\n"
            "Nearest predictions:\n"
            f"{json.dumps(nearest_payload, default=str)}\n\n"
            "Return a concise human-readable summary with bullet points that highlights "
            "key differences in confidence/probability, semantic changes, and notable variances."
        )
        summary = llm_gateway.summarize_prediction_differences(prompt)

        base_payload["nearest_predictions"] = nearest_payload
        base_payload["key_differences"] = differences
        base_payload["summary"] = summary
        return jsonify(base_payload), 200


prediction_controller = PredictionController()
