import logging
import os
import mlflow
import requests
from mlflow.tracking import MlflowClient

from data5580_hw.models.prediction import Model

logger = logging.getLogger(__name__)


class MLFlowGateway:

    models = {}

    def init_app(self, app):
        mlflow.set_tracking_uri(app.config['TRACKING_URI'])
        self.models = app.config.get('MODELS', {})

        if app.config.get('TESTING') or os.environ.get('TESTING'):
            return

        try:
            response = requests.get(app.config['TRACKING_URI'], timeout=2)
            if response.status_code != 200:
                raise Exception(f'MLFlow server returned {response.status_code}')
            for model in self.models.keys():
                for version in self.models[model].keys():
                    flavor_ = self.models[model][version].get('mlflow_flavor', 'pyfunc')
                    self.models[model][version]["model"] = self._load_model(
                        self._get_model_uri(model, version), flavor_
                    )
        except Exception as e:
            logger.warning(
                "MLFlow not available at %s: %s. App will start; /models/compare and prediction need MLFlow. Start with: mlflow server --port 8080 --backend-store-uri sqlite:///mlruns.db (on Windows add --workers 1).",
                app.config['TRACKING_URI'],
                e,
            )

    def _get_model_uri(self, model_name, model_version):
        return f"models:/{model_name}/{model_version}"

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

        return model

    def get_run_metrics(self, run_id: str):
        """
        Get run and its metrics from MLFlow by run ID.
        Returns dict with run_id, metrics, artifact_uri.
        Raises Exception if run_id is invalid or run not found.
        """
        client = MlflowClient()
        run = client.get_run(run_id)
        return {
            "run_id": run.info.run_id,
            "metrics": dict(run.data.metrics) if run.data.metrics else {},
            "artifact_uri": run.info.artifact_uri,
        }


mlflow_gateway: MLFlowGateway = MLFlowGateway()
