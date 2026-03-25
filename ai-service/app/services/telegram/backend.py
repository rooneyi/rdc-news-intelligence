from __future__ import annotations

import httpx
import json
import logging
from app.schemas.article import RAGResponse

logger = logging.getLogger(__name__)

class BackendResponder:
    def __init__(self, base_url: str, top_k: int = 3, use_rag: bool = True):
        # On s'assure que l'URL est propre
        self.base_url = base_url.rstrip("/")
        self.top_k = top_k
        self.use_rag = use_rag
        
        # On sépare les timeouts : 
        # connect=10s (pour savoir vite si le serveur est éteint)
        # read=120s (pour laisser Mistral générer le texte)
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(1200.0, connect=60.0))

    async def close(self) -> None:
        await self._client.aclose()

    async def answer(self, query: str) -> RAGResponse | dict:
        try:
            url = f"{self.base_url}/rag"
            payload = {"query": query, "top_k": self.top_k}
            resp = await self._client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Backend connection error: {e}")
            raise

    async def answer_stream(self, query: str):
        # Cette méthode est maintenant gérée directement dans bot.py 
        # pour profiter du streaming réel sur Telegram
        pass
