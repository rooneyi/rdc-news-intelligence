import json
import logging
import os
import re
import time
import unicodedata
from collections import Counter
from dataclasses import dataclass

import httpx
from app.db.session import get_db_connection

logger = logging.getLogger(__name__)

GROUP_CHAT_TYPES = {"group", "supergroup"}

THEME_KEYWORDS = {
    "politique": [
        "politique",
        "élection",
        "election",
        "gouvernement",
        "ministre",
        "parlement",
        "assemblée",
        "assemblee",
        "opposition",
        "président",
        "president",
    ],
    "sport": [
        "sport",
        "football",
        "basketball",
        "match",
        "tournoi",
        "compétition",
        "competition",
        "joueur",
        "sélection",
        "selection",
    ],
    "santé": [
        "santé",
        "sante",
        "hôpital",
        "hopital",
        "médecin",
        "medecin",
        "maladie",
        "vaccin",
        "épidémie",
        "epidemie",
    ],
    "guerre": [
        "guerre",
        "conflit",
        "attaque",
        "armée",
        "armee",
        "rebelle",
        "violence",
        "bombardement",
        "sécurité",
        "securite",
    ],
}

COMMON_STOPWORDS = {
    "alors",
    "au",
    "aucun",
    "aussi",
    "autre",
    "avant",
    "avec",
    "avoir",
    "bon",
    "car",
    "ce",
    "cela",
    "ces",
    "ceux",
    "chaque",
    "ci",
    "comme",
    "comment",
    "dans",
    "des",
    "du",
    "dedans",
    "dehors",
    "depuis",
    "devrait",
    "doit",
    "donc",
    "dos",
    "droite",
    "debut",
    "elle",
    "elles",
    "en",
    "encore",
    "essai",
    "est",
    "et",
    "eu",
    "fait",
    "faites",
    "fois",
    "font",
    "hors",
    "ici",
    "il",
    "ils",
    "je",
    "juste",
    "la",
    "le",
    "les",
    "leur",
    "là",
    "ma",
    "maintenant",
    "mais",
    "mes",
    "mine",
    "moins",
    "mon",
    "mot",
    "meme",
    "ni",
    "nommes",
    "notre",
    "nous",
    "nouveaux",
    "ou",
    "où",
    "par",
    "parce",
    "parole",
    "pas",
    "personnes",
    "peut",
    "peu",
    "piece",
    "plupart",
    "pour",
    "pourquoi",
    "quand",
    "que",
    "quel",
    "quelle",
    "quelles",
    "quels",
    "qui",
    "sa",
    "sans",
    "ses",
    "seulement",
    "si",
    "sien",
    "son",
    "sont",
    "sous",
    "soyez",
    "sujet",
    "sur",
    "ta",
    "tandis",
    "tellement",
    "tels",
    "tes",
    "ton",
    "tous",
    "tout",
    "trop",
    "tres",
    "tu",
    "valeur",
    "voie",
    "voient",
    "vont",
    "votre",
    "vous",
    "vu",
    "ça",
    "etaient",
    "etat",
    "etions",
    "ete",
    "etre",
}


@dataclass(frozen=True)
class TopicDecision:
    should_activate: bool
    theme: str | None
    confidence: float
    reason: str = ""


def normalize_text(text: str | None) -> str:
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", text)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(character for character in normalized if unicodedata.category(character) != "Mn")


class TopicGateService:
    def __init__(self) -> None:
        self.model = os.getenv("OLLAMA_MODEL", "mistral")
        self.host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        self.timeout = float(os.getenv("TOPIC_GATE_TIMEOUT", "45"))
        self.min_confidence = float(os.getenv("TOPIC_GATE_MIN_CONFIDENCE", "0.6"))
        self.keyword_mode = os.getenv("TOPIC_GATE_KEYWORD_MODE", "hybrid").lower()
        self.dynamic_keywords_enabled = os.getenv("TOPIC_GATE_DYNAMIC_KEYWORDS", "true").lower() in {"1", "true", "yes"}
        self.dynamic_refresh_seconds = int(os.getenv("TOPIC_GATE_DYNAMIC_REFRESH_SECONDS", "900"))
        self.dynamic_scan_limit = int(os.getenv("TOPIC_GATE_DYNAMIC_SCAN_LIMIT", "2500"))
        self.dynamic_top_per_theme = int(os.getenv("TOPIC_GATE_DYNAMIC_TOP_PER_THEME", "25"))
        self.dynamic_min_frequency = int(os.getenv("TOPIC_GATE_DYNAMIC_MIN_FREQUENCY", "4"))
        self.dynamic_min_word_len = int(os.getenv("TOPIC_GATE_DYNAMIC_MIN_WORD_LEN", "4"))
        self._dynamic_keywords_by_theme: dict[str, list[str]] = {theme: [] for theme in THEME_KEYWORDS}
        self._last_dynamic_refresh = 0.0

    def is_group_chat(self, chat_type: str | None) -> bool:
        return (chat_type or "").lower() in GROUP_CHAT_TYPES

    def merge_text(self, *parts: str | None) -> str:
        cleaned_parts = [cleaned for part in parts if (cleaned := normalize_text(part))]
        return normalize_text(" ".join(cleaned_parts))

    def detect_whatsapp_scope(self, value: dict, message: dict) -> str:
        def _safe_nested_get(source: dict, *keys: str) -> str | None:
            current: object = source
            for key in keys:
                if not isinstance(current, dict):
                    return None
                current = current.get(key)
                if current is None:
                    return None
            return current if isinstance(current, str) else None

        candidates = [
            message.get("chat_type"),
            message.get("recipient_type"),
            _safe_nested_get(message, "message_context", "chat_type"),
            _safe_nested_get(message, "context", "chat_type"),
            value.get("chat_type"),
            _safe_nested_get(value, "metadata", "chat_type"),
        ]

        for candidate in candidates:
            if isinstance(candidate, str):
                normalized = candidate.lower()
                if normalized in GROUP_CHAT_TYPES:
                    return "group"
                if normalized == "private":
                    return "private"

        if message.get("source") == "group" or message.get("is_group") is True:
            return "group"

        return "private"

    async def classify(self, text: str) -> TopicDecision:
        cleaned_text = normalize_text(text)
        if not cleaned_text:
            return TopicDecision(False, None, 0.0, "empty_text")

        keyword_decision = self._keyword_fallback(cleaned_text, reason="keywords_first")
        if self.keyword_mode == "keywords-first" and keyword_decision.should_activate:
            return keyword_decision

        prompt = (
            "Tu es un classifieur binaire très strict pour un bot de veille en RDC. "
            "Analyse le message et réponds uniquement avec un JSON valide, sans texte autour. "
            "Les thèmes autorisés sont: politique, sport, santé, guerre. "
            "Si le message est hors thème, réponds avec is_relevant=false. "
            "Schéma attendu: {\"is_relevant\": true|false, \"theme\": \"politique|sport|santé|guerre|null\", "
            "\"confidence\": 0.0-1.0, \"reason\": \"courte justification\"}. "
            f"Message: {cleaned_text}"
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.host}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0,
                            "num_predict": 120,
                        },
                    },
                )
                response.raise_for_status()

            payload = response.json()
            raw_text = str(payload.get("response", "")).strip()
            decision = self._parse_model_response(raw_text, cleaned_text)
            if decision.should_activate:
                return decision

            if self.keyword_mode in {"hybrid", "keywords-first"} and keyword_decision.should_activate:
                return keyword_decision

            return decision
        except Exception as exc:  # noqa: BLE001
            logger.error("[TopicGate] Erreur de classification IA: %s", exc)
            return self._keyword_fallback(cleaned_text, reason=str(exc))

    def _parse_model_response(self, raw_text: str, cleaned_text: str) -> TopicDecision:
        candidate = self._extract_json_block(raw_text)
        if not candidate:
            return self._keyword_fallback(cleaned_text, reason="json_not_found")

        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            return self._keyword_fallback(cleaned_text, reason="json_decode_failed")

        theme = self._normalize_theme(data.get("theme"))
        is_relevant = bool(data.get("is_relevant"))
        confidence = self._coerce_confidence(data.get("confidence"), default=0.7 if theme else 0.0)
        reason = str(data.get("reason", "")).strip()

        if theme and confidence >= self.min_confidence:
            return TopicDecision(True, theme, confidence, reason)

        if is_relevant and theme and confidence > 0:
            return TopicDecision(confidence >= self.min_confidence, theme, confidence, reason or "low_confidence")

        if theme:
            return TopicDecision(confidence >= self.min_confidence, theme, confidence, reason or "theme_detected")

        if is_relevant:
            return TopicDecision(confidence >= self.min_confidence, None, confidence, reason or "model_relevant_no_theme")

        return TopicDecision(False, None, confidence, reason or "not_relevant")

    def _keyword_fallback(self, cleaned_text: str, reason: str) -> TopicDecision:
        normalized = strip_accents(cleaned_text.lower())
        self._refresh_dynamic_keywords_if_needed()

        for theme, static_keywords in THEME_KEYWORDS.items():
            dynamic_keywords = self._dynamic_keywords_by_theme.get(theme, [])
            keywords = [*static_keywords, *dynamic_keywords]
            for keyword in keywords:
                if strip_accents(keyword.lower()) in normalized:
                    canonical_theme = self._normalize_theme(theme)
                    return TopicDecision(True, canonical_theme, 0.75, f"fallback_keyword:{reason}")

        return TopicDecision(False, None, 0.0, f"fallback_no_match:{reason}")

    def _normalize_theme(self, value: object) -> str | None:
        if not isinstance(value, str):
            return None

        normalized = strip_accents(value.strip().lower())
        if normalized in {"politique"}:
            return "politique"
        if normalized == "sport":
            return "sport"
        if normalized in {"sante", "santé"}:
            return "santé"
        if normalized == "guerre":
            return "guerre"
        return None

    def _coerce_confidence(self, value: object, default: float = 0.0) -> float:
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            confidence = default

        if confidence < 0:
            return 0.0
        if confidence > 1:
            return 1.0
        return confidence

    def _extract_json_block(self, text: str) -> str | None:
        stripped = text.strip()
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)

        if stripped.startswith("{") and stripped.endswith("}"):
            return stripped

        match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
        if match:
            return match.group(0)

        return None

    def _refresh_dynamic_keywords_if_needed(self) -> None:
        if not self.dynamic_keywords_enabled:
            return

        now = time.time()
        if now - self._last_dynamic_refresh < self.dynamic_refresh_seconds:
            return

        self._last_dynamic_refresh = now
        self._dynamic_keywords_by_theme = self._load_dynamic_keywords_from_db()

    def _load_dynamic_keywords_from_db(self) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {theme: [] for theme in THEME_KEYWORDS}

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COALESCE(title, ''), COALESCE(content, '')
                FROM articles
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (self.dynamic_scan_limit,),
            )
            rows = cursor.fetchall()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[TopicGate] Impossible de charger les mots-clés dynamiques: %s", exc)
            return result
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()

        if not rows:
            return result

        counters: dict[str, Counter] = {theme: Counter() for theme in THEME_KEYWORDS}
        normalized_seed_by_theme = {
            theme: [strip_accents(keyword.lower()) for keyword in keywords]
            for theme, keywords in THEME_KEYWORDS.items()
        }

        for title, content in rows:
            merged = normalize_text(f"{title} {content}")
            if not merged:
                continue

            normalized_text = strip_accents(merged.lower())
            tokens = self._extract_tokens(normalized_text)
            if not tokens:
                continue

            matched_themes: set[str] = set()
            for theme, seeds in normalized_seed_by_theme.items():
                if any(seed in normalized_text for seed in seeds):
                    matched_themes.add(theme)

            for theme in matched_themes:
                counters[theme].update(tokens)

        for theme, counter in counters.items():
            seeds = set(normalized_seed_by_theme[theme])
            selected: list[str] = []
            for word, frequency in counter.most_common(self.dynamic_top_per_theme * 6):
                if frequency < self.dynamic_min_frequency:
                    continue
                if word in COMMON_STOPWORDS:
                    continue
                if word in seeds:
                    continue
                if len(word) < self.dynamic_min_word_len:
                    continue
                selected.append(word)
                if len(selected) >= self.dynamic_top_per_theme:
                    break
            result[theme] = selected

        logger.info(
            "[TopicGate] Mots-clés dynamiques chargés: %s",
            {theme: len(words) for theme, words in result.items()},
        )
        return result

    def _extract_tokens(self, text: str) -> list[str]:
        tokens = re.findall(r"[a-zA-Z]{2,}", text)
        return [token.lower() for token in tokens]
