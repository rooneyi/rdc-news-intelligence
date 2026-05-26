#!/usr/bin/env python3
"""Retire les sources sans article en BDD et enrichit le catalogue EN/SW."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
_SOURCES = _ROOT / "data" / "crawler" / "sources.json"

_EN_IDS = {
    "voanews.com",
    "bbc-world",
    "dw.com-world",
    "theguardian.com",
    "who.int",
    "reliefweb.int",
    "brusselstimes.com",
    "project-syndicate.org",
}

_NEW_EN = [
    {
        "sourceId": "bbc.com-africa-en",
        "sourceKind": "wordpress",
        "sourceLang": "en",
        "sourceUrl": "https://www.bbc.com",
        "rssUrl": "https://feeds.bbci.co.uk/news/world/africa/rss.xml",
        "requiresRateLimit": True,
    },
    {
        "sourceId": "theguardian.com-africa-en",
        "sourceKind": "wordpress",
        "sourceLang": "en",
        "sourceUrl": "https://www.theguardian.com",
        "rssUrl": "https://www.theguardian.com/world/africa/rss",
        "requiresRateLimit": True,
    },
    {
        "sourceId": "dw.com-en-africa",
        "sourceKind": "wordpress",
        "sourceLang": "en",
        "sourceUrl": "https://www.dw.com",
        "rssUrl": "https://rss.dw.com/xml/rss-en-africa",
        "requiresRateLimit": True,
    },
]

_NEW_SW = [
    {
        "sourceId": "rfi.fr-swahili",
        "sourceKind": "wordpress",
        "sourceLang": "sw",
        "sourceUrl": "https://www.rfi.fr/sw",
        "rssUrl": "https://www.rfi.fr/sw/rss",
        "requiresRateLimit": True,
    },
]


def main() -> None:
    load_dotenv(_ROOT / ".env_file")
    load_dotenv(_ROOT / ".env")
    data = json.loads(_SOURCES.read_text(encoding="utf-8"))
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT source_id, COUNT(*) FROM articles GROUP BY source_id")
    counts = dict(cur.fetchall())
    cur.close()
    conn.close()

    removed: list[str] = []

    for kind in ("html", "wordpress"):
        kept = []
        for item in data["sources"].get(kind, []):
            sid = item.get("sourceId")
            if sid and counts.get(sid, 0) == 0:
                removed.append(sid)
                continue
            if sid in _EN_IDS:
                item["sourceLang"] = "en"
            kept.append(item)
        data["sources"][kind] = kept

    existing = {i["sourceId"] for k in ("html", "wordpress") for i in data["sources"][k]}
    for entry in _NEW_EN + _NEW_SW:
        if entry["sourceId"] not in existing:
            data["sources"]["wordpress"].append(entry)
            print(f"+ ajouté {entry['sourceId']} ({entry['sourceLang']})")

    _SOURCES.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Retiré {len(removed)} sources vides:", ", ".join(sorted(removed)))
    print(f"Catalogue: {sum(len(data['sources'][k]) for k in ('html','wordpress'))} sources")


if __name__ == "__main__":
    main()
