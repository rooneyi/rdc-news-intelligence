import json
import logging
import os
import re
import unicodedata
from dataclasses import dataclass

import httpx

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
            return self._parse_model_response(raw_text, cleaned_text)
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
        for theme, keywords in THEME_KEYWORDS.items():
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
