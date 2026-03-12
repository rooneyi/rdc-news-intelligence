from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service pour générer les embeddings avec lazy loading du modèle"""

    # Modèle par défaut pour les requêtes
    DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    # Modèle pour le dataset (utilisé dans load_dataset.py)
    DATASET_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

    # Cache des modèles chargés {model_name: model_instance}
    _models_cache = {}

    def __init__(self, model_name: str = None):
        """Initialiser avec lazy loading du modèle"""
        self.model_name = model_name or self.DEFAULT_MODEL
        self._model = None

    def _load_model(self):
        """Charger le modèle une seule fois (cache global)"""
        if self.model_name not in self._models_cache:
            logger.info(f"Loading embedding model: {self.model_name}")
            self._models_cache[self.model_name] = SentenceTransformer(self.model_name)
        return self._models_cache[self.model_name]

    def generate(self, text: str) -> list:
        """Générer un embedding pour le texte"""
        model = self._load_model()
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    @classmethod
    def get_dataset_embedder(cls):
        """Factory pour créer un embedder avec le modèle du dataset"""
        return cls(model_name=cls.DATASET_MODEL)
