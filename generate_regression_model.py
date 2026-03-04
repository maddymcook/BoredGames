# mlflow server --port 8080 --backend-store-uri sqlite:///mlruns.db

import mlflow
from tempfile import TemporaryDirectory
import pickle
import mlflow.sklearn
from mlflow.models import infer_signature
from mlflow.tracking import MlflowClient

import numpy as np
import pandas as pd
import shap
from sklearn.datasets import fetch_california_housing
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

# ----------------------------
# Configuration
# ----------------------------
EXPERIMENT_NAME = "california-housing"
REGISTERED_MODEL_NAME = "california-housing"

mlflow.set_tracking_uri("http://localhost:8080")
mlflow.set_experiment(EXPERIMENT_NAME)

# ----------------------------
# Load dataset
# ----------------------------
housing = fetch_california_housing()

# Create features X and target y.
X = pd.DataFrame(housing.data, columns=housing.feature_names)
y = housing.target  # Median house value in $100,000s

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)


# Define a custom pyfunc model
class SHAPModel(mlflow.pyfunc.PythonModel):
    def load_context(self, context):
        # Load model and SHAP explainer
        with open(context.artifacts["model"], 'rb') as fin:
            self.model = pickle.load(fin)

    def predict(self, context, model_input):
        # Calculate SHAP values
        return self.model.shap_values(model_input)

# ----------------------------
# Train + Log
# ----------------------------
with mlflow.start_run() as run:

    model = DecisionTreeRegressor()
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    # Metrics
    mse = mean_squared_error(y_test, predictions)
    r2 = r2_score(y_test, predictions)

    # Log parameters
    mlflow.log_param("model_type", "DecisionTreeRegressor")
    # mlflow.log_param("fit_intercept", model.fit_intercept)

    # Log metrics
    mlflow.log_metric("mse", mse)
    mlflow.log_metric("r2", r2)

    # Log model with signature
    signature = infer_signature(X_train, model.predict(X_train))

    logged_model = mlflow.sklearn.log_model(
        sk_model=model,
        artifact_path="model",
        signature=signature,
        registered_model_name=REGISTERED_MODEL_NAME
    )

    run_id = run.info.run_id

    print(logged_model)

    # log an explainer
    explainer = shap.Explainer(model)

    with TemporaryDirectory() as temp_dir:
        local_path = temp_dir + '/explainer.pkl'

        with open(local_path, 'wb') as fout:
            pickle.dump(explainer, fout)

        artifacts = {
            "model": local_path
        }

        response = mlflow.pyfunc.log_model(
            artifact_path='model-explainer'
            , python_model=SHAPModel()
            , artifacts=artifacts
            , input_example=X_test.fillna(0).sample(n=10, random_state=123)
            , signature=mlflow.models.signature.infer_signature(model_input=X_test,
                                                                model_output=explainer.shap_values(X_test))
            , extra_pip_requirements=['shap']
        )


print(f"Run logged with ID: {run_id}")
