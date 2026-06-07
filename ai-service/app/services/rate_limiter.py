import logging
import os
import redis.asyncio as redis
from app.core.config import REDIS_URL

logger = logging.getLogger(__name__)

_redis = redis.from_url(REDIS_URL, decode_responses=True)

# Limites par défaut (surchargeables via env)
_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "10"))
_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))


async def is_rate_limited(chat_id: str, platform: str = "default") -> bool:
    """
    Sliding window counter par (platform, chat_id).
    Retourne True si la limite est atteinte — le message doit être silencieusement ignoré.
    """
    key = f"ratelimit:{platform}:{chat_id}"
    try:
        pipe = _redis.pipeline()
        await pipe.incr(key)
        await pipe.expire(key, _WINDOW_SECONDS)
        results = await pipe.execute()
        count = results[0]
        if count > _MAX_REQUESTS:
            logger.warning(
                "[RateLimit] %s:%s — %s requêtes / %ss (limite=%s)",
                platform, chat_id[:40], count, _WINDOW_SECONDS, _MAX_REQUESTS,
            )
            return True
        return False
    except Exception as e:
        # En cas d'erreur Redis, on laisse passer pour ne pas bloquer les utilisateurs légitimes
        logger.error("[RateLimit] Erreur Redis pour %s:%s — %s", platform, chat_id[:40], e)
        return False
