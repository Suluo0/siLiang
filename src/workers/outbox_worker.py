"""
Outbox 补偿消费者 — 后台定时任务
每 30 秒消费 PENDING 状态的 Outbox 记录，重试 Milvus 写入
"""
import asyncio
from datetime import datetime, timezone
from src.tools.embedding import EmbeddingEncoder
from src.tools.milvus_client import MilvusClient
from src.models.outbox import Outbox

MAX_RETRIES = 3
POLL_INTERVAL = 30


async def outbox_worker():
    """Outbox 补偿循环"""
    while True:
        try:
            pending = await Outbox.filter(
                status="PENDING",
                retry_count__lt=MAX_RETRIES,
            ).limit(10)

            for event in pending:
                try:
                    payload = event.payload
                    topic_id = payload.get("topic_id", "")
                    core_concept = payload.get("core_concept", "")

                    encoder = EmbeddingEncoder.get_instance()
                    vector = encoder.encode(core_concept)
                    milvus = MilvusClient.get_instance()
                    milvus.insert(
                        topic_id=topic_id,
                        core_concept=core_concept,
                        embedding=vector.tolist(),
                        domain=payload.get("domain", ""),
                        keywords=payload.get("keywords", ""),
                        difficulty=payload.get("difficulty", 3),
                    )

                    event.status = "PROCESSED"
                    event.processed_at = datetime.now(timezone.utc)
                except Exception as e:
                    event.retry_count += 1
                    event.error_message = str(e)[:500]
                    if event.retry_count >= MAX_RETRIES:
                        event.status = "FAILED"
                        event.processed_at = datetime.now(timezone.utc)

                await event.save()

        except Exception:
            pass

        await asyncio.sleep(POLL_INTERVAL)


def start_outbox_worker():
    """启动 Outbox 后台任务"""
    loop = asyncio.get_event_loop()
    loop.create_task(outbox_worker())
