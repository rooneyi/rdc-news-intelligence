import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Event

from app.services.crawler.admin_runner import execute_crawler_job

logger = logging.getLogger(__name__)

# Executor pour les tâches bloquantes (évite de figer FastAPI)
executor = ThreadPoolExecutor(max_workers=2)
stop_event = Event()


def _run_cron_cycle_sync() -> None:
    """Crawl toutes les sources + re-embedding (cycle planifié 2h)."""
    execute_crawler_job(
        source_id="all",
        limit=30,
        run_reembedding_after=True,
        trigger="cron",
    )

async def start_cron_jobs():
    """Boucle infinie qui s'exécute en arrière-plan toutes les 2h."""
    logger.info("🚀 Tâche planifiée démarrée (Crawler + Finetunig vectoriel toutes les 2h)")
    
    # Pause initiale pour laisser l'application s'allumer complètement
    await asyncio.sleep(10)
    
    while not stop_event.is_set():
        logger.info(">>> Début du Cycle Automatisé des 2H <<<")
        
        loop = asyncio.get_running_loop()
        
        await loop.run_in_executor(executor, _run_cron_cycle_sync)
        
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
