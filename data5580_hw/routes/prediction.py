from flask import Blueprint

from data5580_hw.controllers.prediction import prediction_controller


prediction = Blueprint('prediction', __name__)


@prediction.route('/<model>/version/<version>/predict', methods=['POST'])
def predict(model: str, version: str):

    response = prediction_controller.create_prediction(model, version)

    return response