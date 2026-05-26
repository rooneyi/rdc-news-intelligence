"""
Synchronise le corpus PostgreSQL vers ChromaDB.

Par défaut : lit les métadonnées + contenu depuis Postgres, recalcule les embeddings
(même modèle que l'API) et upsert dans Chroma — adapté à l'architecture actuelle
(vecteurs uniquement dans Chroma).

Option --from-pgvector : migration one-shot depuis d'anciennes lignes qui ont encore
la colonne `embedding` remplie en base (plus rapide, pas de recalcul).
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

import psycopg2

_AI_SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_AI_SERVICE_ROOT))
os.chdir(_AI_SERVICE_ROOT)

from app.db.session import get_db_connection  # noqa: E402
from app.schemas.article import ArticleOut  # noqa: E402
from app.services.embedding_service import EmbeddingService  # noqa: E402
from app.services.vector_store_service import VectorStoreService  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _parse_pgvector_embedding(raw) -> list[float]:
    if raw is None:
        raise ValueError("embedding NULL")
    if isinstance(raw, (list, tuple)):
        return [float(x) for x in raw]
    if isinstance(raw, str):
        return [float(x) for x in raw.strip("[]").split(",") if x.strip()]
    raise TypeError(f"embedding type inattendu: {type(raw)}")


def sync_from_pgvector_embeddings(batch_size: int, limit: int | None) -> None:
    """Lit les vecteurs déjà stockés dans Postgres (pgvector) et les pousse vers Chroma.
    DEPRECATED: La colonne 'embedding' a été supprimée du schéma standard.
    """
    logger.warning("ATTENTION: Le mode --from-pgvector est obsolète et échouera si la colonne 'embedding' a été supprimée.")
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        sql = """
            SELECT id, title, content, link, source_id, hash, categories, image, embedding
            FROM articles
            WHERE embedding IS NOT NULL
            ORDER BY id
        """
        params: tuple = ()
        if limit is not None:
            sql += " LIMIT %s"
            params = (limit,)
        cur.execute(sql, params)
        rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    logger.info("Mode --from-pgvector : %s lignes avec embedding en base.", len(rows))
    vector_store = VectorStoreService()
    articles: list[ArticleOut] = []
    embeddings: list[list[float]] = []

    for r in rows:
        emb = _parse_pgvector_embedding(r[8])
        articles.append(
            ArticleOut(
                id=r[0],
                title=r[1] or "",
                content=r[2] or "",
                link=r[3],
                source_id=r[4],
                hash=r[5],
                categories=list(r[6] or []),
                image=r[7],
            )
        )
        embeddings.append(emb)
        if len(articles) >= batch_size:
            vector_store.add_articles(articles, embeddings)
            articles = []
            embeddings = []
    if articles:
        vector_store.add_articles(articles, embeddings)
    logger.info("Synchronisation pgvector → Chroma terminée.")


def sync_from_content(
    batch_size: int,
    limit: int | None,
    model_name: str | None,
) -> None:
    """Recalcule les embeddings depuis le texte (aligné sur create_article / train_pipeline)."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        sql = """
            SELECT id, title, content, link, source_id, hash, categories, image
            FROM articles
            ORDER BY id
        """
        params: tuple = ()
        if limit is not None:
            sql += " LIMIT %s"
            params = (limit,)
        cur.execute(sql, params)
        rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    logger.info("Mode contenu : %s articles à vectoriser puis upsert Chroma.", len(rows))
    embedder = EmbeddingService(model_name=model_name)
    vector_store = VectorStoreService()
    articles: list[ArticleOut] = []
    embeddings: list[list[float]] = []

    for r in rows:
        article_id, title, content, link, source_id, hash_val, categories, image = r
        if not (content or "").strip():
            logger.warning("Article id=%s sans contenu, ignoré.", article_id)
            continue
        try:
            emb = embedder.generate(content)
        except Exception as exc:  # noqa: BLE001
            logger.error("Embedding id=%s échoué: %s", article_id, exc)
            continue
        articles.append(
            ArticleOut(
                id=article_id,
                title=title or "",
                content=content or "",
                link=link,
                source_id=source_id,
                hash=hash_val,
                categories=list(categories or []),
                image=image,
            )
        )
        embeddings.append(emb)
        if len(articles) >= batch_size:
            vector_store.add_articles(articles, embeddings)
            articles = []
            embeddings = []
            logger.info("Batch envoyé (progression…)")

    if articles:
        vector_store.add_articles(articles, embeddings)
    logger.info("Synchronisation contenu → Chroma terminée.")


def main() -> None:
    p = argparse.ArgumentParser(description="Postgres → ChromaDB (articles_rdc)")
    p.add_argument(
        "--from-pgvector",
        action="store_true",
        help="Utiliser la colonne embedding en base (migration depuis l'ancien schéma)",
    )
    p.add_argument("--batch-size", type=int, default=50)
    p.add_argument("--limit", type=int, default=None, help="Limiter le nombre de lignes (test)")
    p.add_argument(
        "--model",
        type=str,
        default=None,
        help="Modèle SentenceTransformers (défaut: EmbeddingService.DEFAULT_MODEL)",
    )
    args = p.parse_args()

    if args.from_pgvector:
        try:
            sync_from_pgvector_embeddings(args.batch_size, args.limit)
        except psycopg2.Error as e:
            logger.error(
                "Échec mode --from-pgvector (colonne embedding absente ou vide ?). "
                "Relancez sans ce flag pour recalcul depuis le contenu. Détail: %s",
                e,
            )
            raise
    else:
        sync_from_content(args.batch_size, args.limit, args.model)


if __name__ == "__main__":
    main()
