# FastAPI entrypoint
# Charge l'environnement avant tout import lourd (sentence_transformers, routes, etc.).
import logging
import os
import time

import app.core.config  # noqa: F401 — charge `.env_file` / `.env`

import asyncio
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.requests import Request

_LOG_FMT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"


def _default_log_file_path() -> str:
    """`<repo>/.logs/fastapi.log` — même emplacement que scripts/dev-all.sh."""
    ai_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    repo_root = os.path.dirname(ai_root)
    return os.path.join(repo_root, ".logs", "fastapi.log")


def _attach_project_file_handler(level: int) -> None:
    """Écrit aussi dans un fichier : avec `uvicorn --reload`, la redirection shell `> log` est souvent vide."""
    if os.getenv("RDC_SKIP_FILE_LOG", "").strip().lower() in {"1", "true", "yes", "on"}:
        return
    path = (os.getenv("RDC_LOG_FILE") or "").strip() or _default_log_file_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    except OSError:
        return
    root = logging.getLogger()
    abs_path = os.path.abspath(path)
    for h in root.handlers:
        if isinstance(h, logging.FileHandler):
            bf = getattr(h, "baseFilename", "")
            if bf and os.path.abspath(bf) == abs_path:
                return
    try:
        fh = logging.FileHandler(path, encoding="utf-8")
    except OSError:
        return
    fh.setLevel(level)
    fh.setFormatter(logging.Formatter(_LOG_FMT, datefmt=_LOG_DATEFMT))
    root.addHandler(fh)


def _configure_logging() -> None:
    """Sans ça, les `logger.info` des routes / services ne sortent souvent pas (niveau WARNING par défaut)."""
    if os.getenv("RDC_SKIP_LOGGING_CONFIG", "").lower() in {"1", "true", "yes"}:
        return
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format=_LOG_FMT,
        datefmt=_LOG_DATEFMT,
        force=True,
    )
    _attach_project_file_handler(level)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    # Uvicorn garde souvent ses logs sur stderr ; laisse tout remonter au root + fichier.
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        lg = logging.getLogger(name)
        lg.propagate = True


_configure_logging()

logger = logging.getLogger(__name__)
_log_target = (os.getenv("RDC_LOG_FILE") or "").strip() or _default_log_file_path()
logger.info("Logging initialisé (console + fichier %s)", _log_target)

app = FastAPI(
    title="RDC News Intelligence AI Service",
    description="Service d'intelligence artificielle pour la détection de désinformation — RDC News",
    version="1.0.0",
)

_skip_health = os.getenv("RDC_HTTP_LOG_SKIP_HEALTH", "").strip().lower() in {"1", "true", "yes", "on"}


@app.middleware("http")
async def http_request_response_logging(request: Request, call_next):
    """Journalise chaque requête entrante et la réponse (statut + durée).

    Pour les réponses en streaming (ex. NDJSON), la durée mesure le temps jusqu'à ce que
    la réponse soit « prête » (en-têtes) ; la fin réelle du flux est loguée dans la route."""
    path = request.url.path
    if _skip_health and path == "/health":
        return await call_next(request)

    started = time.perf_counter()
    client = request.client.host if request.client else "-"
    path_q = path
    if request.url.query:
        path_q = f"{path}?{request.url.query}"

    logger.info("[HTTP] ← %s %s client=%s", request.method, path_q, client)

    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    logger.info(
        "[HTTP] → %s %s status=%s %.1fms",
        request.method,
        path,
        response.status_code,
        elapsed_ms,
    )
    return response


app.state.bootstrap_ok = False
app.state.bootstrap_error = None


def _log_whatsapp_delivery_hints() -> None:
    """Meta n’atteint pas localhost ; mode proxy + file exige un worker de polling."""
    proxy_only = os.getenv("WHATSAPP_WEBHOOK_PROXY_ONLY", "").strip().lower() in {"1", "true", "yes"}
    queue_poll = os.getenv("ENABLE_WHATSAPP_QUEUE_POLLING", "").strip().lower() in {"1", "true", "yes"}
    pop_url = os.getenv("WHATSAPP_QUEUE_POP_URL", "").strip()
    forward_url = os.getenv("WHATSAPP_FORWARD_URL", "").strip()

    logger.info(
        "[Startup][WhatsApp] WEBHOOK_PROXY_ONLY=%s ENABLE_WHATSAPP_QUEUE_POLLING=%s "
        "FORWARD_URL défini=%s POP_URL défini=%s",
        proxy_only,
        queue_poll,
        bool(forward_url),
        bool(pop_url),
    )
    if pop_url:
        logger.info("[Startup][WhatsApp] WHATSAPP_QUEUE_POP_URL=%s", pop_url[:180])

    logger.info(
        "[Startup][WhatsApp] Rappel : l’URL webhook configurée chez Meta doit joindre ce service "
        "(HTTPS public, VPS ou tunnel ngrok/cloudflared). Un FastAPI seul sur 127.0.0.1 ne reçoit pas Meta."
    )

    if proxy_only and not queue_poll:
        logger.warning(
            "[Startup][WhatsApp] Mode proxy+file actif sur cette instance sans polling : une autre machine doit "
            "exécuter ENABLE_WHATSAPP_QUEUE_POLLING=1 et WHATSAPP_QUEUE_POP_URL vers …/webhooks/whatsapp/queue/pop "
            "pour consommer la file."
        )
    if queue_poll and not pop_url:
        logger.warning(
            "[Startup][WhatsApp] Polling activé mais WHATSAPP_QUEUE_POP_URL vide — aucune file distante à lire."
        )


@app.get("/health", tags=["Health"], summary="Service health check")
async def health_check():
    """
    Toujours disponible si ce module se charge.
    `ready: false` indique que le bootstrap complet (RAG, webhooks) a échoué — voir `error`.
    """
    body: dict = {
        "status": "ok",
        "service": "rdc-ai-service",
        "ready": app.state.bootstrap_ok,
    }
    if app.state.bootstrap_error:
        body["error"] = app.state.bootstrap_error
    return JSONResponse(content=body)


def _bootstrap() -> None:
    from app.services.load_dataset import attach_to_app
    from app.api.routes.articles import router as articles_router
    from app.api.routes.webhooks import router as webhooks_router
    from app.services.telegram_polling import run_telegram_polling
    from app.api.routes.webhooks import run_whatsapp_queue_polling

    from app.scheduler import start_cron_jobs, stop_cron_jobs

    attach_to_app(app, background=True, limit=None)

    app.include_router(articles_router)
    app.include_router(webhooks_router, prefix="/webhooks", tags=["Webhooks"])

    @app.on_event("startup")
    async def startup_event():
        # Uvicorn peut reconfigurer le logging après l’import — réattache le fichier une fois l’app démarrée.
        _attach_project_file_handler(logging.getLogger().getEffectiveLevel())
        logger.info("[Startup] Service prêt — traces HTTP dans ce fichier et la console.")
        _log_whatsapp_delivery_hints()

        if os.getenv("ENABLE_CRON_JOBS", "").lower() in {"1", "true", "yes"}:
            asyncio.create_task(start_cron_jobs())

        if os.getenv("ENABLE_TELEGRAM_POLLING", "").lower() in {"1", "true", "yes"}:
            asyncio.create_task(run_telegram_polling())

        if os.getenv("ENABLE_WHATSAPP_QUEUE_POLLING", "").lower() in {"1", "true", "yes"}:
            asyncio.create_task(run_whatsapp_queue_polling())
            logger.info(
                "[Startup] Polling file WhatsApp actif → %s",
                os.getenv("WHATSAPP_QUEUE_POP_URL", "(WHATSAPP_QUEUE_POP_URL non défini)"),
            )

    @app.on_event("shutdown")
    def shutdown_event():
        stop_cron_jobs()


try:
    _bootstrap()
    app.state.bootstrap_ok = True
except Exception as e:
    app.state.bootstrap_error = f"{type(e).__name__}: {e}"
    logger.exception(
        "Bootstrap FastAPI incomplet — /rag et /webhooks indisponibles tant que la cause n'est pas corrigée."
    )
