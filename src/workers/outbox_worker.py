"""Outbox worker：claim/lease、有界批次、指数退避和 dead-letter。"""
import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

import numpy as np
from tortoise.transactions import in_transaction

from src.models.outbox import Outbox
from src.models.topic import Topic
from src.tools.embedding import EmbeddingEncoder
from src.tools.milvus_client import MilvusClient
from src.utils.mail import ALERT_EMAIL, send_alert

logger = logging.getLogger("outbox_worker")

MAX_RETRIES = 5
BATCH_SIZE = 50
LEASE_SECONDS = 120
POLL_INTERVAL = 5
MAX_BACKOFF_SECONDS = 3600


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def retry_delay_seconds(retry_count: int) -> int:
    return min(2 ** max(retry_count, 0) * 30, MAX_BACKOFF_SECONDS)


async def claim_batch(worker_id: str) -> list[Outbox]:
    """用 SKIP LOCKED 原子 claim 一批到期任务。"""
    now = _utcnow()
    async with in_transaction() as connection:
        rows = await Outbox.filter(
            status="PENDING", next_retry_at__lte=now,
        ).using_db(connection).select_for_update(skip_locked=True).limit(BATCH_SIZE)
        if len(rows) < BATCH_SIZE:
            unleased = await Outbox.filter(
                status="PENDING", next_retry_at=None,
            ).using_db(connection).select_for_update(skip_locked=True).limit(BATCH_SIZE - len(rows))
            rows.extend(unleased)
        for row in rows:
            row.status = "PROCESSING"
            row.worker_id = worker_id
            row.lease_until = now + timedelta(seconds=LEASE_SECONDS)
            await row.save(using_db=connection, update_fields=["status", "worker_id", "lease_until", "updated_at"])
        return rows


async def reclaim_expired_leases() -> int:
    return await Outbox.filter(status="PROCESSING", lease_until__lt=_utcnow()).update(
        status="PENDING", worker_id=None, lease_until=None,
    )


async def process_one(record: Outbox) -> None:
    topic_id = str(record.payload.get("topic_id", ""))
    topic = await Topic.filter(id=topic_id).first()
    if not topic:
        await _dead_letter(record, "Topic not found in PostgreSQL")
        return

    try:
        core_concept = record.payload.get("core_concept", topic.core_summary or "")
        vector = EmbeddingEncoder.get_instance().encode(core_concept)
        if not np.isfinite(vector).all() or float(np.linalg.norm(vector)) == 0:
            raise RuntimeError("embedding is zero or non-finite")
        MilvusClient.get_instance().insert(
            topic_id=topic_id, core_concept=core_concept, embedding=vector.tolist(),
            domain=record.payload.get("domain", topic.domain or ""),
            keywords=record.payload.get("keywords", topic.keywords or ""),
            difficulty=record.payload.get("difficulty", topic.difficulty or 3),
        )
    except Exception as exc:
        await _schedule_retry(record, exc)
        return

    await Outbox.filter(id=record.id, status="PROCESSING", worker_id=record.worker_id).update(
        status="PROCESSED", processed_at=_utcnow(), lease_until=None, worker_id=None,
        error_message=None,
    )
    await Topic.filter(id=topic_id).update(status="ACTIVE")


async def _schedule_retry(record: Outbox, exc: Exception) -> None:
    retry_count = record.retry_count + 1
    message = f"{type(exc).__name__}: {exc}"[:500]
    if retry_count >= MAX_RETRIES:
        await _dead_letter(record, message, retry_count=retry_count)
        return
    await Outbox.filter(id=record.id, status="PROCESSING", worker_id=record.worker_id).update(
        status="PENDING", retry_count=retry_count, error_message=message,
        next_retry_at=_utcnow() + timedelta(seconds=retry_delay_seconds(retry_count)),
        lease_until=None, worker_id=None,
    )


async def _dead_letter(record: Outbox, message: str, retry_count: int | None = None) -> None:
    topic_id = str(record.payload.get("topic_id", ""))
    await Outbox.filter(id=record.id).update(
        status="DEAD_LETTER", retry_count=retry_count if retry_count is not None else record.retry_count,
        error_message=message[:500], lease_until=None, worker_id=None,
    )
    if topic_id:
        await Topic.filter(id=topic_id).update(status="MILVUS_FAILED")
    logger.error("Outbox moved to dead-letter: event=%s topic=%s error=%s", record.id, topic_id, message)
    if ALERT_EMAIL:
        try:
            send_alert("[TopicSystem] Outbox dead-letter", f"event={record.id} topic={topic_id}")
        except Exception:
            logger.exception("Outbox dead-letter alert failed")


async def replay_dead_letter(event_id: str) -> bool:
    return await Outbox.filter(id=event_id, status="DEAD_LETTER").update(
        status="PENDING", retry_count=0, error_message=None, next_retry_at=None,
    ) == 1


async def run_outbox_worker(stop_event: asyncio.Event | None = None) -> None:
    worker_id = str(uuid.uuid4())
    stop_event = stop_event or asyncio.Event()
    logger.info("Outbox worker started: %s", worker_id)
    while not stop_event.is_set():
        try:
            await reclaim_expired_leases()
            for record in await claim_batch(worker_id):
                await process_one(record)
        except Exception:
            logger.exception("Outbox worker round failed")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=POLL_INTERVAL)
        except TimeoutError:
            pass
    logger.info("Outbox worker stopped: %s", worker_id)
