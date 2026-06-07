"""Tests pour le cache Redis des réponses RAG — Redis mocké."""
import sys
import os
import json
import pytest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.mark.asyncio
async def test_cache_miss_returns_none():
    with patch("app.services.response_cache._redis") as mock_redis:
        mock_redis.get = AsyncMock(return_value=None)
        from app.services.response_cache import get_cached
        result = await get_cached("question test", "whatsapp")
        assert result is None


@pytest.mark.asyncio
async def test_cache_hit_returns_parsed_dict():
    payload = json.dumps({"verdict": "VRAI", "sources": [{"id": 1, "title": "Test"}]})
    with patch("app.services.response_cache._redis") as mock_redis:
        mock_redis.get = AsyncMock(return_value=payload)
        from app.services.response_cache import get_cached
        result = await get_cached("question test", "whatsapp")
        assert result is not None
        assert result["verdict"] == "VRAI"
        assert len(result["sources"]) == 1


@pytest.mark.asyncio
async def test_set_cached_calls_setex():
    with patch("app.services.response_cache._redis") as mock_redis:
        mock_redis.setex = AsyncMock()
        from app.services.response_cache import set_cached
        await set_cached("question", "telegram", "verdict ici", [])
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        # La clé doit commencer par "ragcache:"
        assert call_args[0][0].startswith("ragcache:")
        # Le TTL doit être positif
        assert call_args[0][1] > 0


@pytest.mark.asyncio
async def test_cache_disabled_skips_redis():
    with patch.dict(os.environ, {"RESPONSE_CACHE_ENABLED": "false"}):
        # Recharger le module pour appliquer la nouvelle valeur d'env
        import importlib
        import app.services.response_cache as rc_module
        importlib.reload(rc_module)
        with patch.object(rc_module, "_redis") as mock_redis:
            mock_redis.get = AsyncMock(return_value="should_not_be_called")
            result = await rc_module.get_cached("question", "web")
            mock_redis.get.assert_not_called()
            assert result is None
        # Remettre le module dans son état normal
        importlib.reload(rc_module)


@pytest.mark.asyncio
async def test_redis_error_returns_none_gracefully():
    with patch("app.services.response_cache._redis") as mock_redis:
        mock_redis.get = AsyncMock(side_effect=ConnectionError("Redis down"))
        from app.services.response_cache import get_cached
        result = await get_cached("question", "web")
        assert result is None
