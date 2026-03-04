"""
Controller for comparing MLFlow runs by performance metrics.

Accepts a list of run IDs and a comparison metric; returns the best run ID
and optional artifact URI. Handles invalid run IDs and missing metrics.
"""
import logging

from flask import jsonify, request
from pydantic import ValidationError

from data5580_hw.models.compare import CompareModelsRequest
from data5580_hw.services.model_compare_service import model_compare_service

logger = logging.getLogger(__name__)


class ModelCompareController:
    """Compare MLFlow runs and return the best performing run."""

    @staticmethod
    def compare_models():
        """
        POST /models/compare
        Body: { "run_ids": ["id1", "id2"], "metric": "r2", "secondary_metric": "mse" (optional) }
        Returns: { "best_run_id", "metric", "metric_value", "artifact_uri", "warnings" }
        """
        try:
            data = request.get_json(force=True)
            if not data:
                return jsonify({"error": "Request body is required. Provide run_ids and optional metric."}), 400
            payload = CompareModelsRequest.model_validate(data)
        except ValidationError as e:
            errors = e.errors()
            msg = "Invalid request"
            if errors and errors[0].get("loc"):
                msg += f": {errors[0]['loc'][0]}"
            return jsonify({"error": msg, "details": [x.get("msg") for x in errors]}), 400

        if not payload.run_ids:
            return jsonify({"error": "At least one run_id is required."}), 400

        try:
            result = model_compare_service.compare_runs(
                run_ids=payload.run_ids,
                metric=payload.metric,
                secondary_metric=payload.secondary_metric,
            )
            return jsonify(result.model_dump()), 200
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.exception("Model comparison failed")
            return jsonify({"error": "Failed to compare runs. Check MLFlow is reachable and run IDs are valid."}), 503


model_compare_controller = ModelCompareController()
