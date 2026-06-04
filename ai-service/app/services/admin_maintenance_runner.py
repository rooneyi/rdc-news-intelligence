"""Jobs admin : re-embedding Chroma, backfill catégories."""
from __future__ import annotations

import logging
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from app.services.category_backfill import backfill_missing_categories
from app.services.crawler.admin_runner import is_crawler_running
from app.services.train_pipeline import run_reembedding

logger = logging.getLogger(__name__)

_lock = threading.Lock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_admin_busy() -> bool:
    return is_crawler_running() or is_maintenance_running()


@dataclass
class MaintenanceJobState:
    running: bool = False
    status: str = "idle"
    job_type: str = "idle"  # reembed | categories | pipeline
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    force_all: bool = False
    only_without_category: bool = False
    backfill_categories_first: bool = False
    category_limit: int = 0
    fetch_html_for_categories: bool = False
    categories_result: Optional[dict[str, Any]] = None
    reembed_result: Optional[dict[str, Any]] = None
    message: str = ""
    error: Optional[str] = None


_state = MaintenanceJobState()


def get_maintenance_job_state() -> dict:
    with _lock:
        return asdict(_state)


def is_maintenance_running() -> bool:
    with _lock:
        return _state.running


def execute_maintenance_job(
    *,
    force_all: bool = False,
    only_without_category: bool = False,
    backfill_categories_first: bool = False,
    category_limit: int = 0,
    fetch_html_for_categories: bool = False,
    batch_size: int = 50,
    trigger: str = "admin",
) -> None:
    global _state
    with _lock:
        if _state.running:
            logger.warning("[%s] Maintenance ignorée : job déjà en cours", trigger)
            return
        _state = MaintenanceJobState(
            running=True,
            status="running",
            job_type="pipeline" if backfill_categories_first else "reembed",
            started_at=_utc_now(),
            force_all=force_all,
            only_without_category=only_without_category,
            backfill_categories_first=backfill_categories_first,
            category_limit=category_limit,
            fetch_html_for_categories=fetch_html_for_categories,
            message="Maintenance en cours…",
        )

    categories_result: Optional[dict[str, Any]] = None
    reembed_result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    status = "success"
    message_parts: list[str] = []

    try:
        if backfill_categories_first:
            with _lock:
                _state.job_type = "categories"
                _state.message = "Backfill des catégories…"
            categories_result = backfill_missing_categories(
                limit=category_limit,
                fetch_html=fetch_html_for_categories,
            )
            message_parts.append(
                f"Catégories : {categories_result.get('updated', 0)} article(s) mis à jour "
                f"({categories_result.get('scanned', 0)} scannés)."
            )

        with _lock:
            _state.job_type = "reembed"
            _state.message = "Re-embedding vers ChromaDB…"
            _state.categories_result = categories_result

        reembed_result = run_reembedding(
            batch_size=batch_size,
            force_all=force_all,
            only_without_category=only_without_category,
        )
        message_parts.append(
            f"Embeddings : {reembed_result.get('reembedded', 0)} / "
            f"{reembed_result.get('processed', 0)} article(s) traités."
        )
        message = " ".join(message_parts) or "Maintenance terminée."
    except Exception as exc:
        status = "error"
        error = str(exc)
        message = f"Échec maintenance : {exc}"
        logger.exception("[%s] Job maintenance en erreur", trigger)

    with _lock:
        _state.running = False
        _state.status = status
        _state.finished_at = _utc_now()
        _state.categories_result = categories_result
        _state.reembed_result = reembed_result
        _state.message = message
        _state.error = error
    logger.info("[%s] Maintenance terminée (%s)", trigger, status)


def schedule_maintenance_job(
    *,
    force_all: bool = False,
    only_without_category: bool = False,
    backfill_categories_first: bool = False,
    category_limit: int = 0,
    fetch_html_for_categories: bool = False,
    batch_size: int = 50,
    trigger: str = "admin",
) -> bool:
    if is_admin_busy():
        return False

    def _run() -> None:
        execute_maintenance_job(
            force_all=force_all,
            only_without_category=only_without_category,
            backfill_categories_first=backfill_categories_first,
            category_limit=category_limit,
            fetch_html_for_categories=fetch_html_for_categories,
            batch_size=batch_size,
            trigger=trigger,
        )

    threading.Thread(target=_run, daemon=True).start()
    return True
