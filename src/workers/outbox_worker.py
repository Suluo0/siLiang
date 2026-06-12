"""
Outbox 补偿 Worker —— 后台任务
- 轮询 outbox 表，重试失败的 Milvus 写入（最多 3 次）
- 3 次仍失败 → 邮件告警 + 回滚 PG 数据
- 定时清理 7 天前的 CANCELLED 数据（物理删除）
"""
import asyncio
import logging
from datetime import datetime, timedelta

from src.models.topic import Topic
from src.models.outbox import Outbox
from src.models.topic_prerequisite import TopicPrerequisite
from src.models.topic_core_concept import TopicCoreConcept
from src.models.topic_derivative import TopicDerivative
from src.models.topic_extension import TopicExtension
from src.models.topic_evaluation_anchor import TopicEvaluationAnchor
from src.models.topic_similar_question import TopicSimilarQuestion
from src.models.topic_advanced_question import TopicAdvancedQuestion
from src.models.topic_reference import TopicReference
from src.models.topic_review_log import TopicReviewLog
from src.models.user_topic_progress import UserTopicProgress
from src.models.user_topic_status import UserTopicStatus
from src.tools.embedding import EmbeddingEncoder
from src.tools.milvus_client import MilvusClient
from src.utils.mail import send_alert, ALERT_EMAIL
from tortoise.transactions import in_transaction

logger = logging.getLogger("outbox_worker")

MAX_RETRIES = 3
POLL_INTERVAL = 30
CLEANUP_INTERVAL = 3600       # 每小时清理一次
CANCELLED_RETENTION_DAYS = 7

_RELATED_MODELS = [
    TopicPrerequisite, TopicCoreConcept, TopicDerivative,
    TopicExtension, TopicEvaluationAnchor, TopicSimilarQuestion,
    TopicAdvancedQuestion, TopicReference, TopicReviewLog,
    UserTopicProgress, UserTopicStatus,
]


async def _process_one(record: Outbox):
    payload = record.payload
    topic_id = payload.get("topic_id", "")

    topic = await Topic.filter(id=topic_id).first()
    if not topic:
        record.status = "FAILED"
        record.error_message = "Topic not found in PG"
        await record.save()
        return

    domain = payload.get("domain", topic.domain or "")
    keywords = payload.get("keywords", "")
    if not keywords and topic.keywords:
        keywords = ",".join(topic.keywords) if isinstance(topic.keywords, list) else topic.keywords
    difficulty = payload.get("difficulty", topic.difficulty or 3)
    core_concept = payload.get("core_concept", topic.core_summary or "")

    try:
        encoder = EmbeddingEncoder.get_instance()
        vector = encoder.encode(core_concept)
        milvus = MilvusClient.get_instance()
        milvus.insert(
            topic_id=topic_id, core_concept=core_concept,
            embedding=vector.tolist(), domain=domain,
            keywords=keywords, difficulty=difficulty,
        )
        record.status = "PROCESSED"
        record.processed_at = datetime.now()
        await record.save()
        await Topic.filter(id=topic_id).update(status="ACTIVE")
        logger.info(f"Outbox compensated: {topic_id}")
        return
    except Exception as e:
        record.error_message = str(e)[:500]

    record.retry_count += 1

    if record.retry_count >= MAX_RETRIES:
        record.status = "FAILED"
        await record.save()
        _send_alert(topic_id, record.error_message or "")
        await _rollback_topic(topic_id)
        logger.warning(f"Outbox exhausted retries, rolled back: {topic_id}")
    else:
        await record.save()


def _send_alert(topic_id: str, error_msg: str):
    if not ALERT_EMAIL:
        return
    try:
        send_alert(
            subject=f"[TopicSystem] Milvus 补偿失败 - {topic_id}",
            body=f"Topic {topic_id} 写入 Milvus 重试 {MAX_RETRIES} 次后仍失败，"
                 f"已回滚 PG 数据。\n错误: {error_msg}",
        )
    except Exception:
        pass


async def _rollback_topic(topic_id: str):
    async with in_transaction():
        for model_cls in _RELATED_MODELS:
            await model_cls.filter(topic_id=topic_id).delete()
        await Topic.filter(id=topic_id).delete()
    logger.info(f"Rolled back topic: {topic_id}")


async def _cleanup_cancelled():
    cutoff = datetime.now() - timedelta(days=CANCELLED_RETENTION_DAYS)
    cancelled = await Topic.filter(status="CANCELLED", updated_at__lte=cutoff).all()
    if not cancelled:
        return
    async with in_transaction():
        for topic in cancelled:
            for model_cls in _RELATED_MODELS:
                await model_cls.filter(topic_id=topic.id).delete()
            await topic.delete()
    logger.info(f"Cleaned up {len(cancelled)} cancelled topics older than {CANCELLED_RETENTION_DAYS} days")


async def run_outbox_worker():
    logger.info("Outbox worker started")
    last_cleanup = datetime.min

    while True:
        try:
            pending = await Outbox.filter(status="PENDING").all()
            for record in pending:
                await _process_one(record)
        except Exception as e:
            logger.error(f"Outbox worker round failed: {e}")

        try:
            now = datetime.now()
            if (now - last_cleanup).total_seconds() >= CLEANUP_INTERVAL:
                await _cleanup_cancelled()
                last_cleanup = now
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

        await asyncio.sleep(POLL_INTERVAL)
