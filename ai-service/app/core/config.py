import os
from dotenv import load_dotenv

# Priorité : `.env` (ex. VPS / prod), sinon `.env_file` (habitude locale du dépôt).
_ai_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_dotenv = os.path.join(_ai_root, ".env")
_dotenv_file = os.path.join(_ai_root, ".env_file")
dotenv_path = _dotenv if os.path.exists(_dotenv) else _dotenv_file
load_dotenv(dotenv_path=dotenv_path)

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "rdc_news")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DATABASE_URL = os.getenv("DATABASE_URL") or f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
