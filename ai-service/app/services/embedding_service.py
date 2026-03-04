from sentence_transformers import SentenceTransformer

class EmbeddingService:
    def __init__(self):
        self.model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

    def generate(self, text: str):
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()