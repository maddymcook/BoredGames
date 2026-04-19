from typing import Union

from data5580_hw.models.prediction import Prediction, Model


class ModelService:

    @staticmethod
    def create_inference(model: Model, prediction: Prediction) -> Union[str, int, float]:
        m = model._model
        df = prediction.get_pandas_frame_aligned_to_model(m)
        return m.predict(df)[0]


model_service = ModelService()
