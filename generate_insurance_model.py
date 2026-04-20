"""
Train and register a new regression model from the Kaggle insurance dataset.

Usage:
    python generate_insurance_model.py
"""

from __future__ import annotations

import os
import pickle
from pathlib import Path
from tempfile import TemporaryDirectory

import kagglehub
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from mlflow.models import infer_signature
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from umap import UMAP

EXPERIMENT_NAME = "insurance-charges"
REGISTERED_MODEL_NAME = "insurance-charges"
TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://127.0.0.1:8080")
TARGET_COL = "charges"
RANDOM_STATE = 42


class SHAPModel(mlflow.pyfunc.PythonModel):
    def load_context(self, context):
        with open(context.artifacts["explainer"], "rb") as f:
            self.explainer = pickle.load(f)

    def predict(self, context, model_input):
        # Return SHAP values for model_input rows.
        values = self.explainer(model_input)
        return values.values


def _load_insurance_df() -> pd.DataFrame:
    dataset_dir = Path(kagglehub.dataset_download("mirichoi0218/insurance"))
    csv_path = dataset_dir / "insurance.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Expected file not found: {csv_path}")
    return pd.read_csv(csv_path)


def main() -> None:
    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

    df = _load_insurance_df()
    y = df[TARGET_COL].astype(float)
    X = df.drop(columns=[TARGET_COL])
    X = pd.get_dummies(X, columns=["sex", "smoker", "region"], drop_first=True)
    X = X.astype("float64")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE
    )

    with mlflow.start_run() as run:
        model = RandomForestRegressor(
            n_estimators=250,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        )
        model.fit(X_train, y_train)

        preds = model.predict(X_test)
        rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
        r2 = float(r2_score(y_test, preds))

        mlflow.log_param("dataset", "kaggle-insurance")
        mlflow.log_param("model_type", "RandomForestRegressor")
        mlflow.log_param("n_estimators", model.n_estimators)
        mlflow.log_param("feature_count", X.shape[1])
        mlflow.log_metric("rmse", rmse)
        mlflow.log_metric("r2", r2)

        signature = infer_signature(X_train, model.predict(X_train))
        mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path="model",
            signature=signature,
            registered_model_name=REGISTERED_MODEL_NAME,
        )

        with TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)

            # --- Embedding artifact ---
            emb_sample = X_train.sample(min(300, len(X_train)), random_state=RANDOM_STATE)
            reducer = UMAP(
                n_components=2,
                n_neighbors=min(15, max(2, len(emb_sample) - 1)),
                min_dist=0.1,
                metric="euclidean",
                random_state=RANDOM_STATE,
            )
            emb_2d = reducer.fit_transform(emb_sample.to_numpy(dtype=float))
            emb_df = pd.DataFrame(
                emb_2d, columns=["umap_x", "umap_y"], index=emb_sample.index
            ).reset_index(names=["row_id"])
            emb_df["target_charges"] = y_train.loc[emb_df["row_id"]].values

            embedding_csv = tmp / "insurance_umap_embeddings.csv"
            emb_df.to_csv(embedding_csv, index=False)
            mlflow.log_artifact(str(embedding_csv), artifact_path="embeddings")
            mlflow.log_param("embedding_method", "umap_2d")
            mlflow.log_metric("embedding_rows", float(len(emb_df)))

            # --- Always-on explainer artifact (permutation importance) ---
            perm = permutation_importance(
                model,
                X_test,
                y_test,
                n_repeats=5,
                random_state=RANDOM_STATE,
                n_jobs=-1,
            )
            perm_df = pd.DataFrame(
                {
                    "feature": X_test.columns,
                    "importance_mean": perm.importances_mean,
                    "importance_std": perm.importances_std,
                }
            ).sort_values("importance_mean", ascending=False)
            fallback_csv = tmp / "feature_importance_explainer.csv"
            perm_df.to_csv(fallback_csv, index=False)
            mlflow.log_artifact(str(fallback_csv), artifact_path="explainers")
            mlflow.log_param("explainer_baseline_type", "permutation_importance")

            # --- Optional SHAP explainer artifact ---
            try:
                import shap

                explainer = shap.Explainer(
                    model,
                    X_train.sample(min(200, len(X_train)), random_state=RANDOM_STATE),
                )
                explainer_path = tmp / "explainer.pkl"
                with open(explainer_path, "wb") as f:
                    pickle.dump(explainer, f)

                sample = X_test.head(min(20, len(X_test)))
                mlflow.pyfunc.log_model(
                    artifact_path="model-explainer",
                    python_model=SHAPModel(),
                    artifacts={"explainer": str(explainer_path)},
                    input_example=X_test.fillna(0).sample(
                        min(10, len(X_test)), random_state=RANDOM_STATE
                    ),
                    signature=infer_signature(
                        model_input=sample,
                        model_output=explainer(sample).values,
                    ),
                    extra_pip_requirements=["shap"],
                )
                mlflow.log_param("explainer_type", "shap")
            except Exception as exc:
                print(f"Warning: SHAP explainer logging skipped: {exc}")
                mlflow.log_param("explainer_type", "permutation_importance")

        print(f"Run logged with ID: {run.info.run_id}")
        print(f"Tracking URI: {TRACKING_URI}")
        print(f"Registered model: {REGISTERED_MODEL_NAME}")
        print(f"Metrics: rmse={rmse:.4f}, r2={r2:.4f}")


if __name__ == "__main__":
    main()
