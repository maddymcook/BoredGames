import numpy as np

from data5580_hw.models.prediction import Prediction, Model, Explanations, Explanation


class ExplainerService:

    @staticmethod
    def create_explanation(model: Model, prediction: Prediction) -> Explanations:
        inputs_df = prediction.get_pandas_frame_aligned_to_model(model._model)
        explanations_ = model._explainer.predict(inputs_df)

        explanations = Explanations()
        features = list(inputs_df.columns)

        arr = np.asarray(explanations_)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)

        for idx in range(arr.shape[0]):
            row = arr[idx]
            explanations.explanations.append(
                Explanation(
                    name=str(idx),
                    values=dict(zip(features, row)),
                )
            )

        return explanations


explainer_service = ExplainerService()
