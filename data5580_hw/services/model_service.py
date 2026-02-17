from typing import Union
import pandas as pd

from flask import Flask

from data5580_hw.models.prediction import Prediction, Model


class ModelService:

    @staticmethod
    def create_inference(model: Model, prediction: Prediction) -> Union[str, int, float]:
        return model._model.predict(prediction.get_pandas_frame_of_inputs())[0]


model_service = ModelService()
