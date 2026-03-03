from typing import Union, List

from data5580_hw.models.prediction import Prediction, Model, Explanations, Explanation


class ExplainerService:

    @staticmethod
    def create_explanation(model: Model, prediction: Prediction) -> Explanations:
        explanations_ = model._explainer.predict(prediction.get_pandas_frame_of_inputs())

        explanations = Explanations()

        features = list(prediction.get_pandas_frame_of_inputs().columns)

        for idx in range(0, len(explanations_)):
            explanations.explanations.append(
                Explanation(
                    name=str(idx)
                    , values=dict(zip(features, explanations_[idx]))
                )
            )

        return explanations


explainer_service = ExplainerService()
