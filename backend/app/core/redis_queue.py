"""Redis queue client (C2: uses REDIS_QUEUE_URL for queue/Pub/Sub operations).

Only the queue Redis (AOF persistence) should be used for Pub/Sub and task queues.
The cache Redis (RDB) should only be used for ephemeral cache data.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

_NOTIFICATION_CHANNEL = "notification:events"


async def get_queue_redis() -> aioredis.Redis:
    """Get an async Redis connection to the queue instance."""
    return aioredis.from_url(
        settings.REDIS_QUEUE_URL,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )


async def publish_notification(event_data: dict[str, Any]) -> None:
    """Publish a notification event to the queue Redis Pub/Sub channel.
    
    In a multi-process deployment, all backend instances subscribe to
    this channel and forward events to their local WebSocket connections.
    """
    try:
        r = await get_queue_redis()
        await r.publish(_NOTIFICATION_CHANNEL, json.dumps(event_data, default=str))
        await r.aclose()
    except Exception as exc:
        logger.warning("Failed to publish notification to queue Redis: %s", exc)
