import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

# — `.env_file` = config locale / dépôt (souvent complet).
# — `.env` = surcharge (ex. VPS, secrets) ; les clés présentes remplacent celles de `.env_file`.
#
# En local, si un `.env` traîne (copie VPS, valeurs fausses) et casse la DB : exporte avant le lancement
#   RDC_ENV_FILE_ONLY=1
# pour ne charger **que** `.env_file` (variable d’environnement système, pas dans les fichiers dotenv).
_ai_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_env_file = os.path.join(_ai_root, ".env_file")
_env = os.path.join(_ai_root, ".env")
_env_file_only = os.getenv("RDC_ENV_FILE_ONLY", "").strip().lower() in {"1", "true", "yes", "on"}

# override=True : les fichiers du projet priment sur des exports shell périmés (ex. DB_PASSWORD faux).
if _env_file_only:
    if os.path.exists(_env_file):
        load_dotenv(dotenv_path=_env_file, override=True)
elif os.path.exists(_env_file):
    load_dotenv(dotenv_path=_env_file, override=True)
    if os.path.exists(_env):
        load_dotenv(dotenv_path=_env, override=True)
elif os.path.exists(_env):
    load_dotenv(dotenv_path=_env, override=True)

def _strip_env(key: str, default: str = "") -> str:
    v = os.getenv(key)
    if v is None:
        return default
    return v.strip()


DB_HOST = _strip_env("DB_HOST", "localhost") or "localhost"
DB_PORT = _strip_env("DB_PORT", "5432") or "5432"
DB_NAME = _strip_env("DB_NAME", "rdc_news") or "rdc_news"
DB_USER = _strip_env("DB_USER", "postgres") or "postgres"
DB_PASSWORD = _strip_env("DB_PASSWORD", "postgres") or "postgres"


def _database_url_from_parts() -> str:
    """Mot de passe échappé pour les caractères spéciaux dans l’URL."""
    return (
        f"postgresql://{quote_plus(DB_USER)}:{quote_plus(DB_PASSWORD)}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )


# Par défaut l’URL est **toujours** reconstruite depuis DB_*.
# Sinon une ligne DATABASE_URL obsolète dans .env (mot de passe ancien) prime encore et provoque
# « authentification échouée » alors que DB_PASSWORD est correct.
# Pour forcer une URL brute (SSL, etc.) : DATABASE_FROM_URL_ONLY=1 + DATABASE_URL=...
if os.getenv("DATABASE_FROM_URL_ONLY", "").strip().lower() in {"1", "true", "yes", "on"}:
    DATABASE_URL = (
        os.getenv("DATABASE_URL")
        or os.getenv("DB_URL")
        or _database_url_from_parts()
    )
else:
    DATABASE_URL = _database_url_from_parts()
