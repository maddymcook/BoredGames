"""
Gateway for Arize model monitoring integration.

Initialized once at app startup via init_app(app). Call log_inference()
after each prediction. All errors are caught and logged locally so that
a monitoring failure never breaks the prediction response.
"""
import logging
import os
from datetime import datetime
from typing import Optional, Union

logger = logging.getLogger(__name__)


class ArizeGateway:
    """Wraps the Arize MLModelsClient and exposes a single log_inference method."""

    def __init__(self) -> None:
        self._client = None
        self._space_id: Optional[str] = None
        self._environment = None
        self._enabled: bool = False

    def init_app(self, app) -> None:
        """
        Read config/env vars and create the Arize client.

        Required env vars (or app.config keys):
            ARIZE_API_KEY   – your Arize API key
            ARIZE_SPACE_ID  – your Arize space ID

        Optional:
            ARIZE_ENVIRONMENT – PRODUCTION | VALIDATION | TRAINING (default: PRODUCTION)
        """
        api_key = os.environ.get("ARIZE_API_KEY") or app.config.get("ARIZE_API_KEY")
        space_id = os.environ.get("ARIZE_SPACE_ID") or app.config.get("ARIZE_SPACE_ID")

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
            from arize import ArizeClient
            from arize.ml.types import Environments

            env_map = {
                "PRODUCTION": Environments.PRODUCTION,
                "VALIDATION": Environments.VALIDATION,
                "TRAINING": Environments.TRAINING,
            }
            self._environment = env_map.get(env_name, Environments.PRODUCTION)
            self._space_id = space_id

            arize_client = ArizeClient(api_key=api_key)
            self._client = arize_client.ml

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
        *,
        prediction_id: str,
        model_name: str,
        model_version: str,
        model_type: str,
        features: dict,
        prediction_label: Union[str, int, float],
        actual_label: Union[str, int, float, None] = None,
        timestamp: Optional[datetime] = None,
        tags: Optional[dict] = None,
    ) -> None:
        """
        Log a single inference to Arize asynchronously.

        Errors are swallowed so that a monitoring failure never affects
        the prediction response returned to the caller.
        """
        if not self._enabled or self._client is None:
            return

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

            self._client.log_stream(
                space_id=self._space_id,
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

            logger.debug(
                "Arize inference logged (prediction_id=%s, model=%s v%s).",
                prediction_id,
                model_name,
                model_version,
            )

        except Exception:
            logger.exception(
                "Arize logging failed for prediction_id=%s. Data not sent.",
                prediction_id,
            )


arize_gateway = ArizeGateway()
