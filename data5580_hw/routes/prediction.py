from flask import Blueprint

from data5580_hw.controllers.prediction import prediction_controller


prediction = Blueprint('prediction', __name__)


@prediction.route('/<model>/version/<version>/predict', methods=['POST'])
def predict(model: str, version: str):

    response = prediction_controller.create_prediction(model, version)

    return response


@prediction.route("/prediction/<prediction_id>", methods=["GET"])
def get_prediction(prediction_id: str):
    return prediction_controller.get_prediction_by_id(prediction_id)


@prediction.route("/prediction/<prediction_id>/explainer", methods=["GET"])
def get_prediction_explainer(prediction_id: str):
    return prediction_controller.get_prediction_explainer(prediction_id)
