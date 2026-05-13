"""
Intégration Whapi.Cloud : parsing des webhooks entrants et envoi des réponses via API REST.

Doc format messages : https://support.whapi.cloud/help-desk/receiving/webhooks/incoming-webhooks-format/incoming-message
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Literal

import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WhapiInbound:
    """Message normalisé pour le pipeline RAG (même logique que WhatsApp Meta)."""

    chat_id: str
    message_id: str | None
    is_group: bool
    kind: Literal["text", "image"]
    text: str | None
    image_url: str | None
    caption: str | None


def _is_group_chat(chat_id: str) -> bool:
    return chat_id.endswith("@g.us")


def _extract_text_and_media(msg: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    """
    Retourne (texte pour RAG, url image si présente, légende).
    """
    mtype = (msg.get("type") or "").lower()
    text_out: str | None = None
    image_url: str | None = None
    caption: str | None = None

    if mtype == "text":
        t = msg.get("text") or {}
        if isinstance(t, dict):
            text_out = (t.get("body") or "").strip() or None
        return text_out, None, None

    if mtype == "link_preview":
        lp = msg.get("link_preview") or {}
        if isinstance(lp, dict):
            text_out = (lp.get("body") or "").strip() or None
        return text_out, None, None

    if mtype in {"image", "sticker", "video", "audio"}:
        blob = msg.get(mtype)
        if isinstance(blob, dict):
            caption = (blob.get("caption") or "").strip() or None
            image_url = blob.get("link")
            if isinstance(image_url, str) and image_url.startswith("http"):
                return None, image_url, caption
            prev = blob.get("preview")
            if isinstance(prev, str) and prev.startswith("data:image"):
                logger.warning(
                    "[Whapi] Média sans lien HTTP (preview base64 seulement). "
                    "Active « Auto Download » sur Whapi ou envoie une image avec lien."
                )
        return None, image_url, caption

    if mtype == "document":
        doc = msg.get("document") or {}
        if isinstance(doc, dict):
            caption = (doc.get("caption") or "").strip() or None
            link = doc.get("link")
            mime = (doc.get("mime_type") or "").lower()
            if isinstance(link, str) and link.startswith("http"):
                if mime.startswith("image/"):
                    return None, link, caption
                text_out = caption or f"[document:{doc.get('file_name') or 'fichier'}]"
                return text_out, None, caption

    return None, None, None


def parse_whapi_payload(payload: dict[str, Any]) -> list[WhapiInbound]:
    """
    Transforme le JSON Whapi en liste de messages à traiter (ignore from_me, statuts).
    """
    out: list[WhapiInbound] = []
    raw_messages = payload.get("messages")
    if not isinstance(raw_messages, list):
        return out

    for msg in raw_messages:
        if not isinstance(msg, dict):
            continue
        if msg.get("from_me") is True:
            continue

        chat_id = str(msg.get("chat_id") or "").strip()
        if not chat_id:
            continue

        mid = msg.get("id")
        message_id = str(mid) if mid is not None else None
        is_group = _is_group_chat(chat_id)

        text_part, image_url, caption = _extract_text_and_media(msg)

        if image_url:
            out.append(
                WhapiInbound(
                    chat_id=chat_id,
                    message_id=message_id,
                    is_group=is_group,
                    kind="image",
                    text=None,
                    image_url=image_url,
                    caption=caption,
                )
            )
            continue

        if text_part:
            out.append(
                WhapiInbound(
                    chat_id=chat_id,
                    message_id=message_id,
                    is_group=is_group,
                    kind="text",
                    text=text_part,
                    image_url=None,
                    caption=None,
                )
            )
            continue

    return out


def whapi_config_ok() -> bool:
    return bool((os.getenv("WHAPI_TOKEN") or "").strip())


async def whapi_send_text(to_chat_id: str, body: str) -> None:
    """POST /messages/text sur gate.whapi.cloud (ou WHAPI_API_BASE)."""
    token = (os.getenv("WHAPI_TOKEN") or "").strip()
    if not token:
        logger.error("[Whapi] WHAPI_TOKEN manquant — impossible d’envoyer la réponse.")
        return

    base = (os.getenv("WHAPI_API_BASE") or "https://gate.whapi.cloud").rstrip("/")
    url = f"{base}/messages/text"
    timeout = float(os.getenv("WHAPI_HTTP_TIMEOUT", "60"))

    payload = {"to": to_chat_id, "body": body}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code >= 400:
            logger.error(
                "[Whapi] Envoi texte échoué (%s): %s",
                resp.status_code,
                (resp.text or "")[:500],
            )
            return
        logger.info("[Whapi] Message envoyé vers %s", to_chat_id[:40])


def whapi_webhook_secret_expected() -> str:
    return (os.getenv("WHAPI_WEBHOOK_SECRET") or "").strip()
