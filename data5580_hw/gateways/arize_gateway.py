"""
Arize ML observability integration.

Environment variables (also surfaced on Flask app.config):
  ARIZE_ENABLED — set to 1/true to send inference logs.
  ARIZE_API_KEY — API key (or rely on SDK defaults).
  ARIZE_SPACE_KEY — Space ID in Arize (used as space_id for uploads).
  ARIZE_ENVIRONMENT — development | staging | production (maps to Arize Environments;
    inference without ground truth uses PRODUCTION so uploads validate).
  ARIZE_FALLBACK_PATH — JSONL file for records when the Arize API fails.
  ARIZE_REGION — optional, e.g. us-central-1a (see arize.regions.Region).
  ARIZE_VALIDATION_BATCH_ID — batch id when logging to VALIDATION (staging + labels).
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import pandas as pd
from arize.client import ArizeClient
from arize.ml.types import Environments, ModelTypes, Schema
from arize.regions import Region

from data5580_hw.models.prediction import Model, Prediction

logger = logging.getLogger(__name__)

PREDICTION_ID_COL = "prediction_id"
TIMESTAMP_COL = "inference_timestamp"
PRED_SCORE_COL = "prediction_score"
PRED_LABEL_COL = "prediction_label"
ACTUAL_SCORE_COL = "actual_score"
ACTUAL_LABEL_COL = "actual_label"


def _env_testing(app_config: dict) -> bool:
    """True when the Flask app is in test mode (explicit config wins over process env)."""
    if "TESTING" in app_config:
        return bool(app_config["TESTING"])
    return bool(os.environ.get("TESTING"))


def _parse_region(value: str) -> Region | None:
    if not value:
        return None
    for r in Region:
        if r.value == value:
            return r
    logger.warning("Unknown ARIZE_REGION %r; using SDK default endpoints.", value)
    return None


def _model_type_from_domain(model: Model) -> ModelTypes:
    t = (model.type or "REGRESSION").upper().replace("-", "_")
    mapping = {
        "REGRESSION": ModelTypes.REGRESSION,
        "NUMERIC": ModelTypes.NUMERIC,
        "BINARY_CLASSIFICATION": ModelTypes.BINARY_CLASSIFICATION,
        "MULTI_CLASS": ModelTypes.MULTI_CLASS,
        "MULTI_CLASS_CLASSIFICATION": ModelTypes.MULTI_CLASS,
        "SCORE_CATEGORICAL": ModelTypes.SCORE_CATEGORICAL,
        "RANKING": ModelTypes.RANKING,
    }
    return mapping.get(t, ModelTypes.REGRESSION)


def _is_numeric_model(mt: ModelTypes) -> bool:
    return mt in (ModelTypes.REGRESSION, ModelTypes.NUMERIC)


def _resolve_log_environment(
    profile: str, has_actual: bool
) -> tuple[Environments, str]:
    """
    Map deployment profile to Arize Environments + batch_id for VALIDATION.
    Without ground truth, TRAINING/VALIDATION cannot satisfy SDK validation; use PRODUCTION.
    """
    p = (profile or "production").lower()
    batch_id = ""
    if not has_actual:
        return Environments.PRODUCTION, batch_id
    if p == "production":
        return Environments.PRODUCTION, batch_id
    if p == "development":
        return Environments.TRAINING, batch_id
    if p == "staging":
        return Environments.VALIDATION, batch_id
    return Environments.PRODUCTION, batch_id


class ArizeGateway:
    """Buffers failed payloads to JSONL; never raises to callers."""

    def __init__(self) -> None:
        self._client: ArizeClient | None = None
        self._space_id: str = ""
        self._fallback_path: Path = Path("instance/arize_failed.jsonl")
        self._profile: str = "production"
        self._validation_batch_id: str = "staging-batch"
        self._enabled: bool = False

    def init_app(self, app) -> None:
        cfg = app.config
        self._enabled = bool(cfg.get("ARIZE_ENABLED"))
        self._space_id = (cfg.get("ARIZE_SPACE_KEY") or "").strip()
        self._fallback_path = Path(
            cfg.get("ARIZE_FALLBACK_PATH")
            or "instance/arize_failed.jsonl"
        )
        self._profile = (cfg.get("ARIZE_ENVIRONMENT") or "production").lower()
        self._validation_batch_id = (cfg.get("ARIZE_VALIDATION_BATCH_ID") or "staging-batch").strip()

        self._client = None
        if _env_testing(cfg):
            return
        if not self._enabled:
            return
        api_key = (cfg.get("ARIZE_API_KEY") or "").strip()
        if not api_key or not self._space_id:
            logger.info(
                "Arize monitoring is enabled but ARIZE_API_KEY or ARIZE_SPACE_KEY is missing; skipping client init."
            )
            return
        region = _parse_region((cfg.get("ARIZE_REGION") or "").strip())
        kwargs: dict[str, Any] = {"api_key": api_key}
        if region is not None:
            kwargs["region"] = region
        self._client = ArizeClient(**kwargs)

    def log_inference(
        self,
        model: Model,
        prediction: Prediction,
        *,
        batch_id_override: str | None = None,
    ) -> None:
        if not self._enabled or self._client is None:
            return

        has_actual = prediction.actual is not None
        env, batch_id = _resolve_log_environment(self._profile, has_actual)
        if env == Environments.VALIDATION:
            batch_id = batch_id_override or self._validation_batch_id

        mt = _model_type_from_domain(model)
        try:
            dataframe, schema = self._build_dataframe_and_schema(
                model, prediction, mt, has_actual
            )
        except Exception:
            logger.exception("Arize: failed to build dataframe/schema for logging")
            self._write_fallback(
                model, prediction, "build_dataframe_schema", batch_id, env
            )
            return

        try:
            self._client.ml.log(
                space_id=self._space_id,
                model_name=model.name,
                model_type=mt,
                dataframe=dataframe,
                schema=schema,
                environment=env,
                model_version=model.version,
                batch_id=batch_id,
                validate=True,
            )
        except Exception as e:
            logger.error(
                "Arize log failed (%s): %s",
                type(e).__name__,
                e,
                exc_info=True,
            )
            self._write_fallback(
                model, prediction, f"{type(e).__name__}: {e}", batch_id, env
            )

    def _build_dataframe_and_schema(
        self,
        model: Model,
        prediction: Prediction,
        model_type: ModelTypes,
        has_actual: bool,
    ) -> tuple[pd.DataFrame, Schema]:
        inputs = prediction.get_pandas_frame_of_inputs()
        row = inputs.iloc[:1].copy()

        row[PREDICTION_ID_COL] = str(prediction.id)
        ts = prediction.created
        row[TIMESTAMP_COL] = int(pd.Timestamp(ts).timestamp())

        numeric = _is_numeric_model(model_type)
        if numeric:
            if prediction.label is not None:
                row[PRED_SCORE_COL] = float(prediction.label)
            if has_actual and prediction.actual is not None:
                row[ACTUAL_SCORE_COL] = float(prediction.actual)
        else:
            if prediction.label is not None:
                row[PRED_LABEL_COL] = str(prediction.label)
            if has_actual and prediction.actual is not None:
                row[ACTUAL_LABEL_COL] = str(prediction.actual)

        for key, val in (prediction.tags or {}).items():
            col = f"tag_{key}"
            if col in row.columns:
                col = f"tag_meta_{key}"
            row[col] = val

        feature_cols = [c for c in inputs.columns.tolist()]
        tag_cols = [c for c in row.columns if c.startswith("tag_") or c.startswith("tag_meta_")]

        if numeric:
            schema = Schema(
                prediction_id_column_name=PREDICTION_ID_COL,
                timestamp_column_name=TIMESTAMP_COL,
                feature_column_names=feature_cols,
                prediction_score_column_name=PRED_SCORE_COL,
                actual_score_column_name=ACTUAL_SCORE_COL if has_actual else None,
                tag_column_names=tag_cols or None,
            )
        else:
            schema = Schema(
                prediction_id_column_name=PREDICTION_ID_COL,
                timestamp_column_name=TIMESTAMP_COL,
                feature_column_names=feature_cols,
                prediction_label_column_name=PRED_LABEL_COL,
                actual_label_column_name=ACTUAL_LABEL_COL if has_actual else None,
                tag_column_names=tag_cols or None,
            )

        return row, schema

    def _write_fallback(
        self,
        model: Model,
        prediction: Prediction,
        error: str,
        batch_id: str,
        env: Environments,
    ) -> None:
        record = {
            "error": error,
            "model_name": model.name,
            "model_version": model.version,
            "environment": env.name,
            "batch_id": batch_id,
            "prediction": prediction.label,
            "features": prediction.features,
            "true_value": prediction.actual,
            "timestamp": prediction.created.isoformat() if prediction.created else None,
            "prediction_id": prediction.id,
            "tags": prediction.tags,
        }
        path = self._fallback_path
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, default=str) + "\n")
        except OSError:
            logger.exception("Arize fallback: could not write to %s", path)


arize_gateway = ArizeGateway()
