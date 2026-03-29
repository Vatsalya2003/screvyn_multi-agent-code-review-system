"""
Celery configuration — connects to Redis and registers tasks.

Why Celery?
    GitHub expects a webhook response within 10 seconds.
    Your 4-agent review takes ~28 seconds. Celery lets you:
    1. Accept the webhook instantly (return 202 in <200ms)
    2. Run the review in a background worker process
    3. Post the comment when it's done

    This is the same pattern used at every major tech company
    for handling async workloads.

How to run:
    # Terminal 1: start the worker
    celery -A celery_app worker --loglevel=info --concurrency=2

    # Terminal 2: start FastAPI
    uvicorn main:app --reload --port 8000
"""

import os

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

app = Celery(
    "screvyn",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["tasks.review_task"],
)

# Celery configuration
app.conf.update(
    # Serialization — use JSON so payloads are human-readable in Redis
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Task settings
    task_acks_late=True,           # ack AFTER task completes (crash safety)
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,  # fetch 1 task at a time (fair scheduling)

    # Result backend — store results for 24 hours (frontend can poll)
    result_expires=86400,

    # Retry — if Redis drops the connection, retry before crashing
    broker_connection_retry_on_startup=True,

    # Task time limits
    task_soft_time_limit=120,   # soft limit: 2 min (raises SoftTimeLimitExceeded)
    task_time_limit=150,        # hard kill: 2.5 min
)
