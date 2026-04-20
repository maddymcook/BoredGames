from flask import Blueprint, jsonify

from data5580_hw.controllers.prediction import prediction_controller
from data5580_hw.gateways.mlflow_gateway import mlflow_gateway


prediction = Blueprint('prediction', __name__)


@prediction.route("/models/registry", methods=["GET"])
def registered_models():
    """Which model names/versions this process loaded from config (debug / demo)."""
    reg = {name: list(vers.keys()) for name, vers in mlflow_gateway.models.items()}
    return jsonify({"models": reg})


@prediction.route('/<model>/version/<version>/predict', methods=['POST'])
def predict(model: str, version: str):

    response = prediction_controller.create_prediction(model, version)

    return response


@prediction.route(
    "/prediction/<prediction_id>", methods=["GET"], strict_slashes=False
)
def get_prediction(prediction_id: str):
    return prediction_controller.get_prediction_by_id(prediction_id)


@prediction.route(
    "/prediction/<prediction_id>/explainer",
    methods=["GET"],
    strict_slashes=False,
)
def get_prediction_explainer(prediction_id: str):
    return prediction_controller.get_prediction_explainer(prediction_id)
