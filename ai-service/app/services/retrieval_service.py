import logging
from app.db.session import get_db
from app.schemas.article import ArticleOut

logger = logging.getLogger(__name__)


class RetrievalService:
    """Service de recherche vectorielle dans la DB"""

    def search(self, query_embedding: list, limit: int = 5) -> list[ArticleOut]:
        """
        Rechercher les articles les plus similaires par vecteur

        Args:
            query_embedding: Liste de floats (vecteur embeddings)
            limit: Nombre de résultats (défaut: 5)

        Returns:
            Liste d'ArticleOut
        """
        try:
            conn = get_db()
            cur = conn.cursor()
            try:
                cur.execute(
                    """
                    SELECT
                        id,
                        title,
                        content,
                        link,
                        source_id,
                        hash,
                        (1 - (embedding <=> %s::vector)) AS similarity
                    FROM articles
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (query_embedding, query_embedding, limit)
                )
                results = cur.fetchall()
                logger.debug(f"Retrieval: found {len(results)} similar articles")
                return [
                    ArticleOut(
                        id=r[0],
                        title=r[1],
                        content=r[2],
                        link=r[3],
                        source_id=r[4],
                        hash=r[5],
                        similarity=float(r[6]) if r[6] is not None else None,
                    )
                    for r in results
                ]
            finally:
                cur.close()
                conn.close()
        except Exception as e:
            logger.error(f"Error in retrieval search: {e}")
            raise
