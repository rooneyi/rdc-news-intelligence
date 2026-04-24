"""
Script d'initialisation de la base de données
Crée la table articles si elle n'existe pas
"""
import logging
from app.db.session import get_db_connection
from app.db.models import CREATE_TABLE_SQL, MIGRATE_TABLE_SQL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_database():
    """Initialiser la base de données avec les tables nécessaires"""
    try:
        logger.info("Initializing database...")
        conn = get_db_connection()
        cur = conn.cursor()

        # Créer l'extension pgvector si elle n'existe pas
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        logger.info("✓ Extension pgvector activée")

        # Créer la table articles
        cur.execute(CREATE_TABLE_SQL)
        logger.info("✓ Table articles créée (ou déjà existante)")

        # Migrer les colonnes source_id/link/hash si absentes
        cur.execute(MIGRATE_TABLE_SQL)
        logger.info("✓ Colonnes source_id/link/hash présentes")

        conn.commit()
        cur.close()
        conn.close()

        logger.info("✅ Database initialized successfully!")
        return True
    except Exception as e:
        logger.error(f"❌ Error initializing database: {e}")
        raise


if __name__ == "__main__":
    init_database()

