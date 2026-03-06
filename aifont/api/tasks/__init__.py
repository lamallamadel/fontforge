"""Celery application factory."""

from __future__ import annotations

from celery import Celery

from aifont.api.config import get_settings


def create_celery_app() -> Celery:
    settings = get_settings()
    app = Celery(
        "aifont",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
    )
    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
    )
    app.autodiscover_tasks(["aifont.api.tasks"])
    return app


celery_app = create_celery_app()
