#!/usr/bin/env python3
"""
Teste la connexion Postgres avec la même config que l’app (app.core.config).
Usage depuis ai-service/ : python scripts/check_db_connection.py
"""
from __future__ import annotations

import os
import sys

# Import après avoir forcé le cwd si besoin
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.core.config as cfg


def main() -> None:
    pw = cfg.DB_PASSWORD or ""
    print(
        f"Config vue par Python :\n"
        f"  DB_HOST={cfg.DB_HOST!r}\n"
        f"  DB_PORT={cfg.DB_PORT!r}\n"
        f"  DB_NAME={cfg.DB_NAME!r}\n"
        f"  DB_USER={cfg.DB_USER!r}\n"
        f"  DB_PASSWORD (<longueur>)={len(pw)}\n"
        f"  DATABASE_URL (masquée)={cfg.DATABASE_URL.split('@')[1] if '@' in cfg.DATABASE_URL else cfg.DATABASE_URL!r}\n"
        f"  RDC_ENV_FILE_ONLY={os.getenv('RDC_ENV_FILE_ONLY', '')!r}\n"
        f"  DATABASE_FROM_URL_ONLY={os.getenv('DATABASE_FROM_URL_ONLY', '')!r}\n"
    )

    try:
        import psycopg2

        conn = psycopg2.connect(cfg.DATABASE_URL)
        conn.close()
        print("Connexion OK.")
        sys.exit(0)
    except Exception as e:
        print(f"ÉCHEC : {e}")
        print(
            "\nVérifie :\n"
            "  1) Le mot de passe utilisateur Postgres sur cette machine (pas forcément « postgres »).\n"
            "  2) psql : PGPASSWORD='ton_mdp' psql -h localhost -U postgres -d rdc_news -c 'select 1'\n"
            "  3) Qu’aucun export shell ne surcharge : unset DB_PASSWORD DB_HOST DATABASE_URL ; puis relance ce script.\n"
            "  4) Évite sudo ./dev-all.sh si tu n’as pas besoin de root — sudo peut changer l’environnement.\n"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
