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

try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator(
        excluded_handlers=["/metrics", "/health"],
        should_respect_env_var=False,
    ).instrument(app).expose(app)
    logger.info("[Metrics] Endpoint /metrics Prometheus actif")
except ImportError:
    logger.warning(
        "[Metrics] prometheus-fastapi-instrumentator absent — /metrics désactivé. "
        "Installe avec : pip install prometheus-fastapi-instrumentator"
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


def _log_whapi_delivery_hints() -> None:
    """Whapi n’atteint pas localhost ; proxy + file exige un worker de polling (comme Meta)."""
    proxy_only = os.getenv("WHAPI_WEBHOOK_PROXY_ONLY", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    queue_poll = os.getenv("ENABLE_WHAPI_QUEUE_POLLING", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    pop_url = os.getenv("WHAPI_QUEUE_POP_URL", "").strip()
    relay = os.getenv("WHAPI_REPLY_RELAY_URL", "").strip()

    logger.info(
        "[Startup][Whapi] WEBHOOK_PROXY_ONLY=%s ENABLE_WHAPI_QUEUE_POLLING=%s "
        "POP_URL défini=%s REPLY_RELAY défini=%s",
        proxy_only,
        queue_poll,
        bool(pop_url),
        bool(relay),
    )
    if pop_url:
        logger.info("[Startup][Whapi] WHAPI_QUEUE_POP_URL=%s", pop_url[:180])
    if relay:
        logger.info("[Startup][Whapi] WHAPI_REPLY_RELAY_URL=%s", relay[:180])

    if proxy_only and not queue_poll:
        logger.warning(
            "[Startup][Whapi] Mode proxy+file sur cette instance sans polling : une autre machine doit "
            "activer ENABLE_WHAPI_QUEUE_POLLING et WHAPI_QUEUE_POP_URL vers …/webhooks/whapi/queue/pop."
        )
    if queue_poll and not pop_url:
        logger.warning(
            "[Startup][Whapi] Polling activé mais WHAPI_QUEUE_POP_URL vide — aucune file Whapi distante."
        )


async def _check_redis() -> dict:
    import redis.asyncio as aioredis
    from app.core.config import REDIS_URL
    t0 = time.perf_counter()
    try:
        r = aioredis.from_url(REDIS_URL, decode_responses=True)
        await asyncio.wait_for(r.ping(), timeout=2.0)
        await r.aclose()
        return {"ok": True, "latency_ms": round((time.perf_counter() - t0) * 1000, 1)}
    except Exception as e:
        return {"ok": False, "error": str(e)[:120]}


async def _check_postgres() -> dict:
    import asyncio
    from app.db.session import get_db_connection
    t0 = time.perf_counter()
    try:
        def _ping():
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            conn.close()
        await asyncio.wait_for(asyncio.to_thread(_ping), timeout=3.0)
        return {"ok": True, "latency_ms": round((time.perf_counter() - t0) * 1000, 1)}
    except Exception as e:
        return {"ok": False, "error": str(e)[:120]}


async def _check_ollama() -> dict:
    import httpx
    host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{host}/api/tags")
        ok = resp.status_code == 200
        return {"ok": ok, "latency_ms": round((time.perf_counter() - t0) * 1000, 1)}
    except Exception as e:
        return {"ok": False, "error": str(e)[:120]}


async def _check_chromadb() -> dict:
    t0 = time.perf_counter()
    try:
        from app.services.vector_store_service import VectorStoreService
        count = await asyncio.wait_for(
            asyncio.to_thread(lambda: VectorStoreService().collection.count()),
            timeout=3.0,
        )
        return {"ok": True, "latency_ms": round((time.perf_counter() - t0) * 1000, 1), "doc_count": count}
    except Exception as e:
        return {"ok": False, "error": str(e)[:120]}


@app.get("/health", tags=["Health"], summary="Service health check")
async def health_check():
    """
    Toujours disponible si ce module se charge.
    `ready: false` indique que le bootstrap complet (RAG, webhooks) a échoué — voir `error`.
    Vérifie activement Redis, PostgreSQL, Ollama et ChromaDB avec timeout court.
    """
    from app.services.ocr_service import OCRService

    redis_status, postgres_status, ollama_status, chroma_status = await asyncio.gather(
        _check_redis(),
        _check_postgres(),
        _check_ollama(),
        _check_chromadb(),
        return_exceptions=False,
    )

    all_ok = all(
        s.get("ok") for s in [redis_status, postgres_status, ollama_status, chroma_status]
    )

    body: dict = {
        "status": "ok" if all_ok else "degraded",
        "service": "rdc-ai-service",
        "ready": app.state.bootstrap_ok,
        "ocr_tesseract": OCRService.is_tesseract_available(),
        "dependencies": {
            "redis": redis_status,
            "postgres": postgres_status,
            "ollama": ollama_status,
            "chromadb": chroma_status,
        },
    }
    if app.state.bootstrap_error:
        body["error"] = app.state.bootstrap_error
    status_code = 200 if app.state.bootstrap_ok else 503
    return JSONResponse(content=body, status_code=status_code)


def _validate_startup_config() -> None:
    """Vérifie les variables d'environnement critiques et logue des avertissements clairs."""
    issues: list[str] = []

    # Token de vérification Meta — la valeur par défaut est publique et dangereuse
    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "").strip()
    if not verify_token:
        issues.append(
            "WHATSAPP_VERIFY_TOKEN manquant — n'importe qui peut valider le webhook Meta. "
            "Définis une valeur secrète dans .env_file."
        )
    elif verify_token == "rdc_news_token":
        issues.append(
            "WHATSAPP_VERIFY_TOKEN utilise la valeur par défaut publique 'rdc_news_token'. "
            "Change-la pour une valeur secrète unique dans .env_file."
        )

    # Token Telegram
    if not os.getenv("TELEGRAM_BOT_TOKEN", "").strip():
        logger.warning("[Config] TELEGRAM_BOT_TOKEN absent — webhook/polling Telegram inopérant.")

    # Base de données
    from app.core.config import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD
    if not all([DB_HOST, DB_NAME, DB_USER, DB_PASSWORD]):
        issues.append(
            "Variables DB_* incomplètes (DB_HOST, DB_NAME, DB_USER, DB_PASSWORD). "
            "Vérifie .env_file."
        )

    # Redis
    if not os.getenv("REDIS_URL", "").strip():
        logger.warning("[Config] REDIS_URL absent — cache, dedup et rate limiting désactivés.")

    for issue in issues:
        logger.error("[Config] ⚠️  %s", issue)

    if issues:
        logger.error(
            "[Config] %s problème(s) de configuration détecté(s) — "
            "certaines fonctionnalités peuvent être non sécurisées ou inopérantes.",
            len(issues),
        )


def _bootstrap() -> None:
    from app.services.load_dataset import attach_to_app
    from app.api.routes.articles import router as articles_router
    from app.api.routes.webhooks import router as webhooks_router
    from app.services.telegram_polling import run_telegram_polling
    from app.api.routes.webhooks import run_whatsapp_queue_polling, run_whapi_queue_polling

    from app.scheduler import start_cron_jobs, stop_cron_jobs

    attach_to_app(app, background=True, limit=None)

    app.include_router(articles_router)
    app.include_router(webhooks_router, prefix="/webhooks", tags=["Webhooks"])

    async def _warmup_ollama() -> None:
        """Envoie un prompt minimal à Ollama pour forcer le chargement du modèle en mémoire.
        Évite le cold start de 3-5 min sur la première vraie requête utilisateur."""
        import httpx
        host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        model = os.getenv("OLLAMA_MODEL", "mistral")
        from app.services.llm_service import normalize_ollama_keep_alive

        keep_alive = normalize_ollama_keep_alive(os.getenv("OLLAMA_KEEP_ALIVE", "-1"))
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{host}/api/generate",
                    json={
                        "model": model,
                        "prompt": "Bonjour",
                        "stream": False,
                        "keep_alive": keep_alive,
                        "num_predict": 1,
                        "options": {"num_ctx": 128, "num_thread": int(os.getenv("OLLAMA_NUM_THREAD", "4"))},
                    },
                )
                if resp.status_code == 200:
                    logger.info("[Startup] Warmup Ollama OK — modèle ‘%s’ chargé en mémoire", model)
                else:
                    logger.warning("[Startup] Warmup Ollama statut=%s — modèle peut nécessiter un cold start", resp.status_code)
        except Exception as e:
            logger.warning("[Startup] Warmup Ollama échoué (%s) — service démarré quand même", e)

    @app.on_event("startup")
    async def startup_event():
        _attach_project_file_handler(logging.getLogger().getEffectiveLevel())
        logger.info("[Startup] Service prêt — traces HTTP dans ce fichier et la console.")
        _validate_startup_config()
        _log_whatsapp_delivery_hints()
        _log_whapi_delivery_hints()
        asyncio.create_task(_warmup_ollama())

        if os.getenv("ENABLE_CRON_JOBS", "").lower() in {"1", "true", "yes"}:
            asyncio.create_task(start_cron_jobs())

        if os.getenv("ENABLE_TELEGRAM_POLLING", "").lower() in {"1", "true", "yes"}:
            asyncio.create_task(run_telegram_polling())
            logger.warning(
                "[Startup][Telegram] Polling actif — désactive le webhook Telegram chez BotFather "
                "si tu reçois des doubles réponses (webhook + polling sur le même message)."
            )

        if os.getenv("ENABLE_WHATSAPP_QUEUE_POLLING", "").lower() in {"1", "true", "yes"}:
            asyncio.create_task(run_whatsapp_queue_polling())
            logger.info(
                "[Startup] Polling file WhatsApp actif → %s",
                os.getenv("WHATSAPP_QUEUE_POP_URL", "(WHATSAPP_QUEUE_POP_URL non défini)"),
            )

        if os.getenv("ENABLE_WHAPI_QUEUE_POLLING", "").lower() in {"1", "true", "yes"}:
            asyncio.create_task(run_whapi_queue_polling())
            logger.info(
                "[Startup] Polling file Whapi actif → %s",
                os.getenv("WHAPI_QUEUE_POP_URL", "(WHAPI_QUEUE_POP_URL non défini)"),
            )

    @app.on_event("shutdown")
    def shutdown_event():
        stop_cron_jobs()
        from app.db.session import close_pool
        close_pool()


try:
    _bootstrap()
    app.state.bootstrap_ok = True
except Exception as e:
    app.state.bootstrap_error = f"{type(e).__name__}: {e}"
    logger.exception(
        "Bootstrap FastAPI incomplet — /rag et /webhooks indisponibles tant que la cause n'est pas corrigée."
    )
