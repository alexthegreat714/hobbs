"""
OCR Adapter for Hobbs Agent Vision System.

Provides optical character recognition using local OCR models
with graceful fallback when not available.
"""

from typing import Any, Dict, List, Optional
from pathlib import Path

from config.settings import logger


# Try to import OCR libraries
OCR_AVAILABLE = False
OCR_ENGINE = None

# Try pytesseract first (most common)
try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
    OCR_ENGINE = "pytesseract"
    logger.info("pytesseract OCR is available")
except ImportError:
    pass

# Try easyocr as fallback
if not OCR_AVAILABLE:
    try:
        import easyocr
        OCR_AVAILABLE = True
        OCR_ENGINE = "easyocr"
        logger.info("easyocr is available")
    except ImportError:
        pass

if not OCR_AVAILABLE:
    logger.warning("No OCR engine available - OCR will return empty results")


class OCRAdapter:
    """
    OCR adapter for text extraction from images.

    Supports:
    - pytesseract (Tesseract OCR)
    - easyocr
    - Fallback mode returning empty results
    """

    def __init__(self):
        """Initialize the OCR adapter."""
        self.available = OCR_AVAILABLE
        self.engine = OCR_ENGINE
        self._easyocr_reader = None

        if self.engine == "easyocr":
            try:
                import easyocr
                self._easyocr_reader = easyocr.Reader(['en'], verbose=False)
            except Exception as e:
                logger.warning(f"Failed to initialize easyocr: {e}")
                self.available = False

    def run_ocr(self, image_path: str) -> Dict[str, Any]:
        """
        Run OCR on an image to extract text.

        Args:
            image_path: Path to the image file

        Returns:
            Dictionary with extracted text:
            {
                "text": "full extracted text",
                "lines": ["line1", "line2", ...],
                "engine": "pytesseract" or "easyocr" or "none",
                "available": bool
            }
        """
        result = {
            "text": "",
            "lines": [],
            "engine": "none",
            "available": self.available
        }

        if not self.available:
            logger.debug("OCR not available, returning empty text")
            return result

        try:
            # Verify image exists
            if not Path(image_path).exists():
                logger.warning(f"Image not found: {image_path}")
                return result

            if self.engine == "pytesseract":
                result = self._run_pytesseract(image_path)
            elif self.engine == "easyocr":
                result = self._run_easyocr(image_path)

        except Exception as e:
            logger.error(f"OCR failed: {e}")

        return result

    def _run_pytesseract(self, image_path: str) -> Dict[str, Any]:
        """Run pytesseract OCR."""
        import pytesseract
        from PIL import Image

        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)

        lines = [line.strip() for line in text.split('\n') if line.strip()]

        return {
            "text": text.strip(),
            "lines": lines,
            "engine": "pytesseract",
            "available": True
        }

    def _run_easyocr(self, image_path: str) -> Dict[str, Any]:
        """Run easyocr."""
        if self._easyocr_reader is None:
            return {
                "text": "",
                "lines": [],
                "engine": "none",
                "available": False
            }

        results = self._easyocr_reader.readtext(image_path)

        lines = [r[1] for r in results]
        text = "\n".join(lines)

        return {
            "text": text,
            "lines": lines,
            "engine": "easyocr",
            "available": True
        }

    def get_status(self) -> Dict[str, Any]:
        """Get adapter status."""
        return {
            "available": self.available,
            "engine": self.engine if self.available else None
        }


# Singleton instance
ocr_adapter = OCRAdapter()
