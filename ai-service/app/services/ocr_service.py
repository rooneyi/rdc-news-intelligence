import logging
import os
import shutil
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError
import pytesseract

logger = logging.getLogger(__name__)


class OCRService:
    """Service OCR local basé sur Tesseract.

    Nécessite que le binaire `tesseract` soit installé sur la machine.
    Le langage par défaut est configuré via la variable d'env `OCR_LANG` (ex: "fra+eng").
    """

    def __init__(self) -> None:
        self.lang = os.getenv("OCR_LANG", "fra+eng")
        self._tesseract_cmd = (os.getenv("TESSERACT_CMD") or "").strip() or None
        if self._tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self._tesseract_cmd

    @staticmethod
    def is_tesseract_available() -> bool:
        cmd = (os.getenv("TESSERACT_CMD") or "").strip() or "tesseract"
        return bool(shutil.which(cmd))

    def _prepare_image(self, image_bytes: bytes) -> Image.Image:
        if len(image_bytes) < 64:
            raise ValueError("Fichier image trop petit ou vide.")
        try:
            image = Image.open(BytesIO(image_bytes))
            image.load()
        except UnidentifiedImageError as exc:
            raise ValueError(
                "Format d’image non reconnu (JPEG/PNG/WebP attendu). "
                "Vérifie Auto Download Whapi ou renvoie une capture."
            ) from exc
        image = ImageOps.exif_transpose(image)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        w, h = image.size
        min_side = min(w, h)
        target = int(os.getenv("OCR_MIN_SIDE_PX", "900"))
        if min_side > 0 and min_side < target:
            scale = target / min_side
            image = image.resize(
                (max(1, int(w * scale)), max(1, int(h * scale))),
                Image.Resampling.LANCZOS,
            )
        return image

    def extract_text(self, image_bytes: bytes) -> str:
        """Extrait le texte d'une image (bytes) en utilisant Tesseract."""
        if not self.is_tesseract_available():
            raise RuntimeError(
                "Tesseract introuvable sur le serveur (installe tesseract-ocr et tesseract-ocr-fra)."
            )
        try:
            image = self._prepare_image(image_bytes)
            text = pytesseract.image_to_string(image, lang=self.lang)
            return text.strip()
        except Exception as e:  # noqa: BLE001
            logger.error("Erreur OCR (%s octets): %s", len(image_bytes), e)
            raise
