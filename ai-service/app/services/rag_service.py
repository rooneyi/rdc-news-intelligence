import logging
import os
from typing import AsyncGenerator
from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import RetrievalService
from app.services.llm_service import LLMService
from app.services.response_cache import get_cached, set_cached

logger = logging.getLogger(__name__)


def _is_postgres_connection_error(text: str) -> bool:
    low = text.lower()
    return (
        "database connection failed" in low
        or "password authentication failed" in low
        or "authentification par mot de passe" in low
        or "authentication failed" in low
        or "could not connect to server" in low
        or ("fatal" in low and "postgres" in low)
        or ("connexion" in low and "postgresql" in low)
    )


def _format_rag_error(exc: BaseException) -> str:
    """Même préfixe utilisateur qu’avant ; précision PostgreSQL si l’exception le permet."""
    raw = str(exc)
    if _is_postgres_connection_error(raw):
        return (
            "Désolé, Mistral est trop sollicité : "
            "[PostgreSQL — connexion / mot de passe / DB_* dans ai-service/.env_file] "
            f"{raw}"
        )
    return f"Désolé, Mistral est trop sollicité : {raw}"


class RAGService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.retrieval_service = RetrievalService()
        self.llm_service = LLMService()
        self.min_similarity_default = float(os.getenv("RAG_MIN_SIMILARITY", "0.36"))
        self.min_similarity_messaging = float(os.getenv("RAG_MIN_SIMILARITY_MSG", "0.40"))
        self.enable_rerank = os.getenv("RAG_ENABLE_RERANK", "true").lower() in (
            "1",
            "true",
            "yes",
        )

    def _filter_relevant_articles(self, articles: list, channel: str) -> list:
        # Web : même seuil que messagerie pour des sources aussi pertinentes que WhatsApp/Telegram.
        min_similarity = (
            self.min_similarity_messaging
            if channel in {"whatsapp", "telegram", "web"}
            else self.min_similarity_default
        )
        filtered = [
            a for a in articles
            if (a.similarity is not None and a.similarity >= min_similarity)
        ]
        logger.info(
            "[RAGService] Filtrage pertinence: %s/%s conservés (seuil=%.2f, canal=%s)",
            len(filtered),
            len(articles),
            min_similarity,
            channel,
        )
        return filtered

    async def generate_viral_answer_stream(
        self,
        query: str,
        old_query: str,
        old_verdict: str,
        group_count: int,
        top_k: int = 5,
        channel: str = "web",
        query_embedding: list | None = None,
    ) -> AsyncGenerator[dict, None]:
        """Génère une synthèse d'intelligence pour un sujet viral transverse."""
        try:
            effective_top_k = min(top_k, 5)
            if query_embedding is None:
                query_embedding = self.embedding_service.generate(query)
            articles = self.retrieval_service.search(query_embedding, limit=effective_top_k * 2)

            if self.enable_rerank and len(articles) > 1:
                articles = await self.llm_service.rerank(query, articles)

            articles = self._filter_relevant_articles(articles, channel)
            articles = articles[:effective_top_k]

            sources = [{"id": a.id, "title": a.title, "url": a.link} for a in articles]
            if sources:
                yield {"type": "sources", "sources": sources}

            full_text_parts: list[str] = []
            async for chunk in self.llm_service.summarize_viral_stream(query, old_query, old_verdict, articles, group_count, channel=channel):
                full_text_parts.append(chunk)
                yield {"type": "summary_chunk", "text": chunk}

            await set_cached(query, channel, "".join(full_text_parts), sources)
            yield {"type": "done"}
        except Exception as e:
            logger.error(f"Erreur generate_viral_answer_stream: {e}")
            yield {"type": "error", "message": _format_rag_error(e)}

    async def generate_refined_answer_stream(
        self,
        query: str,
        old_query: str,
        old_verdict: str,
        top_k: int = 5,
        channel: str = "web",
        query_embedding: list | None = None,
    ) -> AsyncGenerator[dict, None]:
        """Génère une réponse améliorée en streaming quand une question similaire existe."""
        try:
            effective_top_k = min(top_k, 3) if channel in {"telegram", "whatsapp"} else top_k

            if query_embedding is None:
                query_embedding = self.embedding_service.generate(query)
            articles = self.retrieval_service.search(query_embedding, limit=effective_top_k * 2)
            
            if self.enable_rerank and len(articles) > 1:
                articles = await self.llm_service.rerank(query, articles)
            
            articles = self._filter_relevant_articles(articles, channel)
            articles = articles[:effective_top_k]

            sources = [{"id": a.id, "title": a.title, "url": a.link} for a in articles]
            if sources:
                yield {"type": "sources", "sources": sources}

            async for chunk in self.llm_service.summarize_refined_stream(query, old_query, old_verdict, articles, channel=channel):
                yield {"type": "summary_chunk", "text": chunk}

            yield {"type": "done"}
        except Exception as e:
            logger.error(f"Erreur generate_refined_answer_stream: {e}")
            yield {"type": "error", "message": _format_rag_error(e)}

    async def generate_refined_full_answer(
        self,
        query: str,
        old_query: str,
        old_verdict: str,
        top_k: int = 5,
        channel: str = "web",
        query_embedding: list | None = None,
    ) -> dict:
        """Génère une réponse améliorée complète pour une question similaire."""
        try:
            effective_top_k = min(top_k, 3) if channel in {"telegram", "whatsapp"} else top_k

            if query_embedding is None:
                query_embedding = self.embedding_service.generate(query)
            articles = self.retrieval_service.search(query_embedding, limit=effective_top_k * 2)

            if self.enable_rerank and len(articles) > 1:
                articles = await self.llm_service.rerank(query, articles)

            articles = self._filter_relevant_articles(articles, channel)
            articles = articles[:effective_top_k]

            sources = [{"id": a.id, "title": a.title, "url": a.link} for a in articles]

            verdict = await self.llm_service.summarize_refined_full(query, old_query, old_verdict, articles, channel=channel)
            result = {"verdict": verdict, "sources": sources}
            await set_cached(query, channel, verdict, sources)
            return result
        except Exception as e:
            logger.error(f"Erreur generate_refined_full_answer: {e}")
            return {
                "verdict": f"⚠️ Une erreur est survenue lors de l'amélioration de la réponse ({str(e)})",
                "sources": []
            }

    async def generate_viral_full_answer(
        self,
        query: str,
        old_query: str,
        old_verdict: str,
        group_count: int,
        top_k: int = 5,
        channel: str = "web",
        query_embedding: list | None = None,
    ) -> dict:
        """Génère une synthèse d'intelligence complète pour un sujet viral transverse."""
        try:
            effective_top_k = min(top_k, 5)
            if query_embedding is None:
                query_embedding = self.embedding_service.generate(query)
            articles = self.retrieval_service.search(query_embedding, limit=effective_top_k * 2)
            
            if self.enable_rerank and len(articles) > 1:
                articles = await self.llm_service.rerank(query, articles)
            
            articles = self._filter_relevant_articles(articles, channel)
            articles = articles[:effective_top_k]
            
            sources = [{"id": a.id, "title": a.title, "url": a.link} for a in articles]
            
            verdict = ""
            async for chunk in self.llm_service.summarize_viral_stream(query, old_query, old_verdict, articles, group_count, channel=channel):
                verdict += chunk

            result = {"verdict": verdict, "sources": sources}
            await set_cached(query, channel, verdict, sources)
            return result
        except Exception as e:
            logger.error(f"Erreur generate_viral_full_answer: {e}")
            return {
                "verdict": f"⚠️ Erreur lors de la synthèse virale: {str(e)}",
                "sources": []
            }

    async def generate_answer_stream(
        self,
        query: str,
        top_k: int = 5,
        channel: str = "web",
        query_embedding: list | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Génère une réponse RAG en streaming réel.
        `query_embedding` peut être passé pour éviter de le recalculer si déjà disponible.
        """
        try:
            effective_top_k = top_k
            if channel in {"telegram", "whatsapp"}:
                effective_top_k = min(top_k, 3)
            elif channel == "web":
                effective_top_k = min(
                    top_k,
                    int(os.getenv("RAG_WEB_TOP_K", os.getenv("WHATSAPP_TOP_K", "3"))),
                )

            # 1. Vérifier le cache avant tout calcul coûteux
            cached = await get_cached(query, channel)
            if cached:
                if cached.get("sources"):
                    yield {"type": "sources", "sources": cached["sources"]}
                yield {"type": "summary_chunk", "text": cached["verdict"]}
                yield {"type": "done"}
                return

            # 2. Recherche vectorielle (embedding pré-calculé si fourni)
            search_limit = effective_top_k * 2 if not self.enable_rerank else effective_top_k * 3
            if query_embedding is None:
                query_embedding = self.embedding_service.generate(query)
            articles = self.retrieval_service.search(query_embedding, limit=search_limit)
            
            # 2. Re-ranking sémantique via l'LLM (désactivable : RAG_ENABLE_RERANK=false)
            if self.enable_rerank and len(articles) > 1:
                logger.info(
                    "[RAGService] Re-ranking sémantique pour %s candidats",
                    len(articles),
                )
                articles = await self.llm_service.rerank(query, articles)
            
            # 3. Filtrage par pertinence
            articles = self._filter_relevant_articles(articles, channel)
            # On ne garde que les top_k finaux après re-ranking
            articles = articles[:effective_top_k]

            if not articles:
                logger.info("[RAGService] Aucun article suffisamment pertinent pour la requête.")
                yield {
                    "type": "summary_chunk",
                    "text": (
                        "❌ VÉRIFICATION : NON VÉRIFIABLE\n"
                        "📝 EXPLICATION : Je n'ai trouvé aucune source locale suffisamment liée à votre question."
                    ),
                }
                yield {"type": "done"}
                return

            # 4. Envoyer les sources tout de suite pour montrer que le RAG travaille
            sources = [{"id": a.id, "title": a.title, "url": a.link} for a in articles]
            logger.info(f"[RAGService] Envoi des sources ({len(sources)}): {sources}")
            yield {"type": "sources", "sources": sources}

            # 5. Streamer Mistral mot par mot en collectant pour le cache
            full_text_parts: list[str] = []
            async for chunk in self.llm_service.summarize_stream(query, articles, channel=channel):
                full_text_parts.append(chunk)
                yield {"type": "summary_chunk", "text": chunk}

            # 6. Sauvegarder en cache pour les prochaines requêtes identiques
            await set_cached(query, channel, "".join(full_text_parts), sources)

            logger.info("[RAGService] Fin du flux RAG (done)")
            yield {"type": "done"}

        except Exception as e:
            logger.error(f"Erreur critique dans le flux RAG: {e}")
            yield {"type": "error", "message": _format_rag_error(e)}

    async def generate_full_answer(
        self,
        query: str,
        top_k: int = 5,
        channel: str = "web",
        query_embedding: list | None = None,
    ) -> dict:
        """Génère une réponse RAG complète et retourne le texte + les sources.
        `query_embedding` peut être passé pour éviter de le recalculer si déjà disponible."""
        try:
            # Vérifier le cache d’abord
            cached = await get_cached(query, channel)
            if cached:
                return cached

            if channel in ["telegram", "whatsapp"]:
                top_k = min(top_k, 3)
            elif channel == "web":
                top_k = min(
                    top_k,
                    int(os.getenv("RAG_WEB_TOP_K", os.getenv("WHATSAPP_TOP_K", "3"))),
                )

            if query_embedding is None:
                query_embedding = self.embedding_service.generate(query)
            search_limit = top_k * 2 if not self.enable_rerank else top_k * 3
            articles = self.retrieval_service.search(query_embedding, limit=search_limit)
            
            if self.enable_rerank and len(articles) > 1:
                logger.info("[RAGService] Re-ranking avant génération (%s candidats)", len(articles))
                articles = await self.llm_service.rerank(query, articles)

            articles = self._filter_relevant_articles(articles, channel)
            articles = articles[:top_k]
            
            sources = [{"id": a.id, "title": a.title, "url": a.link} for a in articles]

            if not articles:
                logger.info("[RAGService] Aucun article trouvé. Message générique retourné.")
                return {
                    "verdict": f"❌ VÉRIFICATION : NON VÉRIFIABLE\n📝 EXPLICATION : Je n'ai trouvé aucune source locale (RDC News) concernant '{query}'.",
                    "sources": []
                }

            logger.info("[RAGService] Appel Mistral/Ollama (generate_full_answer, %s sources)", len(articles))
            verdict = await self.llm_service.summarize_full(query, articles, channel=channel)
            result = {"verdict": verdict, "sources": sources}
            await set_cached(query, channel, verdict, sources)
            return result

        except Exception as e:
            logger.error(f"Erreur critique dans le flux complet RAG: {e}")
            detail = str(e)
            if _is_postgres_connection_error(detail):
                detail = (
                    "[PostgreSQL — vérifie DB_* / .env_file, "
                    "`python scripts/check_db_connection.py`] "
                    + detail
                )
            return {
                "verdict": f"⚠️ Une erreur interne est survenue lors de l'analyse (Mistral indisponible : {detail})",
                "sources": []
            }
