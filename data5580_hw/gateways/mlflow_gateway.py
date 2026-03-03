import mlflow
import requests

from data5580_hw.models.prediction import Model


class MLFlowGateway:

    models = {}

    def init_app(self, app):
        mlflow.set_tracking_uri(app.config['TRACKING_URI'])
        self.models = app.config['MODELS']

        response = requests.get(app.config['TRACKING_URI'])

        if response.status_code != 200:
            raise Exception(f'MLFlow tracking server not listening at {app.config["TRACKING_URI"]}. Start server with cmd: mlflow server --port 8080 --backend-store-uri sqlite:///mlruns.db')

        for model in self.models.keys():
            for version in self.models[model].keys():
                flavor_ = self.models[model][version].get('mlflow_flavor', 'pyfunc')
                self.models[model][version]["model"] = self._load_model(self._get_model_uri(model, version), flavor_)

                if True:
                    from mlflow.client import MlflowClient

                    run_id = MlflowClient().get_model_version(model, version).run_id
                    run: mlflow.ActiveRun = mlflow.get_run(run_id)

                    for model_ in run.outputs.model_outputs:
                        model_details = mlflow.get_logged_model(model_.model_id)
                        if model_details.name == 'model-explainer':
                            self.models[model][version]['explainer'] = mlflow.pyfunc.load_model(model_details.model_uri)
                            break

    def _get_model_uri(self, model_name, model_version):
        return f"models:/{model_name}/{model_version}"

    def _get_explainer_uri(self, run_id):
        return f"runs:/{run_id}/model-explainer"

    def _load_model(self, model_uri, model_flavor):
        if model_flavor == "sklearn":
            return mlflow.sklearn.load_model(model_uri)
        elif model_flavor == "tensorflow":
            return mlflow.tensorflow.load_model(model_uri)
        elif model_flavor == "pytorch":
            return mlflow.pytorch.load_model(model_uri)
        elif model_flavor == "xgboost":
            return mlflow.xgboost.load_model(model_uri)
        elif model_flavor == "pyfunc":
            return mlflow.pyfunc.load_model(model_uri)
        else:
            raise ValueError(f"Unsupported model flavor: {model_flavor}")

    def get_model(self, model_name, model_version) -> Model:

        model_ = self.models[model_name][model_version]

        model = Model(
            type=model_["model_type"]
            , name=model_name
            , version=model_version
        )

        model._model = model_['model']
        model._explainer = model_.get('explainer', None)

        return model


mlflow_gateway: MLFlowGateway = MLFlowGateway()