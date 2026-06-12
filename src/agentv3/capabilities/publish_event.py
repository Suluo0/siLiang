"""
publish_interview_event capability — 发布面试事件到 MQ
"""
import json
import logging

logger = logging.getLogger(__name__)

_MQ_AVAILABLE = False
try:
    from src.common.rabbitmq import rabbitmq_publisher
    _MQ_AVAILABLE = True
except Exception:
    logger.warning("RabbitMQ 不可用，面试事件将仅记录日志")


async def publish_interview_event(event_data: dict) -> dict:
    """
    发布面试轮次完成事件到 MQ（异步 fire-and-forget）。

    Args:
        event_data: 包含 room_id, user_id, round_number, topic_id, scores, missing_points 等

    Returns:
        {"published": bool, "method": "mq" | "log"}
    """
    payload = {
        "event_type": "interview.round.completed",
        "data": event_data,
    }

    if _MQ_AVAILABLE:
        try:
            await rabbitmq_publisher.send_task("interview.round.completed", payload)
            return {"published": True, "method": "mq"}
        except Exception as e:
            logger.warning(f"MQ 发布失败，降级到日志: {e}")

    logger.info(f"[Interview Event] {json.dumps(payload, ensure_ascii=False)}")
    return {"published": True, "method": "log"}
