"""
Rejoue un fichier JSONL généré par le crawler vers l'API FastAPI /crawler/articles/batch.
Usage:
    python -m app.services.crawler.scripts.replay_jsonl --source-id radiookapi.net \
        --file data/crawler/radiookapi.net.jsonl \
        --endpoint http://127.0.0.1:8000 \
        --batch-size 50

L'endpoint par défaut est pris dans CRAWLER_BACKEND_ENDPOINT ou http://127.0.0.1:8000.
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Iterable, List

import httpx

DEFAULT_ENDPOINT = "http://127.0.0.1:8000"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def chunk(iterable: Iterable[dict], size: int) -> Iterable[List[dict]]:
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def replay(file_path: Path, endpoint: str, batch_size: int, token: str | None) -> None:
    if not file_path.exists():
        raise FileNotFoundError(file_path)

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    client = httpx.Client(timeout=30)
    url = f"{endpoint.rstrip('/')}/crawler/articles/batch"
    logger.info("Rejoue %s vers %s", file_path, url)

    with file_path.open("r", encoding="utf-8") as f:
        rows = (json.loads(line) for line in f)
        total_sent = 0
        for batch in chunk(rows, batch_size):
            resp = client.post(url, headers=headers, json=batch)
            if resp.is_error:
                logger.error("Batch échoué (%s): %s", resp.status_code, resp.text)
                resp.raise_for_status()
            data = resp.json()
            saved = data.get("saved") or data.get("status")
            total_sent += len(batch)
            logger.info("Batch ok: %s (total envoyés: %d)", saved, total_sent)
    client.close()
    logger.info("Terminé: %d articles envoyés", total_sent)


def main() -> int:
    parser = argparse.ArgumentParser(description="Rejouer un JSONL du crawler vers l'API")
    parser.add_argument("--file", required=True, help="Chemin du fichier JSONL (ex: data/crawler/radiookapi.net.jsonl)")
    parser.add_argument("--endpoint", default=None, help="Endpoint API (défaut: env CRAWLER_BACKEND_ENDPOINT ou http://127.0.0.1:8000)")
    parser.add_argument("--batch-size", type=int, default=50, help="Taille des batches")
    parser.add_argument("--token", default=None, help="Token Bearer optionnel")
    args = parser.parse_args()

    import os

    endpoint = args.endpoint or os.getenv("CRAWLER_BACKEND_ENDPOINT") or DEFAULT_ENDPOINT
    token = args.token or os.getenv("CRAWLER_BACKEND_TOKEN") or os.getenv("BACKEND_TOKEN")

    replay(Path(args.file), endpoint, args.batch_size, token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

