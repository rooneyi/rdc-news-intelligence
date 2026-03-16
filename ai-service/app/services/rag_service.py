import logging
import re
from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import RetrievalService
from app.schemas.article import ArticleOut

logger = logging.getLogger(__name__)


class RAGService:
    """Service RAG (Retrieval-Augmented Generation)

    Récupère les articles pertinents et génère un résumé avec sources
    """

    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.retrieval_service = RetrievalService()

    def generate_answer(self, query: str, top_k: int = 5) -> dict:
        """
        Générer une réponse RAG basée sur la requête

        Args:
            query: Question/requête de l'utilisateur
            top_k: Nombre d'articles à récupérer

        Returns:
            Dict avec 'summary', 'sources', 'query'
        """
        try:
            logger.info(f"RAG query: {query[:100]}")

            # 1. Générer l'embedding de la requête
            query_embedding = self.embedding_service.generate(query)

            # 2. Récupérer les articles les plus pertinents
            articles = self.retrieval_service.search(query_embedding, limit=top_k)

            if not articles:
                return {
                    "summary": "Aucun article pertinent trouvé pour cette requête.",
                    "sources": [],
                    "query": query
                }

            # 3. Générer le résumé basé sur les articles
            summary = self._generate_summary(query, articles)

            # 4. Formater les sources
            sources = self._format_sources(articles)

            logger.info(f"RAG completed: {len(articles)} articles, summary length: {len(summary)}")

            return {
                "summary": summary,
                "sources": sources,
                "query": query,
                "num_sources": len(sources)
            }

        except Exception as e:
            logger.error(f"Error in RAG generation: {e}")
            raise

    def _generate_summary(self, query: str, articles: list[ArticleOut]) -> str:
        """
        Générer un résumé basé sur les articles récupérés

        Pour l'instant: résumé extractif simple
        TODO: Intégrer un LLM (OpenAI, HuggingFace, etc.)
        """
        bullets = []
        for article in articles[:5]:
            snippet = self._extract_snippet(article.content)
            bullets.append(f"- **{article.title}**: {snippet}")

        summary = (
            f"Synthèse pour la requête \"{query}\" basée sur {len(articles)} articles pertinents:\n"
            + "\n".join(bullets)
        )

        return summary

    def _extract_snippet(self, content: str, max_sentences: int = 2) -> str:
        sentences = re.split(r"(?<=[.!?])\s+", content)
        snippet = " ".join(sentences[:max_sentences]).strip()
        if len(snippet) > 300:
            snippet = snippet[:300].rstrip() + "..."
        return snippet or content[:200]

    def _format_sources(self, articles: list[ArticleOut]) -> list[dict]:
        """
        Formater les articles en sources avec métadonnées
        """
        sources = []
        for idx, article in enumerate(articles, 1):
            url = article.link or f"/articles/{article.id}"
            sources.append({
                "id": article.id,
                "rank": idx,
                "title": article.title,
                "excerpt": article.content[:200] + "..." if len(article.content) > 200 else article.content,
                "url": url,
                "relevance_score": f"Top {idx}",
                "source_id": article.source_id,
                "hash": article.hash,
            })

        return sources


class RAGServiceWithLLM(RAGService):
    """
    Version avancée du RAG avec un vrai LLM

    TODO: Implémenter avec OpenAI, Anthropic, ou un modèle local
    """

    def __init__(self, llm_model: str = "gpt-3.5-turbo"):
        super().__init__()
        self.llm_model = llm_model
        # TODO: Initialiser le client LLM

    def _generate_summary(self, query: str, articles: list[ArticleOut]) -> str:
        """
        Générer un résumé avec un LLM
        """
        # TODO: Appeler le LLM avec un prompt approprié
        # Pour l'instant, utilise la version de base
        return super()._generate_summary(query, articles)
