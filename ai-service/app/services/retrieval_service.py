import logging
from app.schemas.article import ArticleOut
from app.services.vector_store_service import VectorStoreService

logger = logging.getLogger(__name__)


class RetrievalService:
    """Service de recherche vectorielle via ChromaDB"""

    def __init__(self):
        self.vector_store = VectorStoreService()

    def search(self, query_embedding: list, limit: int = 5) -> list[ArticleOut]:
        """
        Rechercher les articles les plus similaires par vecteur dans ChromaDB

        Args:
            query_embedding: Liste de floats (vecteur embeddings)
            limit: Nombre de résultats (défaut: 5)

        Returns:
            Liste d'ArticleOut
        """
        try:
            results = self.vector_store.search(query_embedding, limit)
            logger.debug(f"Retrieval: found {len(results)} similar articles in ChromaDB")
            return results
        except Exception as e:
            logger.error(f"Error in retrieval search: {e}")
            raise
