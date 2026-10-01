"""Celery transport; database job state and ownership remain in the modular API."""

from celery import Celery
from sqlalchemy.exc import OperationalError

from services.api.config import get_settings

app = Celery("otcaselab", broker=get_settings().redis_url)
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=180,
    task_soft_time_limit=160,
    broker_connection_retry_on_startup=True,
)


@app.task(name="otcaselab.process_job", bind=True, max_retries=2)
def process_job(self, job_id: str):
    from services.api.jobs import JobLeaseBusy, execute_job

    # execute_job rechecks ownership, allowed input, deduplication, and state.
    try:
        return execute_job(job_id)
    except JobLeaseBusy as exc:
        raise self.retry(exc=exc, countdown=exc.retry_after, max_retries=2)
    except (ConnectionError, OperationalError) as exc:
        raise self.retry(exc=exc, countdown=3 * (2**self.request.retries), max_retries=2)
