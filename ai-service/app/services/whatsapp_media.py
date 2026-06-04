"""Chargement des images WhatsApp (Meta + Whapi)."""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from app.services.whapi_cloud import (
    decode_whapi_data_uri_image,
    download_whapi_media_bytes,
)

logger = logging.getLogger(__name__)


class WhatsappImageLoadError(Exception):
    """Échec téléchargement / décodage avec message utilisateur."""

    def __init__(self, user_message: str, *, log_detail: str | None = None):
        super().__init__(log_detail or user_message)
        self.user_message = user_message


async def load_whatsapp_image_bytes(
    *,
    transport: str,
    client: httpx.AsyncClient,
    media_id: str | None,
    media_download_url: str | None,
    media_inline_data_uri: str | None,
    meta_auth_headers: dict[str, str],
) -> bytes:
    """
    Charge les octets image (Whapi URL + auth, preview base64, ou Meta Graph API).
    """
    http_url = (
        str(media_download_url).strip()
        if media_download_url and str(media_download_url).strip().startswith("http")
        else None
    )
    preview_uri = (
        str(media_inline_data_uri).strip()
        if media_inline_data_uri
        and str(media_inline_data_uri).strip().startswith("data:image")
        else None
    )
    preview_bytes = decode_whapi_data_uri_image(preview_uri) if preview_uri else None

    if transport == "whapi":
        if http_url:
            data, err = await download_whapi_media_bytes(client, http_url)
            if data:
                logger.info("[Whapi] Image téléchargée via lien HTTP (%s octets).", len(data))
                return data
            logger.warning("[Whapi] Échec lien HTTP : %s — repli preview si disponible.", err)
            if preview_bytes:
                logger.info(
                    "[Whapi] Repli preview webhook (%s octets).",
                    len(preview_bytes),
                )
                return preview_bytes
            raise WhatsappImageLoadError(
                err or "Impossible de télécharger l’image.",
            )
        if preview_bytes:
            logger.info(
                "[Whapi] Image depuis preview webhook (%s octets) — "
                "active Auto Download pour pleine résolution.",
                len(preview_bytes),
            )
            return preview_bytes
        raise WhatsappImageLoadError(
            "Image reçue sans lien téléchargeable. Active « Auto Download » sur Whapi "
            "ou ajoute une légende avec ta question.",
        )

    # Meta Cloud API
    if not media_id:
        raise WhatsappImageLoadError(
            "Identifiant média Meta manquant — réessaie avec une capture plus légère.",
        )

    meta_resp = await client.get(
        f"https://graph.facebook.com/v17.0/{media_id}",
        headers=meta_auth_headers,
    )
    try:
        meta_data: dict[str, Any] = meta_resp.json()
    except ValueError:
        meta_data = {}
    if meta_resp.status_code >= 400:
        logger.error(
            "[WhatsApp] Meta média %s (status=%s): %s",
            media_id,
            meta_resp.status_code,
            meta_data,
        )
        raise WhatsappImageLoadError(
            "Impossible de télécharger l’image depuis WhatsApp (token ou permissions média).",
        )

    media_url = meta_data.get("url")
    if not media_url:
        raise WhatsappImageLoadError(
            "Impossible d’accéder au fichier image via l’API Meta.",
        )

    img_resp = await client.get(str(media_url), headers=meta_auth_headers)
    if img_resp.status_code >= 400 or not img_resp.content:
        raise WhatsappImageLoadError(
            "Meta n’a pas renvoyé le fichier image (lien expiré — renvoie l’image).",
        )
    return img_resp.content
