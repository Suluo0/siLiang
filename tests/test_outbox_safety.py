"""R-006 Outbox 退避、降级和重放安全测试。"""
import asyncio
import uuid

import pytest

from src.models.outbox import Outbox
from src.models.topic import Topic
from src.tools.embedding import EmbeddingEncoder
from src.workers.outbox_worker import (
    MAX_BACKOFF_SECONDS,
    _dead_letter,
    claim_batch,
    replay_dead_letter,
    retry_delay_seconds,
)

pytestmark = pytest.mark.fault


@pytest.mark.unit
def test_retry_backoff_is_bounded_and_increasing():
    values = [retry_delay_seconds(value) for value in range(10)]
    assert values == sorted(values)
    assert values[-1] <= MAX_BACKOFF_SECONDS


@pytest.mark.unit
def test_missing_embedding_credentials_raise(monkeypatch):
    encoder = EmbeddingEncoder()
    encoder.api_key = ""
    with pytest.raises(RuntimeError):
        encoder.encode("non-empty")


async def _topic() -> Topic:
    return await Topic.create(
        id=uuid.uuid4(),
        topic="Outbox safety",
        domain="backend",
        difficulty=3,
        status="MILVUS_PENDING",
    )


@pytest.mark.integration
async def test_dead_letter_preserves_truth_data_and_can_be_replayed(db):
    topic = await _topic()
    event = await Outbox.create(
        event_type="TOPIC_CREATED",
        payload={"topic_id": str(topic.id)},
        status="PROCESSING",
        worker_id="worker-a",
    )

    await _dead_letter(event, "milvus unavailable", retry_count=5)

    assert await Topic.filter(id=topic.id).exists()
    await topic.refresh_from_db()
    await event.refresh_from_db()
    assert topic.status == "MILVUS_FAILED"
    assert event.status == "DEAD_LETTER"
    assert event.retry_count == 5

    assert await replay_dead_letter(str(event.id)) is True
    await event.refresh_from_db()
    assert event.status == "PENDING"
    assert event.retry_count == 0


@pytest.mark.integration
@pytest.mark.concurrency
async def test_two_workers_claim_each_event_at_most_once(db):
    topic = await _topic()
    event = await Outbox.create(
        event_type="TOPIC_CREATED",
        payload={"topic_id": str(topic.id)},
        status="PENDING",
    )

    first, second = await asyncio.gather(claim_batch("worker-a"), claim_batch("worker-b"))
    claimed_ids = [str(item.id) for batch in (first, second) for item in batch]

    assert claimed_ids == [str(event.id)]
    await event.refresh_from_db()
    assert event.status == "PROCESSING"
    assert event.worker_id in {"worker-a", "worker-b"}
