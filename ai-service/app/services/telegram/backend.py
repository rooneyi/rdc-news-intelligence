from __future__ import annotations

import httpx

from app.schemas.article import RAGResponse


class BackendResponder:
    def __init__(self, base_url: str, top_k: int = 3, use_rag: bool = True):
        self.base_url = base_url.rstrip("/")
        self.top_k = top_k
        self.use_rag = use_rag
        self._client = httpx.AsyncClient(timeout=20)

    async def close(self) -> None:
        await self._client.aclose()

    async def answer(self, query: str) -> RAGResponse | dict:
        if self.use_rag:
            url = f"{self.base_url}/rag"
            payload = {"query": query, "top_k": self.top_k}
        else:
            url = f"{self.base_url}/query"
            payload = {"query": query}
        resp = await self._client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()

