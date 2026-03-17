from __future__ import annotations

from typing import List

from app.services.crawler.utils import infer_categories

KEYWORDS = {
    "politique": ["politique", "senat", "assemblée", "gouvernement", "élections", "parlement"],
    "societe": ["société", "greve", "grève", "transport", "population", "social"],
    "securite": ["sécurité", "police", "armée", "crime", "attaque", "conflit"],
    "sante": ["santé", "hopital", "hôpital", "maladie", "covid", "soins"],
    "sport": ["sport", "match", "football", "caf", "ligue"],
    "justice": ["justice", "tribunal", "procès", "condamnation", "avocat"],
    "culture": ["culture", "musique", "cinéma", "film", "concert"],
    "environnement": ["environnement", "climat", "écologie", "déforestation", "pollution"],
}


def classify(text: str, fallback_url: str | None = None) -> List[str]:
    text_lower = text.lower()
    found: List[str] = []
    for cat, words in KEYWORDS.items():
        if any(w in text_lower for w in words):
            found.append(cat)
    if not found and fallback_url:
        found = infer_categories(fallback_url)
    return found

