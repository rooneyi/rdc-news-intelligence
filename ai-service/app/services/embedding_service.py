# services/embedding_service.py

from sentence_transformers import SentenceTransformer
import numpy as np

class EmbeddingService:
    def __init__(self):
        self.model = SentenceTransformer("intfloat/multilingual-e5-large")

    def generate(self, text: str) -> list:
        embedding = self.model.encode(
            f"query: {text}",
            normalize_embeddings=True
        )
        return embedding.tolist()