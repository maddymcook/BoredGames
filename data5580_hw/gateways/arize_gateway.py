"""
Gateway for Arize model monitoring integration.

Supports:
  - arize 7.x: `arize.api.Client` + `client.log` (Future -> requests.Response)
  - arize 8.x: `ArizeClient` + `log_stream` / `ml.log_stream`

If `arize.api.Client` cannot be imported, falls back to `ArizeClient`.
"""
import base64
import json
import logging
import os
import threading
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)

_SDK_BACKEND_LEGACY = "legacy_api"
_SDK_BACKEND_ARIZE_CLIENT = "arize_client"


def _normalize_arize_space_id(space_id: str) -> str:
    """
    Prepare ARIZE_SPACE_KEY for SDK / HTTP clients.

    The Arize UI often shows a Base64 blob that decodes to ``Space:<id>:<suffix>``.
    Some APIs reject the numeric id alone (403 invalid Space ID); they expect the
    opaque Base64 string. Default behavior: if the value decodes as a Space relay
    payload, return the original string unchanged.

    Env overrides:
        ARIZE_SPACE_KEY_NO_DECODE=1 — never transform (pass through as-is).
        ARIZE_SPACE_KEY_NUMERIC_ONLY=1 — extract only the numeric id (legacy).
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
                if os.environ.get("ARIZE_SPACE_KEY_NUMERIC_ONLY") in {
                    "1",
                    "true",
                    "TRUE",
                }:
                    return parts[1]
                return space_id
    except Exception:
        pass
    return space_id


def _finalize_arize_log_future(
    fut: Any,
    *,
    prediction_id: str,
    model_name: str,
    model_version: str,
    fallback_path: Optional[str],
    safe_features: dict,
    safe_tags: Optional[dict],
    prediction_label: Any,
    actual_label: Any,
) -> None:
    """Runs after Client.log / log_stream Future completes; logs HTTP outcome."""
    try:
        timeout = int(os.environ.get("ARIZE_LOG_FUTURE_TIMEOUT", "60"))
        resp = fut.result(timeout=timeout)
        code = getattr(resp, "status_code", None)
        body = (getattr(resp, "text", None) or "")[:500]
        if code == 200:
            logger.info(
                "Arize log ok prediction_id=%s model=%s v=%s status=%s",
                prediction_id,
                model_name,
                model_version,
                code,
            )
        else:
            logger.warning(
                "Arize log non-200 prediction_id=%s model=%s v=%s status=%s body=%s",
                prediction_id,
                model_name,
                model_version,
                code,
                body,
            )
    except Exception as exc:
        logger.error(
            "Arize log failed prediction_id=%s model=%s v=%s: %s",
            prediction_id,
            model_name,
            model_version,
            exc,
            exc_info=True,
        )
        if fallback_path:
            try:
                os.makedirs(os.path.dirname(fallback_path), exist_ok=True)
                with open(fallback_path, "a", encoding="utf-8") as f:
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
                                "error": str(exc),
                            }
                        )
                        + "\n"
                    )
            except Exception:
                logger.exception("Failed to write Arize fallback log.")


def _dispatch_stream_future(fut: Any, meta: dict[str, Any]) -> None:
    _finalize_arize_log_future(
        fut,
        prediction_id=meta["prediction_id"],
        model_name=meta["model_name"],
        model_version=meta["model_version"],
        fallback_path=meta["fallback_path"],
        safe_features=meta["safe_features"],
        safe_tags=meta["safe_tags"],
        prediction_label=meta["prediction_label"],
        actual_label=meta["actual_label"],
    )


class ArizeGateway:
    """Arize SDK adapter (legacy `Client.log` or `ArizeClient.log_stream`)."""

    def __init__(self) -> None:
        self._client: Any = None
        self._space_id: Optional[str] = None
        self._environment: Any = None
        self._enabled: bool = False
        self._fallback_path: Optional[str] = None
        self._sdk_backend: Optional[str] = None

    def init_app(self, app) -> None:
        """
        Read config/env vars and create the Arize client.

        Required:
            ARIZE_API_KEY, ARIZE_SPACE_KEY (or app.config equivalents)

        Optional:
            ARIZE_ENVIRONMENT – production | validation | training | staging | development
        """
        self._sdk_backend = None
        if app.config.get("TESTING"):
            logger.info("Arize monitoring disabled in testing mode.")
            return

        cfg = app.config
        if "ARIZE_ENABLED" in cfg:
            enabled_val = cfg["ARIZE_ENABLED"]
        else:
            enabled_val = os.environ.get("ARIZE_ENABLED", True)
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
                "Arize monitoring disabled: ARIZE_API_KEY and/or ARIZE_SPACE_KEY not set."
            )
            return

        env_name = (
            os.environ.get("ARIZE_ENVIRONMENT")
            or app.config.get("ARIZE_ENVIRONMENT", "PRODUCTION")
        ).upper()

        try:
            from arize.api import Client as LegacyArizeClient
            from arize.utils.types import Environments

            env_map = {
                "PRODUCTION": Environments.PRODUCTION,
                "VALIDATION": Environments.VALIDATION,
                "TRAINING": Environments.TRAINING,
                "STAGING": Environments.VALIDATION,
                "DEVELOPMENT": Environments.TRAINING,
            }
            self._environment = env_map.get(env_name, Environments.PRODUCTION)
            self._space_id = space_id
            self._client = LegacyArizeClient(space_id=space_id, api_key=api_key)
            self._sdk_backend = _SDK_BACKEND_LEGACY
            self._enabled = True
            logger.info(
                "Arize monitoring enabled via arize.api.Client (space_id=%s, environment=%s).",
                space_id,
                env_name,
            )
            return
        except Exception as e_legacy:
            logger.debug("arize.api.Client unavailable, trying ArizeClient: %s", e_legacy)

        try:
            from arize import ArizeClient
            from arize.ml.types import Environments

            env_map = {
                "PRODUCTION": Environments.PRODUCTION,
                "VALIDATION": Environments.VALIDATION,
                "TRAINING": Environments.TRAINING,
                "STAGING": Environments.VALIDATION,
                "DEVELOPMENT": Environments.TRAINING,
            }
            self._environment = env_map.get(env_name, Environments.PRODUCTION)
            self._space_id = space_id
            self._client = ArizeClient(api_key=api_key)
            self._sdk_backend = _SDK_BACKEND_ARIZE_CLIENT
            self._enabled = True
            logger.info(
                "Arize monitoring enabled via ArizeClient (arize 8.x, space_id=%s, environment=%s).",
                space_id,
                env_name,
            )
            return
        except Exception:
            logger.exception(
                "Failed to initialize Arize (tried arize.api.Client and ArizeClient). "
                "Monitoring disabled."
            )

    def log_inference(
        self,
        *args,
        **kwargs,
    ) -> None:
        """Log a single inference (legacy Client.log or ArizeClient.log_stream)."""
        if not self._enabled or self._client is None:
            return

        legacy_call = len(args) == 2 and not kwargs
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

        prediction_id = kwargs.get("prediction_id")
        model_name = kwargs.get("model_name")
        model_version = kwargs.get("model_version")
        model_type = kwargs.get("model_type")
        if not prediction_id or not model_name or not model_version:
            logger.warning("Arize logging skipped: missing required inference metadata.")
            return

        features = kwargs.get("features", {}) or {}
        prediction_label = kwargs.get("prediction_label")
        actual_label = kwargs.get("actual_label")
        timestamp = kwargs.get("timestamp")
        tags = kwargs.get("tags")

        safe_features: dict = {}
        safe_tags: Optional[dict] = None

        try:
            if self._sdk_backend == _SDK_BACKEND_ARIZE_CLIENT:
                self._log_inference_arize_client(
                    prediction_id=prediction_id,
                    model_name=model_name,
                    model_version=model_version,
                    model_type=model_type,
                    features=features,
                    prediction_label=prediction_label,
                    actual_label=actual_label,
                    timestamp=timestamp,
                    tags=tags,
                )
                return

            self._log_inference_legacy_api(
                prediction_id=prediction_id,
                model_name=model_name,
                model_version=model_version,
                model_type=model_type,
                features=features,
                prediction_label=prediction_label,
                actual_label=actual_label,
                timestamp=timestamp,
                tags=tags,
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

    def _log_inference_legacy_api(
        self,
        *,
        prediction_id: str,
        model_name: str,
        model_version: str,
        model_type: Any,
        features: Any,
        prediction_label: Any,
        actual_label: Any,
        timestamp: Any,
        tags: Any,
    ) -> None:
        try:
            from arize.utils.types import ModelTypes
        except ImportError:
            from arize.ml.types import ModelTypes

        model_type_map = {
            "REGRESSION": ModelTypes.REGRESSION,
            "BINARY_CLASSIFICATION": ModelTypes.BINARY_CLASSIFICATION,
            "SCORE_CATEGORICAL": ModelTypes.SCORE_CATEGORICAL,
            "NUMERIC": ModelTypes.NUMERIC,
        }
        arize_model_type = model_type_map.get(str(model_type).upper(), ModelTypes.REGRESSION)

        ts = timestamp or datetime.now()
        prediction_timestamp = int(ts.timestamp())

        safe_features = {
            k: (float(v) if isinstance(v, (int, float)) else str(v))
            for k, v in (features or {}).items()
        }
        safe_tags = None
        if tags:
            safe_tags = {
                k: (float(v) if isinstance(v, (int, float)) else str(v))
                for k, v in tags.items()
            }

        log_kwargs: dict[str, Any] = {
            "model_id": model_name,
            "model_type": arize_model_type,
            "environment": self._environment,
            "model_version": model_version,
            "prediction_id": prediction_id,
            "prediction_timestamp": prediction_timestamp,
            "prediction_label": prediction_label,
            "features": safe_features,
        }
        if actual_label is not None:
            log_kwargs["actual_label"] = actual_label
        if safe_tags:
            log_kwargs["tags"] = safe_tags

        logger.info(
            "Arize log dispatch (legacy) model_id=%s v=%s prediction_id=%s",
            model_name,
            model_version,
            prediction_id,
        )
        fut = self._client.log(**log_kwargs)

        wait = str(os.environ.get("ARIZE_LOG_WAIT", "")).lower() in ("1", "true", "yes")
        finisher = lambda f=fut: _finalize_arize_log_future(
            f,
            prediction_id=prediction_id,
            model_name=model_name,
            model_version=model_version,
            fallback_path=self._fallback_path,
            safe_features=safe_features,
            safe_tags=safe_tags,
            prediction_label=prediction_label,
            actual_label=actual_label,
        )
        if wait:
            finisher()
        else:
            threading.Thread(target=finisher, daemon=True).start()

    def _log_inference_arize_client(
        self,
        *,
        prediction_id: str,
        model_name: str,
        model_version: str,
        model_type: Any,
        features: Any,
        prediction_label: Any,
        actual_label: Any,
        timestamp: Any,
        tags: Any,
    ) -> None:
        from arize.ml.types import ModelTypes

        model_type_map = {
            "REGRESSION": ModelTypes.REGRESSION,
            "BINARY_CLASSIFICATION": ModelTypes.BINARY_CLASSIFICATION,
            "SCORE_CATEGORICAL": ModelTypes.SCORE_CATEGORICAL,
            "NUMERIC": ModelTypes.NUMERIC,
        }
        arize_model_type = model_type_map.get(str(model_type).upper(), ModelTypes.REGRESSION)

        ts = timestamp or datetime.now()
        prediction_timestamp = int(ts.timestamp())

        safe_features = {
            k: (float(v) if isinstance(v, (int, float)) else str(v))
            for k, v in (features or {}).items()
        }
        safe_tags = None
        if tags:
            safe_tags = {
                k: (float(v) if isinstance(v, (int, float)) else str(v))
                for k, v in tags.items()
            }

        effective_space_id = self._space_id or _normalize_arize_space_id(
            os.environ.get("ARIZE_SPACE_KEY") or os.environ.get("ARIZE_SPACE_ID") or ""
        )

        stream_kwargs: dict[str, Any] = {
            "space_id": effective_space_id,
            "model_name": model_name,
            "model_type": arize_model_type,
            "environment": self._environment,
            "model_version": model_version,
            "prediction_id": prediction_id,
            "prediction_timestamp": prediction_timestamp,
            "prediction_label": prediction_label,
            "actual_label": actual_label,
            "features": safe_features,
        }
        if safe_tags:
            stream_kwargs["tags"] = safe_tags

        logger.info(
            "Arize log_stream dispatch model=%s v=%s prediction_id=%s",
            model_name,
            model_version,
            prediction_id,
        )

        if hasattr(self._client, "log_stream"):
            fut = self._client.log_stream(**stream_kwargs)
        elif hasattr(self._client, "ml") and hasattr(self._client.ml, "log_stream"):
            fut = self._client.ml.log_stream(**stream_kwargs)
        else:
            raise RuntimeError("ArizeClient has no log_stream method.")

        wait = str(os.environ.get("ARIZE_LOG_WAIT", "")).lower() in ("1", "true", "yes")
        meta = {
            "prediction_id": prediction_id,
            "model_name": model_name,
            "model_version": model_version,
            "fallback_path": self._fallback_path,
            "safe_features": safe_features,
            "safe_tags": safe_tags,
            "prediction_label": prediction_label,
            "actual_label": actual_label,
        }
        target = lambda: _dispatch_stream_future(fut, meta)
        if wait:
            target()
        else:
            threading.Thread(target=target, daemon=True).start()


arize_gateway = ArizeGateway()
