import logging
import os
from typing import AsyncGenerator
from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import RetrievalService
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.retrieval_service = RetrievalService()
        self.llm_service = LLMService()
        self.min_similarity_default = float(os.getenv("RAG_MIN_SIMILARITY", "0.36"))
        self.min_similarity_messaging = float(os.getenv("RAG_MIN_SIMILARITY_MSG", "0.40"))

    def _filter_relevant_articles(self, articles: list, channel: str) -> list:
        min_similarity = (
            self.min_similarity_messaging
            if channel in {"whatsapp", "telegram"}
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

    async def generate_answer_stream(
        self,
        query: str,
        top_k: int = 5,
        channel: str = "web",
    ) -> AsyncGenerator[dict, None]:
        """
        Génère une réponse RAG en streaming réel.
        C'est cette méthode qui permet à Mistral de répondre sans timeout.
        """
        try:
            # 1. Recherche des articles (Très rapide)
            query_embedding = self.embedding_service.generate(query)
            articles = self.retrieval_service.search(query_embedding, limit=top_k)
            articles = self._filter_relevant_articles(articles, channel)

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

            # 2. Envoyer les sources tout de suite pour montrer que le RAG travaille
            sources = [{"id": a.id, "title": a.title, "url": a.link} for a in articles]
            logger.info(f"[RAGService] Envoi des sources: {sources}")
            yield {"type": "sources", "sources": sources}

            # 3. Streamer Mistral mot par mot
            async for chunk in self.llm_service.summarize_stream(query, articles, channel=channel):
                logger.info(f"[RAGService] Chunk généré: {chunk[:60]}...")
                yield {"type": "summary_chunk", "text": chunk}

            logger.info("[RAGService] Fin du flux RAG (done)")
            yield {"type": "done"}

        except Exception as e:
            logger.error(f"Erreur critique dans le flux RAG: {e}")
            yield {"type": "error", "message": f"Désolé, Mistral est trop sollicité : {str(e)}"}

    async def generate_full_answer(self, query: str, top_k: int = 5, channel: str = "web") -> str:
        """Génère une réponse RAG complète en un seul bloc (pour les Webhooks)."""
        try:
            # Pour les canaux messagerie, on réduit légèrement le nombre d'articles
            # pour aller plus vite (contexte plus court pour le LLM).
            if channel in ["telegram", "whatsapp"]:
                top_k = min(top_k, 3)

            query_embedding = self.embedding_service.generate(query)
            articles = self.retrieval_service.search(query_embedding, limit=top_k)
            articles = self._filter_relevant_articles(articles, channel)
            
            if not articles:
                logger.info("[RAGService] Aucun article trouvé. Message générique retourné.")
                return f"❌ VÉRIFICATION : NON VÉRIFIABLE\n📝 EXPLICATION : Je n'ai trouvé aucune source locale (RDC News) concernant '{query}'."

            # Pas de timeout : on attend la réponse complète de Mistral,
            # utile pour les canaux où on préfère la qualité à tout prix.
            return await self.llm_service.summarize_full(query, articles, channel=channel)

        except Exception as e:
            logger.error(f"Erreur critique dans le flux complet RAG: {e}")
            return f"⚠️ Une erreur interne est survenue lors de l'analyse (Mistral indisponible : {str(e)})"
