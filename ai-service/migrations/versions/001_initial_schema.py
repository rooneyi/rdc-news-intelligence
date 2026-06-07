"""Initial schema — articles + training_runs

Revision ID: 001
Revises:
Create Date: 2026-06-06
"""
from typing import Sequence, Union
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id          SERIAL PRIMARY KEY,
            title       TEXT NOT NULL,
            content     TEXT NOT NULL,
            source_id   TEXT,
            link        TEXT,
            hash        TEXT,
            categories  TEXT[] DEFAULT '{}',
            image       TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS articles_link_idx
            ON articles(link) WHERE link IS NOT NULL
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS articles_hash_idx
            ON articles(hash) WHERE hash IS NOT NULL
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS training_runs (
            id               SERIAL PRIMARY KEY,
            started_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            ended_at         TIMESTAMP,
            status           TEXT DEFAULT 'running',
            model_name       TEXT,
            processed_count  INTEGER DEFAULT 0,
            reembedded_count INTEGER DEFAULT 0,
            note             TEXT,
            created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS training_runs_started_idx
            ON training_runs(started_at)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS training_runs_status_idx
            ON training_runs(status)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS training_runs CASCADE")
    op.execute("DROP TABLE IF EXISTS articles CASCADE")
