from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service pour générer les embeddings avec lazy loading du modèle"""

    # Modèle multilingue recommandé pour le contenu en Français (RDC)
    # Dimension 384, compatible avec ta colonne VECTOR(384)
    DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    DATASET_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    # Cache des modèles chargés {model_name: model_instance}
    _models_cache = {}

    def __init__(self, model_name: str = None):
        """Initialiser avec lazy loading du modèle"""
        self.model_name = model_name or self.DEFAULT_MODEL
        self.cache_folder = "models_cache"

    def _load_model(self):
        """Charger le modèle une seule fois (cache global)"""
        if self.model_name not in self._models_cache:
            logger.info(f"Loading embedding model: {self.model_name}")
            # sentence-transformers 2.7.0 ne supporte pas le paramètre local_files_only
            # Le cache est déjà géré via cache_folder; si le modèle est présent en local,
            # il sera utilisé sans requête réseau.
            model = SentenceTransformer(self.model_name, cache_folder=self.cache_folder)
            self._models_cache[self.model_name] = model
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
