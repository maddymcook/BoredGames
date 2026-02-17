"""
Route for comparing MLFlow runs by performance metrics.

POST /models/compare
Body: {
  "run_ids": ["<run_id_1>", "<run_id_2>", ...],
  "metric": "r2",
  "secondary_metric": "mse"
}
Returns the best run ID and optional artifact URI. See controller and
models.compare for input/output documentation.
"""
from flask import Blueprint

from data5580_hw.controllers.model_compare_controller import model_compare_controller

model_compare = Blueprint("model_compare", __name__)


@model_compare.route("/models/compare", methods=["POST"])
def compare_models():
    return model_compare_controller.compare_models()
