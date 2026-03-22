import os
import httpx
import logging
from typing import List
from app.schemas.article import ArticleOut

logger = logging.getLogger(__name__)


class LLMService:
    """Client simple pour un LLM exposé via Ollama (HTTP /api/generate)."""

    def __init__(self, model: str | None = None, host: str | None = None, timeout: int | None = None):
        self.model = model or os.getenv("OLLAMA_MODEL", "mistral")
        self.host = host or os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        # Timeout plus court par défaut pour éviter les blocages avant fallback
        env_timeout = os.getenv("OLLAMA_TIMEOUT")
        self.timeout = timeout or (int(env_timeout) if env_timeout else 20)

    def _build_prompt(self, query: str, articles: List[ArticleOut]) -> str:
        bullets = []
        for idx, art in enumerate(articles[:5], 1):
            bullets.append(
                f"[{idx}] Titre: {art.title}\nSource: {art.link or art.source_id or 'n/a'}\nTexte: {art.content}\n"
            )
        sources_text = "\n".join(bullets)
        prompt = (
            "Tu es un assistant qui synthétise des articles de presse en français.\n"
            "Consigne: réponds de façon structurée (Contexte, Points clés, Sources).\n"
            f"Question: {query}\n"
            "Articles fournis:\n"
            f"{sources_text}\n"
            "Rédige une synthèse concise (5-8 phrases) et liste les sources référencées sous forme d'URL ou d'identifiants."
        )
        return prompt

    def summarize(self, query: str, articles: List[ArticleOut]) -> str:
        if not articles:
            return "Aucun article fourni."

        prompt = self._build_prompt(query, articles)
        url = f"{self.host}/api/generate"
        try:
            logger.info("Calling LLM model=%s host=%s", self.model, self.host)
            resp = httpx.post(
                url,
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response") or data.get("text") or ""
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM call failed: %s", exc)
            raise

