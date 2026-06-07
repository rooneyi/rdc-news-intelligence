from sentence_transformers import SentenceTransformer
import hashlib
import json
import logging
import os

logger = logging.getLogger(__name__)

# TTL du cache embedding Redis : 1 heure par défaut
_EMBEDDING_CACHE_TTL = int(os.getenv("EMBEDDING_CACHE_TTL", "3600"))


def _get_redis():
    """Connexion Redis lazy pour éviter l'import circulaire au module level."""
    import redis as sync_redis
    from app.core.config import REDIS_URL
    return sync_redis.from_url(REDIS_URL, decode_responses=True)


class EmbeddingService:
    """Service pour générer les embeddings avec lazy loading du modèle et cache Redis."""

    DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    DATASET_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    _models_cache: dict = {}
    _redis_client = None

    def __init__(self, model_name: str = None):
        self.model_name = model_name or self.DEFAULT_MODEL
        self.cache_folder = "models_cache"

    def _load_model(self):
        if self.model_name not in self._models_cache:
            logger.info("Loading embedding model: %s", self.model_name)
            model = SentenceTransformer(self.model_name, cache_folder=self.cache_folder)
            self._models_cache[self.model_name] = model
        return self._models_cache[self.model_name]

    def _redis(self):
        if EmbeddingService._redis_client is None:
            try:
                EmbeddingService._redis_client = _get_redis()
            except Exception:
                pass
        return EmbeddingService._redis_client

    def _cache_key(self, text: str) -> str:
        digest = hashlib.sha256(f"{self.model_name}:{text}".encode()).hexdigest()
        return f"emb:{digest}"

    def generate(self, text: str) -> list:
        """Générer un embedding. Vérifie le cache Redis d'abord (TTL=1h)."""
        key = self._cache_key(text)
        r = self._redis()

        # Lecture cache
        if r is not None and _EMBEDDING_CACHE_TTL > 0:
            try:
                cached = r.get(key)
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.debug("[EmbeddingService] Cache Redis lecture échouée: %s", e)

        # Calcul
        model = self._load_model()
        embedding = model.encode(text, normalize_embeddings=True).tolist()

        # Écriture cache
        if r is not None and _EMBEDDING_CACHE_TTL > 0:
            try:
                r.setex(key, _EMBEDDING_CACHE_TTL, json.dumps(embedding))
            except Exception as e:
                logger.debug("[EmbeddingService] Cache Redis écriture échouée: %s", e)

        return embedding

    @classmethod
    def get_dataset_embedder(cls):
        return cls(model_name=cls.DATASET_MODEL)
