import logging

from celery import Celery
from celery.signals import task_failure, worker_ready, worker_shutdown

from data5580_hw.config import Config

logger = logging.getLogger(__name__)

celery_app = Celery("data5580_hw")

# Ensure worker has sane defaults even when started without Flask app factory.
_default_cfg = Config()
celery_app.conf.update(
    broker_url=_default_cfg.CELERY_BROKER_URL,
    result_backend=_default_cfg.CELERY_RESULT_BACKEND,
    task_track_started=_default_cfg.CELERY_TASK_TRACK_STARTED,
    task_time_limit=_default_cfg.CELERY_TASK_TIME_LIMIT,
    task_soft_time_limit=_default_cfg.CELERY_TASK_SOFT_TIME_LIMIT,
    task_default_retry_delay=_default_cfg.CELERY_TASK_DEFAULT_RETRY_DELAY,
    task_annotations={"*": {"max_retries": _default_cfg.CELERY_TASK_MAX_RETRIES}},
    result_expires=_default_cfg.CELERY_RESULT_EXPIRES,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    imports=("data5580_hw.tasks.jobs",),
)


def init_celery(app) -> Celery:
    """
    Bind Celery config to the Flask app and ensure tasks run with app context.
    """

    celery_app.conf.update(
        broker_url=app.config["CELERY_BROKER_URL"],
        result_backend=app.config["CELERY_RESULT_BACKEND"],
        task_track_started=app.config["CELERY_TASK_TRACK_STARTED"],
        task_time_limit=app.config["CELERY_TASK_TIME_LIMIT"],
        task_soft_time_limit=app.config["CELERY_TASK_SOFT_TIME_LIMIT"],
        task_default_retry_delay=app.config["CELERY_TASK_DEFAULT_RETRY_DELAY"],
        task_annotations={"*": {"max_retries": app.config["CELERY_TASK_MAX_RETRIES"]}},
        result_expires=app.config["CELERY_RESULT_EXPIRES"],
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        imports=("data5580_hw.tasks.jobs",),
    )

    class FlaskTask(celery_app.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app.Task = FlaskTask
    return celery_app


@worker_ready.connect
def _on_worker_ready(sender=None, **kwargs):
    logger.info("Celery worker started: %s", sender)


@worker_shutdown.connect
def _on_worker_shutdown(sender=None, **kwargs):
    logger.info("Celery worker shutting down: %s", sender)


@task_failure.connect
def _on_task_failure(task_id=None, exception=None, traceback=None, sender=None, **kwargs):
    logger.error(
        "Celery task failed task_id=%s task=%s error=%s",
        task_id,
        getattr(sender, "name", "unknown"),
        exception,
    )
