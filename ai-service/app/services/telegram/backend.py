from __future__ import annotations

import httpx

from app.schemas.article import RAGResponse


class BackendResponder:
    def __init__(self, base_url: str, top_k: int = 3, use_rag: bool = True):
        self.base_url = base_url.rstrip("/")
        self.top_k = top_k
        self.use_rag = use_rag
        # Augmente le timeout pour éviter les ReadTimeout côté LLM/RAG
        self._client = httpx.AsyncClient(timeout=60)

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

    async def answer_stream(self, query: str):
        """Consommer l'endpoint RAG streaming (JSONL) et renvoyer summary + sources."""
        if not self.use_rag:
            return await self.answer(query)

        url = f"{self.base_url}/rag/stream"
        payload = {"query": query, "top_k": self.top_k}

        summary_parts = []
        sources = []
        async with self._client.stream("POST", url, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                try:
                    data = httpx.Response(200, content=line).json()
                except Exception:
                    continue
                if data.get("type") == "sources":
                    sources = data.get("sources", [])
                elif data.get("type") == "summary_chunk":
                    txt = data.get("text")
                    if txt:
                        summary_parts.append(txt)
                elif data.get("type") == "done":
                    break

        summary = ". ".join(summary_parts)
        return {
            "summary": summary,
            "sources": sources,
            "num_sources": len(sources),
            "query": query,
        }

