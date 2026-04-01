import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import sys
from unittest.mock import patch

from app.services.crawler.scripts.sync import main as crawl_main
from app.services.train_pipeline import run_reembedding

logger = logging.getLogger(__name__)

# Executor pour les tâches bloquantes (évite de figer FastAPI)
executor = ThreadPoolExecutor(max_workers=2)
stop_event = Event()

def _run_crawler_sync():
    """Wrapper pour lancer le script CLI existant de façon programmatique."""
    logger.info("=== [CRON] Début du Crawl Automatique ===")
    try:
        # Paramètres passés au script sync.py (par défaut toutes les sources, max 20 articles à chaque cycle)
        # On limite le 'limit' pour ne pas surcharger à chaque cycle de 2h
        args = ["sync.py", "--source-id", "all", "--limit", "30"]
        with patch.object(sys, 'argv', args):
            try:
                crawl_main()
            except SystemExit as e:
                # argparse termine par sys.exit(0) ce qui est normal
                if e.code != 0:
                    logger.error(f"Le crawler a retourné un code d'erreur: {e.code}")
    except Exception as e:
         logger.error(f"Erreur durant l'exécution du Crawler: {e}")

def _run_reembedding_sync():
    """Lance le rafraîchissement RAG (Transfer Learning RAG)."""
    try:
        logger.info("=== [CRON] Finetuning / Re-Embedding de l'IA ===")
        # Rafraîchir les index vectoriels pour les NOUVEAUX articles en BDD seulement
        res = run_reembedding(batch_size=50, force_all=False)
        logger.info(f"=== [CRON] Re-Embedding terminé ! Résultat: {res} ===")
    except Exception as e:
         logger.error(f"Erreur durant le Re-Embedding: {e}")

async def start_cron_jobs():
    """Boucle infinie qui s'exécute en arrière-plan toutes les 2h."""
    logger.info("🚀 Tâche planifiée démarrée (Crawler + Finetunig vectoriel toutes les 2h)")
    
    # Pause initiale pour laisser l'application s'allumer complètement
    await asyncio.sleep(10)
    
    while not stop_event.is_set():
        logger.info(">>> Début du Cycle Automatisé des 2H <<<")
        
        loop = asyncio.get_running_loop()
        
        # 1. On lance le crawler
        await loop.run_in_executor(executor, _run_crawler_sync)
        
        # 2. On lance l'apprentissage vectoriel (Finetuning/Embedding) RAG
        await loop.run_in_executor(executor, _run_reembedding_sync)
        
        logger.info(">>> Cycle Automatisé terminé. En attente de 2 heures... <<<")
        
        # Attendre 2 heures (2 * 60 * 60 = 7200 secondes)
        total_sleep_time = 7200
        slept = 0
        # Sommeil par petites tranches pour permettre l'arrêt propre (shutdown event)
        while slept < total_sleep_time and not stop_event.is_set():
            await asyncio.sleep(5)
            slept += 5

def stop_cron_jobs():
    """Gère l'arrêt propre du scheduler."""
    logger.info("Arrêt du Cron...")
    stop_event.set()
    executor.shutdown(wait=False)
