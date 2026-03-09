from celery import Celery
from app.config import settings

celery = Celery("cocivil", broker=settings.REDIS_URL, backend=settings.REDIS_URL)
celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=300,
    task_time_limit=600,
)
celery.conf.include = [
    "app.tasks.plan",
    "app.tasks.ingestion",
    "app.tasks.finance",
    "app.tasks.export",
    "app.tasks.entitlement",
    "app.tasks.layout",
    "app.tasks.massing",
    "app.tasks.document_analysis",
    "app.tasks.infrastructure_ingestion",
]
