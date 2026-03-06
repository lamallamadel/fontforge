"""Celery application configuration for AIFont workers."""

import os

from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://cache:6379/0")

celery_app = Celery(
    "aifont_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["aifont.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)
