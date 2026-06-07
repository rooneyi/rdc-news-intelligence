"""Tests pour le rate limiter Redis — Redis mocké."""
import sys
import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.mark.asyncio
async def test_first_request_not_limited():
    with patch("app.services.rate_limiter._redis") as mock_redis:
        mock_pipe = AsyncMock()
        mock_pipe.execute = AsyncMock(return_value=[1, True])  # count=1
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)
        from app.services.rate_limiter import is_rate_limited
        result = await is_rate_limited("user123", "telegram")
        assert result is False


@pytest.mark.asyncio
async def test_exceeds_limit_returns_true():
    with patch("app.services.rate_limiter._redis") as mock_redis:
        with patch.dict(os.environ, {"RATE_LIMIT_MAX_REQUESTS": "5"}):
            mock_pipe = AsyncMock()
            mock_pipe.execute = AsyncMock(return_value=[11, True])  # count=11 > 5
            mock_redis.pipeline = MagicMock(return_value=mock_pipe)

            import importlib
            import app.services.rate_limiter as rl
            importlib.reload(rl)

            result = await rl.is_rate_limited("user123", "whatsapp")
            assert result is True
            importlib.reload(rl)


@pytest.mark.asyncio
async def test_redis_error_does_not_block_user():
    with patch("app.services.rate_limiter._redis") as mock_redis:
        mock_pipe = AsyncMock()
        mock_pipe.execute = AsyncMock(side_effect=ConnectionError("Redis down"))
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)
        from app.services.rate_limiter import is_rate_limited
        result = await is_rate_limited("user123", "telegram")
        # En cas d'erreur Redis, on laisse passer
        assert result is False


@pytest.mark.asyncio
async def test_different_platforms_isolated():
    counts = {"telegram:user1": 1, "whatsapp:meta:user1": 1}

    async def fake_execute():
        return [1, True]

    with patch("app.services.rate_limiter._redis") as mock_redis:
        mock_pipe = AsyncMock()
        mock_pipe.execute = AsyncMock(side_effect=fake_execute)
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)
        from app.services.rate_limiter import is_rate_limited
        tg = await is_rate_limited("user1", "telegram")
        wa = await is_rate_limited("user1", "whatsapp:meta")
        assert tg is False
        assert wa is False
