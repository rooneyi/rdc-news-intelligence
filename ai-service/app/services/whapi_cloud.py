"""
Intégration Whapi.Cloud : parsing des webhooks entrants et envoi des réponses via API REST.

Doc format messages : https://support.whapi.cloud/help-desk/receiving/webhooks/incoming-webhooks-format/incoming-message
"""
from __future__ import annotations

import base64
import binascii
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
    # Si pas de ``link`` HTTP (Auto Download off), Whapi envoie souvent ``preview`` data:image;base64,...
    image_data_uri: str | None = None


def decode_whapi_data_uri_image(data_uri: str) -> bytes | None:
    """Décode ``data:image/...;base64,...`` renvoyé dans les webhooks Whapi."""
    raw = (data_uri or "").strip()
    if not raw.startswith("data:image") or "," not in raw:
        return None
    try:
        b64 = raw.split(",", 1)[1].strip()
        out = base64.b64decode(b64)
        return out if len(out) > 32 else None
    except (binascii.Error, ValueError, IndexError):
        return None


def _is_group_chat(chat_id: str) -> bool:
    return chat_id.endswith("@g.us")


def _from_me_truthy(msg: dict[str, Any]) -> bool:
    v = msg.get("from_me")
    if v is True:
        return True
    if isinstance(v, str) and v.strip().lower() in {"true", "1", "yes", "on"}:
        return True
    return False


def _http_media_link(blob: dict[str, Any]) -> str | None:
    for k in ("link", "url", "media_url", "download_url"):
        v = blob.get(k)
        if isinstance(v, str) and v.strip().lower().startswith("http"):
            return v.strip()
    return None


def _preview_data_uri(blob: dict[str, Any]) -> str | None:
    prev = blob.get("preview")
    if isinstance(prev, str) and prev.strip().startswith("data:image"):
        return prev.strip()
    return None


def _iter_whapi_message_dicts(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Messages ``post`` (``messages``) et mises à jour ``patch`` (``messages_updates[].after_update``).
    """
    root = payload
    if not isinstance(root.get("messages"), list) and isinstance(root.get("data"), dict):
        root = root["data"]

    collected: list[dict[str, Any]] = []
    raw = root.get("messages")
    if isinstance(raw, list):
        for m in raw:
            if isinstance(m, dict):
                collected.append(m)

    updates = root.get("messages_updates")
    if isinstance(updates, list):
        for upd in updates:
            if not isinstance(upd, dict):
                continue
            after = upd.get("after_update")
            if isinstance(after, dict) and after.get("type") and after.get("chat_id"):
                collected.append(after)

    # Même id : la dernière entrée gagne (ex. patch ``after_update`` avec ``link`` après un post preview).
    by_id: dict[str, dict[str, Any]] = {}
    anon_i = 0
    for m in collected:
        mid = m.get("id")
        key = str(mid) if mid is not None else ""
        if not key:
            key = f"__anon_{anon_i}"
            anon_i += 1
        by_id[key] = m
    return list(by_id.values())


def _extract_text_and_media(
    msg: dict[str, Any],
) -> tuple[str | None, str | None, str | None, str | None]:
    """
    Retourne (texte pour RAG, url image si présente, légende, data_uri preview image).
    """
    mtype = (msg.get("type") or "").lower()
    text_out: str | None = None
    image_url: str | None = None
    caption: str | None = None
    data_uri: str | None = None

    if mtype == "text":
        t = msg.get("text") or {}
        if isinstance(t, dict):
            text_out = (t.get("body") or "").strip() or None
        return text_out, None, None, None

    if mtype == "link_preview":
        lp = msg.get("link_preview") or {}
        if isinstance(lp, dict):
            text_out = (lp.get("body") or "").strip() or None
        return text_out, None, None, None

    if mtype in {"image", "sticker", "video", "audio", "gif"}:
        blob = msg.get(mtype)
        if not isinstance(blob, dict) and mtype == "gif":
            blob = msg.get("GIF")
        if isinstance(blob, dict):
            caption = (blob.get("caption") or "").strip() or None
            link = _http_media_link(blob)
            if link:
                return None, link, caption, None
            prev = _preview_data_uri(blob)
            if prev:
                logger.info(
                    "[Whapi] Média type=%s : pas de lien HTTP — traitement via preview embarqué "
                    "(qualité réduite). Active « Auto Download » sur Whapi pour un lien pleine taille.",
                    mtype,
                )
                return None, None, caption, prev
            logger.info(
                "[Whapi] Média type=%s ignoré : pas de lien HTTP ni preview data:image "
                "(clés blob=%s — active « Auto Download » ou renvoie une capture).",
                mtype,
                sorted(blob.keys())[:20],
            )
        return None, None, caption, None

    if mtype == "document":
        doc = msg.get("document") or {}
        if isinstance(doc, dict):
            caption = (doc.get("caption") or "").strip() or None
            link = _http_media_link(doc)
            mime = (doc.get("mime_type") or "").lower()
            if link:
                if mime.startswith("image/"):
                    return None, link, caption, None
                text_out = caption or f"[document:{doc.get('file_name') or 'fichier'}]"
                return text_out, None, caption, None
            prev = _preview_data_uri(doc)
            if mime.startswith("image/") and prev:
                logger.info(
                    "[Whapi] Document image sans lien HTTP — traitement via preview (mime=%s).",
                    mime,
                )
                return None, None, caption, prev

    return None, None, None, None


def parse_whapi_payload(payload: dict[str, Any]) -> list[WhapiInbound]:
    """
    Transforme le JSON Whapi en liste de messages à traiter (ignore from_me, statuts).
    """
    out: list[WhapiInbound] = []
    raw_messages = _iter_whapi_message_dicts(payload)
    if not raw_messages:
        return out

    for msg in raw_messages:
        if not isinstance(msg, dict):
            continue
        if _from_me_truthy(msg):
            continue

        chat_id = str(msg.get("chat_id") or "").strip()
        if not chat_id:
            continue

        mid = msg.get("id")
        message_id = str(mid) if mid is not None else None
        is_group = _is_group_chat(chat_id)

        text_part, image_url, caption, image_data_uri = _extract_text_and_media(msg)

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
                    image_data_uri=None,
                )
            )
            continue

        if image_data_uri:
            out.append(
                WhapiInbound(
                    chat_id=chat_id,
                    message_id=message_id,
                    is_group=is_group,
                    kind="image",
                    text=None,
                    image_url=None,
                    caption=caption,
                    image_data_uri=image_data_uri,
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
                    image_data_uri=None,
                )
            )
            continue

        logger.info(
            "[Whapi] Message ignoré pour RAG type=%r chat_id=%s",
            msg.get("type"),
            chat_id[:60] + ("…" if len(chat_id) > 60 else ""),
        )

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
