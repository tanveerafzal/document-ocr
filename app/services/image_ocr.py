import io
from typing import Optional

import easyocr
from PIL import Image

from app.models.responses import TextBlock, BoundingBox


class ImageOCRService:
    _reader: Optional[easyocr.Reader] = None

    @classmethod
    def get_reader(cls, languages: list[str] = None) -> easyocr.Reader:
        if languages is None:
            languages = ["en"]
        if cls._reader is None:
            cls._reader = easyocr.Reader(languages, gpu=False, verbose=False)
        return cls._reader

    @classmethod
    def extract_text(
        cls,
        image_bytes: bytes,
        languages: list[str] = None,
        detail: int = 1
    ) -> tuple[str, list[TextBlock], float]:
        """
        Extract text from image bytes.

        Args:
            image_bytes: Raw image bytes
            languages: List of language codes (default: ["en"])
            detail: 0 for simple output, 1 for detailed output with boxes

        Returns:
            Tuple of (full_text, text_blocks, average_confidence)
        """
        reader = cls.get_reader(languages)

        image = Image.open(io.BytesIO(image_bytes))
        if image.mode != "RGB":
            image = image.convert("RGB")

        results = reader.readtext(
            image_bytes,
            detail=detail,
            paragraph=False
        )

        text_blocks = []
        full_text_parts = []
        total_confidence = 0.0

        for result in results:
            if detail == 1:
                bbox, text, confidence = result
                x_coords = [point[0] for point in bbox]
                y_coords = [point[1] for point in bbox]

                block = TextBlock(
                    text=text,
                    confidence=confidence,
                    bounding_box=BoundingBox(
                        x_min=min(x_coords),
                        y_min=min(y_coords),
                        x_max=max(x_coords),
                        y_max=max(y_coords)
                    )
                )
                text_blocks.append(block)
                full_text_parts.append(text)
                total_confidence += confidence
            else:
                full_text_parts.append(result)

        full_text = " ".join(full_text_parts)
        avg_confidence = total_confidence / len(results) if results else 0.0

        return full_text, text_blocks, avg_confidence

    @classmethod
    def is_available(cls) -> bool:
        try:
            import easyocr
            return True
        except ImportError:
            return False
