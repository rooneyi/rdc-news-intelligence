import logging
import os
from io import BytesIO

from PIL import Image
import pytesseract

logger = logging.getLogger(__name__)


class OCRService:
    """Service OCR local basé sur Tesseract.

    Nécessite que le binaire `tesseract` soit installé sur la machine.
    Le langage par défaut est configuré via la variable d'env `OCR_LANG` (ex: "fra+eng").
    """

    def __init__(self) -> None:
        self.lang = os.getenv("OCR_LANG", "fra+eng")

    def extract_text(self, image_bytes: bytes) -> str:
        """Extrait le texte d'une image (bytes) en utilisant Tesseract.

        Retourne une chaîne nettoyée (strip). En cas d'erreur, log et relance l'exception.
        """
        try:
            image = Image.open(BytesIO(image_bytes))
            text = pytesseract.image_to_string(image, lang=self.lang)
            return text.strip()
        except Exception as e:  # noqa: BLE001
            logger.error("Erreur OCR: %s", e)
            raise
