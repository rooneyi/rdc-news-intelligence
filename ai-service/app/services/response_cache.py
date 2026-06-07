import hashlib
import json
import logging
import os
import redis.asyncio as aioredis
from app.core.config import REDIS_URL

logger = logging.getLogger(__name__)

try:
    from app.services.metrics import CACHE_HITS, CACHE_MISSES
except ImportError:
    CACHE_HITS = CACHE_MISSES = None  # type: ignore[assignment]

_TTL = int(os.getenv("RESPONSE_CACHE_TTL", "1800"))  # 30 min par défaut
_ENABLED = os.getenv("RESPONSE_CACHE_ENABLED", "true").lower() not in {"0", "false", "no", "off"}

_redis = aioredis.from_url(REDIS_URL, decode_responses=True)


def _key(query: str, channel: str) -> str:
    digest = hashlib.sha256(f"{channel}:{query.lower().strip()}".encode()).hexdigest()
    return f"ragcache:{digest}"


async def get_cached(query: str, channel: str) -> dict | None:
    """Retourne le résultat mis en cache ou None."""
    if not _ENABLED or _TTL <= 0:
        return None
    try:
        raw = await _redis.get(_key(query, channel))
        if raw:
            logger.info("[ResponseCache] Cache hit (canal=%s): %.60s", channel, query)
            if CACHE_HITS is not None:
                CACHE_HITS.labels(channel=channel).inc()
            return json.loads(raw)
    except Exception as e:
        logger.debug("[ResponseCache] Lecture échouée: %s", e)
    if CACHE_MISSES is not None:
        CACHE_MISSES.labels(channel=channel).inc()
    return None


async def set_cached(query: str, channel: str, verdict: str, sources: list) -> None:
    """Sauvegarde un résultat RAG en cache."""
    if not _ENABLED or _TTL <= 0:
        return
    try:
        payload = json.dumps({"verdict": verdict, "sources": sources})
        await _redis.setex(_key(query, channel), _TTL, payload)
        logger.debug("[ResponseCache] Mis en cache (canal=%s, ttl=%ss): %.60s", channel, _TTL, query)
    except Exception as e:
        logger.debug("[ResponseCache] Écriture échouée: %s", e)
