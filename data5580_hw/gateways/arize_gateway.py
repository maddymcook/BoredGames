"""
Arize ML observability integration.

Inference rows are sent with :meth:`arize.client.ArizeClient.ml.log_stream` using
per-field ``features`` (dict), ``prediction_label``, ``actual_label``, ``tags``, and optional ``shap_values``.

Environment variables (also surfaced on Flask app.config):
  ARIZE_ENABLED — set to 1/true to send inference logs.
  ARIZE_API_KEY — API key (or rely on SDK defaults).
  ARIZE_SPACE_KEY — Space ID for uploads. Prefer the numeric Space ID from Space settings.
    A Base64 UI value (decodes to "Space:<digits>:...") is normalized to that numeric ID.
  ARIZE_ENVIRONMENT — development | staging | production (maps to Arize Environments;
    inference without ground truth uses PRODUCTION so uploads validate).
  ARIZE_FALLBACK_PATH — JSONL file for records when the Arize API fails.
  ARIZE_REGION — optional, e.g. us-central-1a (see arize.regions.Region).
  ARIZE_VALIDATION_BATCH_ID — batch id when logging to VALIDATION (staging + labels).
"""

from __future__ import annotations

import base64
import binascii
import json
import logging
import numbers
import os
import re
from pathlib import Path
from typing import Any

import pandas as pd
from arize.client import ArizeClient
from arize.ml.types import Environments, ModelTypes
from arize.regions import Region

from data5580_hw.models.prediction import Model, Prediction

logger = logging.getLogger(__name__)


def _env_testing(app_config: dict) -> bool:
    """True when the Flask app is in test mode (explicit config wins over process env)."""
    if "TESTING" in app_config:
        return bool(app_config["TESTING"])
    return bool(os.environ.get("TESTING"))


def _normalize_arize_space_id(raw: str) -> str:
    """
    The UI sometimes shows a Base64 Relay ID (e.g. decodes to 'Space:39299:2kEU').
    ML uploads expect the numeric space id for Grpc-Metadata-arize-space-id.
    """
    s = (raw or "").strip()
    if not s:
        return s
    if os.environ.get("ARIZE_SPACE_KEY_NO_DECODE", "").lower() in ("1", "true", "yes"):
        return s
    try:
        pad = "=" * (-len(s) % 4)
        decoded = base64.b64decode(s + pad).decode("ascii")
        if decoded.startswith("Space:"):
            m = re.match(r"Space:(\d+):", decoded)
            if m:
                n = m.group(1)
                logger.info(
                    "ARIZE_SPACE_KEY looked like an encoded Space id; using numeric space_id %s",
                    n,
                )
                return n
            logger.info(
                "ARIZE_SPACE_KEY decoded to %r; using decoded value as space_id.",
                decoded,
            )
            return decoded
    except (ValueError, UnicodeDecodeError, binascii.Error):
        pass
    return s


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


def _cast_stream_value(v: Any) -> str | bool | float | int:
    """Coerce values to types accepted by ml.log_stream (no numpy / complex types)."""
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v
    if isinstance(v, numbers.Integral) and not isinstance(v, bool):
        return int(v)
    if isinstance(v, numbers.Real) and not isinstance(v, bool):
        return float(v)
    if hasattr(v, "item"):
        return _cast_stream_value(v.item())
    return str(v)


def _features_dict_for_stream(
    prediction: Prediction,
) -> dict[str, str | bool | float | int] | None:
    feats = prediction.features
    if isinstance(feats, list):
        if not feats:
            return None
        raw: dict[str, Any] = feats[0] if isinstance(feats[0], dict) else {}
    elif isinstance(feats, dict):
        raw = feats
    else:
        return None
    if not raw:
        return None
    return {str(k): _cast_stream_value(v) for k, v in raw.items()}


def _tags_for_stream(
    tags: dict[str, Any] | None,
) -> dict[str, str | bool | float | int] | None:
    if not tags:
        return None
    return {str(k): _cast_stream_value(v) for k, v in tags.items()}


def _shap_dict_for_stream(prediction: Prediction) -> dict[str, float] | None:
    ex = prediction.explanations
    if not ex or not ex.explanations:
        return None
    values = ex.explanations[0].values
    out: dict[str, float] = {}
    for k, v in values.items():
        try:
            out[str(k)] = float(v)
        except (TypeError, ValueError):
            continue
    return out or None


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
        self._space_id = _normalize_arize_space_id(
            str(cfg.get("ARIZE_SPACE_KEY") or "")
        )
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
        numeric = _is_numeric_model(mt)

        try:
            features = _features_dict_for_stream(prediction)
            tags = _tags_for_stream(prediction.tags)
            shap = _shap_dict_for_stream(prediction)
            ts = int(pd.Timestamp(prediction.created).timestamp())

            stream_kw: dict[str, Any] = {
                "space_id": self._space_id,
                "model_name": model.name,
                "model_type": mt,
                "environment": env,
                "model_version": model.version,
                "prediction_id": prediction.id,
                "prediction_timestamp": ts,
            }
            if features:
                stream_kw["features"] = features
            if tags:
                stream_kw["tags"] = tags
            if shap:
                stream_kw["shap_values"] = shap
            if batch_id:
                stream_kw["batch_id"] = batch_id

            if numeric:
                if prediction.label is not None:
                    stream_kw["prediction_label"] = float(prediction.label)
                if has_actual and prediction.actual is not None:
                    stream_kw["actual_label"] = float(prediction.actual)
            else:
                if prediction.label is not None:
                    stream_kw["prediction_label"] = str(prediction.label)
                if has_actual and prediction.actual is not None:
                    stream_kw["actual_label"] = str(prediction.actual)

            logger.info(
                "Arize stream request: space_id=%s model=%s version=%s env=%s profile=%s has_actual=%s",
                self._space_id,
                model.name,
                model.version,
                env.name,
                self._profile,
                has_actual,
            )
            self._client.ml.log_stream(**stream_kw)
            logger.info(
                "Arize: logged inference (stream) model=%s version=%s env=%s prediction_id=%s",
                model.name,
                model.version,
                env.name,
                prediction.id,
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
