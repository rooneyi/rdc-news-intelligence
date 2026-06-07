import os
import re
import unicodedata
import logging

logger = logging.getLogger(__name__)

# Tokens d'instruction Mistral/Llama — s'ils passent dans le prompt, l'utilisateur
# peut overrider les instructions du système (prompt injection).
_INSTRUCTION_TOKENS = re.compile(
    r"\[/?INST\]|<</?SYS>>|\[SYSTEM\]|\[USER\]|\[ASSISTANT\]",
    re.IGNORECASE,
)

# Tentatives courantes de jailbreak détectées en production
_JAILBREAK_PATTERNS = re.compile(
    r"ignore\s+(les\s+)?instructions|oublie\s+(tout|tes\s+instructions)|"
    r"tu\s+es\s+maintenant|new\s+persona|act\s+as|pretend\s+(you\s+are|to\s+be)|"
    r"disregard\s+(all\s+)?previous",
    re.IGNORECASE,
)

_MAX_LEN_MESSAGING = int(os.getenv("INPUT_MAX_LEN_MESSAGING", "800"))
_MAX_LEN_WEB = int(os.getenv("INPUT_MAX_LEN_WEB", "1500"))


def sanitize(text: str, channel: str = "web") -> str:
    """
    Nettoie le texte utilisateur avant injection dans le prompt LLM.
    - Supprime les tokens d'instruction Mistral/Llama
    - Neutralise les tentatives de jailbreak connues
    - Tronque à la longueur max configurable
    - Supprime les caractères de contrôle dangereux
    """
    if not text:
        return ""

    # Normalisation unicode (évite les homoglyphes)
    text = unicodedata.normalize("NFKC", text)

    # Supprimer les octets nuls et caractères de contrôle (sauf \n, \t)
    text = "".join(c for c in text if unicodedata.category(c) != "Cc" or c in "\n\t")

    # Neutraliser les tokens d'instruction : [INST] → (INST)
    original = text
    text = _INSTRUCTION_TOKENS.sub(lambda m: m.group().replace("[", "(").replace("]", ")").replace("<", "(").replace(">", ")"), text)
    if text != original:
        logger.warning("[Sanitizer] Tokens d'instruction neutralisés (canal=%s)", channel)

    # Neutraliser les patterns de jailbreak connus
    if _JAILBREAK_PATTERNS.search(text):
        logger.warning("[Sanitizer] Pattern jailbreak détecté (canal=%s): %.80s", channel, text)
        # On ne bloque pas — on laisse le topic gate et le RAG répondre normalement
        # mais on logue pour monitoring

    # Troncature
    max_len = _MAX_LEN_MESSAGING if channel in {"whatsapp", "telegram"} else _MAX_LEN_WEB
    if len(text) > max_len:
        logger.info("[Sanitizer] Texte tronqué %d→%d chars (canal=%s)", len(text), max_len, channel)
        text = text[:max_len].rstrip()

    return text.strip()
