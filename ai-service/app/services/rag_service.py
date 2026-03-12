import logging
from typing import Optional
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
        # Concaténer les contenus des articles
        combined_text = "\n\n".join([
            f"**{article.title}**\n{article.content[:500]}..."
            for article in articles[:3]  # Top 3 articles
        ])

        # Résumé simple pour commencer
        summary = f"""**Résumé basé sur {len(articles)} articles pertinents:**

En réponse à votre requête "{query}", voici les informations clés trouvées dans notre base de données d'actualités RDC:

{combined_text}

**Points clés:**
- {len(articles)} articles pertinents identifiés
- Sources diverses couvrant le sujet
- Informations extraites de la base de données RDC News Intelligence

**Note:** Ce résumé est généré automatiquement. Consultez les sources ci-dessous pour plus de détails.
"""

        return summary

    def _format_sources(self, articles: list[ArticleOut]) -> list[dict]:
        """
        Formater les articles en sources avec métadonnées
        """
        sources = []
        for idx, article in enumerate(articles, 1):
            sources.append({
                "id": article.id,
                "rank": idx,
                "title": article.title,
                "excerpt": article.content[:200] + "..." if len(article.content) > 200 else article.content,
                "url": f"/articles/{article.id}",  # URL relative
                "relevance_score": f"Top {idx}"
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

