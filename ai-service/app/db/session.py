import logging
import os
import psycopg2
import psycopg2.pool
from app.core.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DATABASE_URL

logger = logging.getLogger(__name__)

# Pool de connexions partagé. Taille configurable via env.
_MIN_CONN = int(os.getenv("DB_POOL_MIN", "2"))
_MAX_CONN = int(os.getenv("DB_POOL_MAX", "10"))
_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def _build_dsn() -> str:
    return DATABASE_URL or (
        f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} "
        f"user={DB_USER} password={DB_PASSWORD}"
    )


def _get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _pool
    if _pool is None or _pool.closed:
        logger.info(
            "[DB Pool] Création pool psycopg2 (min=%s, max=%s, host=%s, db=%s)",
            _MIN_CONN, _MAX_CONN, DB_HOST, DB_NAME,
        )
        _pool = psycopg2.pool.ThreadedConnectionPool(_MIN_CONN, _MAX_CONN, dsn=_build_dsn())
    return _pool


class _PooledConnection:
    """
    Wrapper transparent autour d'une connexion psycopg2.
    Intercèpte close() pour retourner la connexion au pool
    au lieu de la détruire — tous les call sites existants
    (conn.close() dans un finally) fonctionnent sans modification.
    """

    def __init__(self, conn, pool: psycopg2.pool.ThreadedConnectionPool):
        self._conn = conn
        self._pool = pool
        self._returned = False

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def close(self):
        if not self._returned:
            self._returned = True
            try:
                self._pool.putconn(self._conn)
            except Exception as e:
                logger.warning("[DB Pool] putconn échoué: %s", e)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, *_):
        if exc_type:
            try:
                self._conn.rollback()
            except Exception:
                pass
        self.close()


def get_db_connection() -> _PooledConnection:
    """Obtient une connexion depuis le pool. Appeler conn.close() la restitue au pool."""
    pool = _get_pool()
    try:
        conn = pool.getconn()
        if conn.closed:
            pool.putconn(conn)
            conn = pool.getconn()
        return _PooledConnection(conn, pool)
    except psycopg2.pool.PoolError as e:
        raise RuntimeError(f"Database connection pool exhausted: {e}") from e
    except Exception as e:
        logger.error("[DB Pool] Erreur getconn: %s", e)
        raise RuntimeError(f"Database connection failed: {e}") from e


def get_db() -> _PooledConnection:
    """Alias backward-compatible."""
    return get_db_connection()


def close_pool() -> None:
    """Ferme toutes les connexions du pool — appeler au shutdown."""
    global _pool
    if _pool and not _pool.closed:
        _pool.closeall()
        logger.info("[DB Pool] Pool fermé.")
