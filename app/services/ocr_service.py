import pytesseract
from PIL import Image
import logging

logger = logging.getLogger(__name__)

def extract_text_from_image(image_path: str, lang: str = "eng") -> str:
    logger.info(f"Mengekstrak teks dari gambar: {image_path} (bahasa: {lang})")
    img = Image.open(image_path)
    teks = pytesseract.image_to_string(img, lang=lang).strip()
    logger.info(f"Hasil ekstraksi OCR ({len(teks)} karakter):\n--- MULAI TEKS ---\n{teks}\n--- AKHIR TEKS ---")
    return teks
