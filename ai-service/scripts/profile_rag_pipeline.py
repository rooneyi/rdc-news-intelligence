import time
import asyncio
import logging
import os
import sys
from pathlib import Path

# Setup path to include app
_AI_SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_AI_SERVICE_ROOT))
os.chdir(_AI_SERVICE_ROOT)

from app.services.rag_service import RAGService
from app.services.embedding_service import EmbeddingService
from app.services.vector_store_service import VectorStoreService
from app.services.llm_service import LLMService

# Import config to load .env_file
import app.core.config

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Profiler")

async def profile_pipeline(query: str):
    logger.info(f"=== PROFILING RAG PIPELINE ===")
    logger.info(f"Query: {query}\n")
    
    rag_service = RAGService()
    embedding_service = EmbeddingService()
    vector_store = VectorStoreService()
    llm_service = LLMService()
    
    results = {}
    
    # 1. Embedding generation
    start = time.perf_counter()
    query_embedding = embedding_service.generate(query)
    results['1_embedding'] = time.perf_counter() - start
    logger.info(f"1. Embedding: {results['1_embedding']:.2f}s")
    
    # 2. Vector Search (ChromaDB)
    start = time.perf_counter()
    articles = vector_store.search(query_embedding, limit=9)
    results['2_vector_search'] = time.perf_counter() - start
    logger.info(f"2. Vector Search (ChromaDB): {results['2_vector_search']:.2f}s (Found {len(articles)} articles)")
    
    if not articles:
        logger.warning("No articles found to proceed with re-ranking or generation.")
        return

    # 3. Re-ranking (LLM)
    if rag_service.enable_rerank:
        start = time.perf_counter()
        # On simule l'appel de re-ranking
        ranked_articles = await llm_service.rerank(query, articles)
        results['3_reranking'] = time.perf_counter() - start
        logger.info(f"3. Re-ranking (LLM): {results['3_reranking']:.2f}s")
    else:
        results['3_reranking'] = 0
        logger.info("3. Re-ranking: DISABLED")

    # 4. LLM Generation
    start = time.perf_counter()
    # On prend le top 3 pour la génération comme en prod
    top_articles = articles[:3]
    response = await llm_service.summarize_full(query, top_articles)
    results['4_generation'] = time.perf_counter() - start
    logger.info(f"4. LLM Generation: {results['4_generation']:.2f}s")
    
    total = sum(results.values())
    logger.info(f"\nTOTAL TIME: {total:.2f}s ({(total/60):.2f} min)")
    logger.info(f"==============================")
    
    return results

if __name__ == "__main__":
    query = "Quelles sont les dernières nouvelles sur les élections en RDC ?"
    asyncio.run(profile_pipeline(query))
