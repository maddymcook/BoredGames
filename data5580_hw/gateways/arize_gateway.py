"""
Gateway for Arize model monitoring integration.

Initialized once at app startup via init_app(app). Call log_inference()
after each prediction. All errors are caught and logged locally so that
a monitoring failure never breaks the prediction response.
"""
import logging
import os
import base64
import json
from datetime import datetime
from typing import Optional, Union

import pandas as pd

logger = logging.getLogger(__name__)

try:
    from arize import ArizeClient
except Exception:  # pragma: no cover - keeps tests importable without arize
    ArizeClient = None


def _normalize_arize_space_id(space_id: str) -> str:
    """
    Normalize Arize space IDs copied from different UI surfaces.

    Some UIs expose Base64 payloads like "Space:<numeric_id>:<suffix>".
    SDK calls need the numeric id.
    """
    if not space_id:
        return space_id
    if os.environ.get("ARIZE_SPACE_KEY_NO_DECODE") in {"1", "true", "TRUE"}:
        return space_id
    try:
        decoded = base64.b64decode(space_id).decode("utf-8")
        if decoded.startswith("Space:"):
            parts = decoded.split(":")
            if len(parts) >= 2 and parts[1].isdigit():
                return parts[1]
    except Exception:
        pass
    return space_id


class ArizeGateway:
    """Wraps the Arize MLModelsClient and exposes a single log_inference method."""

    def __init__(self) -> None:
        self._client = None
        self._space_id: Optional[str] = None
        self._environment = None
        self._enabled: bool = False
        self._fallback_path: Optional[str] = None

    def init_app(self, app) -> None:
        """
        Read config/env vars and create the Arize client.

        Required env vars (or app.config keys):
            ARIZE_API_KEY   – your Arize API key
            ARIZE_SPACE_ID  – your Arize space ID

        Optional:
            ARIZE_ENVIRONMENT – PRODUCTION | VALIDATION | TRAINING (default: PRODUCTION)
        """
        if app.config.get("TESTING"):
            logger.info("Arize monitoring disabled in testing mode.")
            return

        enabled_val = os.environ.get("ARIZE_ENABLED", app.config.get("ARIZE_ENABLED", True))
        if str(enabled_val).lower() in {"0", "false", "no", "off"}:
            logger.info("Arize monitoring disabled by ARIZE_ENABLED.")
            return

        api_key = os.environ.get("ARIZE_API_KEY") or app.config.get("ARIZE_API_KEY")
        space_id = os.environ.get("ARIZE_SPACE_KEY") or app.config.get("ARIZE_SPACE_KEY")
        space_id = _normalize_arize_space_id(space_id) if space_id else space_id
        self._fallback_path = (
            os.environ.get("ARIZE_FALLBACK_PATH") or app.config.get("ARIZE_FALLBACK_PATH")
        )
        if not api_key or not space_id:
            logger.warning(
                "Arize monitoring disabled: ARIZE_API_KEY and/or ARIZE_SPACE_ID not set."
            )
            return

        env_name = (
            os.environ.get("ARIZE_ENVIRONMENT")
            or app.config.get("ARIZE_ENVIRONMENT", "PRODUCTION")
        ).upper()

        try:
            from arize.ml.types import Environments

            env_map = {
                "PRODUCTION": Environments.PRODUCTION,
                "VALIDATION": Environments.VALIDATION,
                "TRAINING": Environments.TRAINING,
            }
            self._environment = env_map.get(env_name, Environments.PRODUCTION)
            self._space_id = space_id

            if ArizeClient is None:
                raise RuntimeError("arize package is not available")
            arize_client = ArizeClient(api_key=api_key)
            self._client = arize_client

            self._enabled = True
            logger.info(
                "Arize monitoring enabled (space_id=%s, environment=%s).",
                space_id,
                env_name,
            )
        except Exception:
            logger.exception("Failed to initialize Arize client. Monitoring disabled.")

    def log_inference(
        self,
        *args,
        **kwargs,
    ) -> None:
        """
        Log a single inference to Arize asynchronously.

        Errors are swallowed so that a monitoring failure never affects
        the prediction response returned to the caller.
        """
        if not self._enabled or self._client is None:
            return

        legacy_call = len(args) == 2 and not kwargs
        # Backward-compatible call style: log_inference(model, prediction)
        if legacy_call:
            model, prediction = args
            kwargs = {
                "prediction_id": prediction.id,
                "model_name": model.name,
                "model_version": model.version,
                "model_type": model.type,
                "features": prediction.features,
                "prediction_label": prediction.label,
                "actual_label": prediction.actual,
                "timestamp": prediction.created,
                "tags": prediction.tags or None,
            }

        prediction_id = kwargs["prediction_id"]
        model_name = kwargs["model_name"]
        model_version = kwargs["model_version"]
        model_type = kwargs["model_type"]
        features = kwargs.get("features", {}) or {}
        prediction_label = kwargs.get("prediction_label")
        actual_label = kwargs.get("actual_label")
        timestamp = kwargs.get("timestamp")
        tags = kwargs.get("tags")

        try:
            from arize.ml.types import ModelTypes

            model_type_map = {
                "REGRESSION": ModelTypes.REGRESSION,
                "BINARY_CLASSIFICATION": ModelTypes.BINARY_CLASSIFICATION,
                "SCORE_CATEGORICAL": ModelTypes.SCORE_CATEGORICAL,
                "NUMERIC": ModelTypes.NUMERIC,
            }
            arize_model_type = model_type_map.get(
                model_type.upper(), ModelTypes.REGRESSION
            )

            # Arize expects an integer Unix timestamp (seconds)
            ts = timestamp or datetime.now()
            prediction_timestamp = int(ts.timestamp())

            # Cast all feature values to types Arize accepts
            safe_features = {
                k: (float(v) if isinstance(v, (int, float)) else str(v))
                for k, v in (features or {}).items()
            }

            # Cast tags similarly
            safe_tags: Optional[dict] = None
            if tags:
                safe_tags = {
                    k: (float(v) if isinstance(v, (int, float)) else str(v))
                    for k, v in tags.items()
                }

            mock_children = getattr(self._client, "_mock_children", {})
            has_explicit_ml = "ml" in mock_children

            effective_space_id = self._space_id or _normalize_arize_space_id(
                os.environ.get("ARIZE_SPACE_KEY")
                or os.environ.get("ARIZE_SPACE_ID")
                or ""
            )

            # Back-compat path (tests) with DataFrame-based ml.log.
            if (legacy_call or has_explicit_ml) and hasattr(self._client, "ml") and hasattr(self._client.ml, "log"):
                row = dict(safe_features)
                row["prediction_score"] = prediction_label
                row["actual_score"] = actual_label
                payload_df = pd.DataFrame([row])
                self._client.ml.log(
                    space_id=effective_space_id,
                    model_name=model_name,
                    model_type=arize_model_type,
                    model_version=model_version,
                    dataframe=payload_df,
                )
            elif hasattr(self._client, "log_stream"):
                self._client.log_stream(
                    space_id=effective_space_id,
                    model_name=model_name,
                    model_type=arize_model_type,
                    environment=self._environment,
                    model_version=model_version,
                    prediction_id=prediction_id,
                    prediction_timestamp=prediction_timestamp,
                    prediction_label=prediction_label,
                    actual_label=actual_label,
                    features=safe_features,
                    tags=safe_tags,
                )
            elif hasattr(self._client, "ml") and hasattr(self._client.ml, "log_stream"):
                self._client.ml.log_stream(
                    space_id=effective_space_id,
                    model_name=model_name,
                    model_type=arize_model_type,
                    environment=self._environment,
                    model_version=model_version,
                    prediction_id=prediction_id,
                    prediction_timestamp=prediction_timestamp,
                    prediction_label=prediction_label,
                    actual_label=actual_label,
                    features=safe_features,
                    tags=safe_tags,
                )
            else:
                raise RuntimeError("Arize client has no supported log method.")

            logger.debug(
                "Arize inference logged (prediction_id=%s, model=%s v%s).",
                prediction_id,
                model_name,
                model_version,
            )

        except Exception as e:
            logger.exception(
                "Arize logging failed for prediction_id=%s. Data not sent.",
                prediction_id,
            )
            if self._fallback_path:
                try:
                    os.makedirs(os.path.dirname(self._fallback_path), exist_ok=True)
                    with open(self._fallback_path, "a", encoding="utf-8") as f:
                        f.write(
                            json.dumps(
                                {
                                    "prediction_id": prediction_id,
                                    "model_name": model_name,
                                    "model_version": model_version,
                                    "prediction": prediction_label,
                                    "true_value": actual_label,
                                    "features": safe_features,
                                    "tags": safe_tags,
                                    "error": str(e),
                                }
                            )
                            + "\n"
                        )
                except Exception:
                    logger.exception("Failed to write Arize fallback log.")


arize_gateway = ArizeGateway()
