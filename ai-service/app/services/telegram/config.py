from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

from app.core import config as core_config  # ensures .env is loaded


def _parse_chat_ids(raw: str | None) -> List[int]:
    if not raw:
        return []
    ids: List[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.append(int(part))
        except ValueError:
            continue
    return ids


@dataclass
class TelegramSettings:
    token: str
    backend_endpoint: str
    allowed_chat_ids: List[int]
    top_k: int = 3
    model_name: str = "orca-mini"
    use_rag: bool = True
    polling: bool = True

    @classmethod
    def from_env(cls) -> "TelegramSettings":
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN manquant dans l'environnement")

        backend = (
            os.getenv("TELEGRAM_BACKEND_ENDPOINT")
            or os.getenv("CRAWLER_BACKEND_ENDPOINT")
            or os.getenv("BACKEND_ENDPOINT")
            or "http://127.0.0.1:8000"
        )
        allowed = _parse_chat_ids(os.getenv("TELEGRAM_ALLOWED_CHAT_IDS"))
        top_k = int(os.getenv("TELEGRAM_TOP_K", "3"))
        model = os.getenv("TELEGRAM_MODEL_NAME", "orca-mini")
        use_rag = os.getenv("TELEGRAM_USE_RAG", "true").lower() == "true"
        polling = os.getenv("TELEGRAM_POLLING", "true").lower() == "true"
        return cls(
            token=token,
            backend_endpoint=backend,
            allowed_chat_ids=allowed,
            top_k=top_k,
            model_name=model,
            use_rag=use_rag,
            polling=polling,
        )

