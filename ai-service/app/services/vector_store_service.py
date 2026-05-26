import logging
import os
import chromadb
from chromadb.config import Settings
from typing import List, Optional
from app.schemas.article import ArticleOut

# Hack pour utiliser pysqlite3 au lieu de sqlite3 (souvent trop vieux sur Linux)
try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

logger = logging.getLogger(__name__)

class VectorStoreService:
    """Service de gestion de la base de données vectorielle ChromaDB"""

    def __init__(self):
        self.db_path = os.path.join(os.getcwd(), "data", "chroma_db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=self.db_path)
        self.collection_name = "articles_rdc"
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"} # Utilisation de la similarité cosinus
        )
        logger.info(f"[VectorStoreService] Initialisé avec la collection: {self.collection_name}")

    def add_articles(self, articles: List[ArticleOut], embeddings: List[List[float]]):
        """Ajoute des articles à la collection ChromaDB"""
        if not articles:
            return

        ids = [str(a.id) for a in articles]
        metadatas = [
            {
                "title": a.title or "",
                "link": a.link or "",
                "source_id": str(a.source_id) if a.source_id else "",
                "hash": a.hash or "",
                "categories": ",".join(a.categories) if a.categories else "",
                "image": a.image or ""
            }
            for a in articles
        ]
        documents = [a.content for a in articles]

        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents
        )
        logger.info(f"[VectorStoreService] {len(articles)} articles upsertés dans ChromaDB")

    def search(self, query_embedding: List[float], limit: int = 5) -> List[ArticleOut]:
        """Recherche les articles les plus similaires"""
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            include=["documents", "metadatas", "distances"]
        )

        articles = []
        if not results["ids"] or not results["ids"][0]:
            return articles

        for i in range(len(results["ids"][0])):
            # ChromaDB renvoie des distances (plus petit = plus proche). 
            # On convertit en score de similarité (1 - distance) pour rester cohérent avec le reste de l'app.
            distance = results["distances"][0][i]
            similarity = 1.0 - distance
            
            metadata = results["metadatas"][0][i]
            categories = metadata.get("categories", "").split(",") if metadata.get("categories") else []
            
            articles.append(ArticleOut(
                id=int(results["ids"][0][i]) if results["ids"][0][i].isdigit() else 0,
                title=metadata.get("title"),
                content=results["documents"][0][i],
                link=metadata.get("link"),
                source_id=metadata.get("source_id"),
                hash=metadata.get("hash"),
                categories=categories,
                image=metadata.get("image"),
                similarity=similarity
            ))
        
        return articles
