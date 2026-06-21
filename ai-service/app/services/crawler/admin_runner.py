"""Lancement manuel du crawler + re-embedding (admin / cron)."""
from __future__ import annotations

import logging
import sys
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from unittest.mock import patch

from app.services.crawler.scripts.sync import main as crawl_main
from app.services.train_pipeline import run_reembedding

logger = logging.getLogger(__name__)

# Options affichées dans l’admin (Articles max / source)
CRAWL_LIMIT_OPTIONS: tuple[int, ...] = (10, 20, 30, 50, 100, 1000, 2000)
CRAWL_LIMIT_MAX = max(CRAWL_LIMIT_OPTIONS)

_lock = threading.Lock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CrawlerJobState:
    running: bool = False
    status: str = "idle"  # idle | running | success | error
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    source_id: str = "all"
    limit: int = 30
    page_range: Optional[str] = None
    run_reembedding: bool = True
    crawl_exit_code: Optional[int] = None
    reembed_result: Optional[Any] = None
    message: str = ""
    error: Optional[str] = None


_state = CrawlerJobState()


def get_crawler_job_state() -> dict:
    with _lock:
        return asdict(_state)


def is_crawler_running() -> bool:
    with _lock:
        return _state.running


def run_crawler_sync(
    *,
    source_id: str = "all",
    limit: int = 30,
    page_range: Optional[str] = None,
) -> int:
    """Exécute le script sync (comme la CLI). Retourne le code de sortie (0 = OK)."""
    logger.info(
        "=== [Crawler] Début (source=%s, limit=%s, page_range=%s) ===",
        source_id,
        limit,
        page_range,
    )
    args = ["sync.py", "--source-id", source_id, "--limit", str(limit)]
    if page_range:
        args.extend(["--page-range", page_range])
    try:
        with patch.object(sys, "argv", args):
            try:
                crawl_main()
            except SystemExit as exc:
                code = exc.code if exc.code is not None else 0
                if code != 0:
                    logger.error("Crawler code de sortie: %s", code)
                return int(code)
        return 0
    except Exception as exc:
        logger.exception("Erreur crawler: %s", exc)
        raise


def run_reembedding_sync(*, force_all: bool = False) -> Any:
    logger.info("=== [Crawler] Re-embedding (force_all=%s) ===", force_all)
    return run_reembedding(batch_size=50, force_all=force_all)


def execute_crawler_job(
    *,
    source_id: str = "all",
    limit: int = 30,
    page_range: Optional[str] = None,
    run_reembedding_after: bool = True,
    trigger: str = "admin",
) -> None:
    """Tâche longue (thread ou BackgroundTasks FastAPI)."""
    from app.services.admin_maintenance_runner import is_maintenance_running

    global _state
    if is_maintenance_running():
        logger.warning("[%s] Crawl ignoré : maintenance en cours", trigger)
        return
    with _lock:
        if _state.running:
            logger.warning("[%s] Crawl ignoré : job déjà en cours", trigger)
            return
        _state = CrawlerJobState(
            running=True,
            status="running",
            started_at=_utc_now(),
            source_id=source_id,
            limit=limit,
            page_range=page_range,
            run_reembedding=run_reembedding_after,
            message="Collecte en cours…",
        )

    exit_code = 1
    reembed_result: Any = None
    error: Optional[str] = None
    try:
        exit_code = run_crawler_sync(
            source_id=source_id,
            limit=limit,
            page_range=page_range,
        )
        if run_reembedding_after and exit_code == 0:
            reembed_result = run_reembedding_sync(force_all=False)
        message = (
            "Crawl terminé."
            if exit_code == 0
            else f"Crawl terminé avec code {exit_code}."
        )
        if run_reembedding_after and exit_code == 0:
            message += " Re-embedding lancé."
        status = "success" if exit_code == 0 else "error"
    except Exception as exc:
        status = "error"
        error = str(exc)
        message = f"Échec : {exc}"
        logger.exception("[%s] Job crawler en erreur", trigger)

    with _lock:
        _state.running = False
        _state.status = status
        _state.finished_at = _utc_now()
        _state.crawl_exit_code = exit_code
        _state.reembed_result = reembed_result
        _state.message = message
        _state.error = error
    logger.info("[%s] Job crawler terminé (%s)", trigger, status)


def schedule_crawler_job(
    *,
    source_id: str = "all",
    limit: int = 30,
    page_range: Optional[str] = None,
    run_reembedding_after: bool = True,
    trigger: str = "admin",
) -> bool:
    """Démarre le job en arrière-plan. Retourne False si un job tourne déjà."""
    from app.services.admin_maintenance_runner import is_maintenance_running

    if is_maintenance_running():
        return False
    with _lock:
        if _state.running:
            return False

    def _run() -> None:
        execute_crawler_job(
            source_id=source_id,
            limit=limit,
            page_range=page_range,
            run_reembedding_after=run_reembedding_after,
            trigger=trigger,
        )

    threading.Thread(target=_run, daemon=True).start()
    return True
