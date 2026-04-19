import json
import logging
import math
import traceback
from typing import Any

from flask import jsonify, request
from pydantic import ValidationError

from data5580_hw.gateways.arize_gateway import arize_gateway
from data5580_hw.gateways.llm_gateway import llm_gateway
from data5580_hw.gateways.mlflow_gateway import mlflow_gateway
from data5580_hw.models.prediction import Model, Prediction
from data5580_hw.services.database.database_client import db
from data5580_hw.services.database.prediction import (
    ExplanationSql,
    ModelSql,
    PredictionSQL,
)
from data5580_hw.services.explainer_service import explainer_service
from data5580_hw.services.model_service import model_service
from data5580_hw.services.umap_service import umap_embedding_service


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
    if n1 <= 1e-12 or n2 <= 1e-12:
        return -1.0
    return dot / (n1 * n2)


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

        # Run inference
        try:
            prediction.label = model_service.create_inference(model, prediction=prediction)
        except ValueError as e:
            logger.warning(
                "Prediction input mismatch",
                extra={"model_name": model.name, "model_version": model.version},
            )
            return jsonify({"error": f"Invalid input data: {str(e)}"}), 400
        except Exception:
            logger.exception("Error during prediction")
            return jsonify({"error": "Internal error during prediction."}), 500

        # Create UMAP embeddings from model inputs.
        try:
            inputs_df = prediction.get_pandas_frame_aligned_to_model(model._model)
            X = inputs_df.to_numpy(dtype=float)
            prediction.embeddings = umap_embedding_service.compute_embeddings(
                X, umap_params=prediction.umap_params
            )
        except Exception as e:
            # str(KeyError(...)) may omit "numba" even when the stack is inside numba;
            # include the traceback so JIT/bytecode failures degrade like other numba issues.
            tb = traceback.format_exc()
            error_text = (str(e) + "\n" + tb.lower()).lower()
            # Warm-up, numba/umap JIT issues (incl. KeyError 114 in numba.core.byteflow on Windows).
            keyerror_114 = isinstance(e, KeyError) and e.args == (114,)
            recoverable = (
                "not fitted yet" in error_text
                or isinstance(e, AssertionError)
                or "numba" in error_text
                or "byteflow" in error_text
                or keyerror_114
            )
            if recoverable:
                logger.warning(
                    "UMAP embedding skipped (%s); using numeric fallback.",
                    type(e).__name__,
                )
                logger.debug("UMAP embedding traceback:\n%s", tb)
                prediction.embeddings = None
            else:
                logger.exception("UMAP embedding calculation failed")
                return (
                    jsonify(
                        {
                            "error": "UMAP embedding calculation failed.",
                            "details": str(e),
                        }
                    ),
                    400,
                )

        if prediction.embeddings is None:
            vector = _numeric_embedding_from_features(prediction.features)
            prediction.embeddings = [vector] if vector else None

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
        prediction_sql: PredictionSQL = (
            db.session.query(PredictionSQL)
            .filter(PredictionSQL.id == prediction_id)
            .first()
        )
        if not prediction_sql:
            return jsonify({"error": "Prediction not found"}), 404
        return jsonify(prediction_sql.to_prediction().model_dump()), 200

    @staticmethod
    def get_prediction_explainer(prediction_id: str) -> tuple[str, int]:
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

    @staticmethod
    def update_actual(prediction_id: str) -> tuple[str, int]:
        ...


prediction_controller = PredictionController()
