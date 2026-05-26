import json
import logging
import os
import time
from typing import List, Optional, Dict, Any

import redis.asyncio as redis
from app.core.config import REDIS_URL
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

class ConversationalMemoryService:
    """
    Service de mémoire conversationnelle basé sur Redis (Asynchrone).
    Permet de regrouper les messages similaires (clustering) et de réutiliser les verdicts.
    """

    def __init__(self):
        self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        self.embedding_service = EmbeddingService()
        self.ttl = int(os.getenv("MEMORY_TTL_SECONDS", "3600"))  # 1 heure par défaut
        self.similarity_threshold = float(os.getenv("MEMORY_SIMILARITY_THRESHOLD", "0.85"))

    def _get_chat_key(self, chat_id: str) -> str:
        return f"chat_history:{chat_id}"

    def _get_msg_key(self, msg_hash: str) -> str:
        return f"msg_data:{msg_hash}"

    async def add_to_memory(self, chat_id: str, query: str, embedding: List[float], verdict: str, sources: List[Dict[str, Any]]):
        """Ajoute un message et son verdict à la mémoire Redis."""
        try:
            # On utilise un hash du texte pour identifier le message de façon unique dans Redis
            import hashlib
            msg_hash = hashlib.md5(query.encode('utf-8')).hexdigest()
            
            msg_key = self._get_msg_key(msg_hash)
            chat_key = self._get_chat_key(chat_id)
            
            data = {
                "query": query,
                "embedding": embedding,
                "verdict": verdict,
                "sources": sources,
                "timestamp": time.time()
            }
            
            # Stocker les données du message avec expiration
            await self.redis_client.setex(msg_key, self.ttl, json.dumps(data))
            
            # Ajouter à l'index du chat (SADD)
            await self.redis_client.sadd(chat_key, msg_hash)
            # On ne peut pas mettre d'expiration sur les membres d'un SET, 
            # mais on peut mettre une expiration sur la clé du SET elle-même.
            await self.redis_client.expire(chat_key, self.ttl)
            
            logger.info(f"[Memory] Message ajouté à la mémoire pour le chat {chat_id}")
        except Exception as e:
            logger.error(f"[Memory] Erreur add_to_memory: {e}")

    async def search_similar(self, chat_id: str, query_embedding: List[float]) -> Optional[Dict[str, Any]]:
        """Recherche un message similaire dans l'historique récent du chat."""
        try:
            chat_key = self._get_chat_key(chat_id)
            msg_hashes = await self.redis_client.smembers(chat_key)
            
            if not msg_hashes:
                return None
            
            best_match = None
            max_similarity = 0.0
            
            # On parcourt les messages récents du chat
            for msg_hash in msg_hashes:
                msg_key = self._get_msg_key(msg_hash)
                raw_data = await self.redis_client.get(msg_key)
                
                if not raw_data:
                    # Le message a expiré, on le retire du SET du chat
                    await self.redis_client.srem(chat_key, msg_hash)
                    continue
                
                data = json.loads(raw_data)
                stored_emb = data.get("embedding")
                
                if stored_emb:
                    similarity = self._cosine_similarity(query_embedding, stored_emb)
                    if similarity > max_similarity:
                        max_similarity = similarity
                        best_match = data
            
            if best_match and max_similarity >= self.similarity_threshold:
                logger.info(f"[Memory] Match trouvé (score={max_similarity:.2f}) dans le chat {chat_id}")
                return best_match
                
        except Exception as e:
            logger.error(f"[Memory] Erreur search_similar: {e}")
            
        return None

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        if len(vec1) != len(vec2):
            return 0.0
        return sum(a * b for a, b in zip(vec1, vec2))
