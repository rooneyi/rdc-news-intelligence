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

    def _get_global_index_key(self) -> str:
        return "global_topics_index"

    async def add_to_memory(
        self, 
        chat_id: str, 
        query: str, 
        embedding: List[float], 
        verdict: str, 
        sources: List[Dict[str, Any]],
        platform_message_id: Optional[str] = None
    ):
        """Ajoute un message à la mémoire locale et à l'index global des bulles."""
        try:
            import hashlib
            msg_hash = hashlib.md5(query.encode('utf-8')).hexdigest()
            
            msg_key = self._get_msg_key(msg_hash)
            chat_key = self._get_chat_key(chat_id)
            global_key = self._get_global_index_key()
            
            # 1. Recherche de similarité (Locale puis Globale)
            local_similar = await self.search_similar(chat_id, embedding)
            global_similar = await self.search_global_similar(embedding)
            
            # Logique de Bulle Globale
            if global_similar:
                global_topic_id = global_similar.get("global_topic_id")
                group_count = global_similar.get("group_count", 1)
                # Si c'est un nouveau groupe pour ce sujet, on incrémente
                chats_seen = global_similar.get("chats_seen", [])
                if chat_id not in chats_seen:
                    chats_seen.append(chat_id)
                    group_count += 1
            else:
                global_topic_id = f"topic:{int(time.time())}"
                group_count = 1
                chats_seen = [chat_id]

            # Logique de Racine (Pivot) locale
            root_message_id = platform_message_id
            occurrence_count = 1
            if local_similar:
                root_message_id = local_similar.get("root_message_id") or local_similar.get("platform_message_id")
                occurrence_count = local_similar.get("occurrence_count", 0) + 1
            
            data = {
                "query": query,
                "embedding": embedding,
                "verdict": verdict,
                "sources": sources,
                "timestamp": time.time(),
                "platform_message_id": platform_message_id,
                "root_message_id": root_message_id,
                "global_topic_id": global_topic_id,
                "group_count": group_count,
                "chats_seen": chats_seen,
                "occurrence_count": occurrence_count
            }
            
            # Stockage Message
            await self.redis_client.setex(msg_key, self.ttl, json.dumps(data))
            
            # Index Local
            await self.redis_client.sadd(chat_key, msg_hash)
            await self.redis_client.expire(chat_key, self.ttl)
            
            # Index Global (pour la détection transverse)
            await self.redis_client.hset(global_key, global_topic_id, json.dumps({
                "embedding": embedding,
                "last_query": query,
                "group_count": group_count,
                "chats_seen": chats_seen,
                "timestamp": time.time()
            }))
            await self.redis_client.expire(global_key, self.ttl)
            
            logger.info(f"[Memory] Global Bubble Updated: {global_topic_id} (Groups: {group_count}, Local Count: {occurrence_count})")
        except Exception as e:
            logger.error(f"[Memory] Erreur add_to_memory: {e}")

    async def search_global_similar(self, query_embedding: List[float]) -> Optional[Dict[str, Any]]:
        """Recherche si un sujet similaire existe n'importe où dans le pays (tous les groupes)."""
        try:
            global_key = self._get_global_index_key()
            all_topics = await self.redis_client.hgetall(global_key)
            
            best_match = None
            max_similarity = 0.0
            
            for topic_id, raw_data in all_topics.items():
                data = json.loads(raw_data)
                stored_emb = data.get("embedding")
                if stored_emb:
                    similarity = self._cosine_similarity(query_embedding, stored_emb)
                    if similarity > max_similarity:
                        max_similarity = similarity
                        best_match = data
                        best_match["global_topic_id"] = topic_id
            
            if best_match and max_similarity >= self.similarity_threshold:
                return best_match
        except Exception as e:
            logger.error(f"[Memory] Erreur search_global_similar: {e}")
        return None

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
