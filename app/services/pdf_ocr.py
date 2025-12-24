import io
import tempfile
import subprocess
from pathlib import Path

import fitz

from app.models.responses import PageResult


class PDFOCRService:

    @classmethod
    def extract_text(cls, pdf_bytes: bytes) -> tuple[list[PageResult], float]:
        """
        Extract text from PDF bytes using OCRmyPDF.

        Args:
            pdf_bytes: Raw PDF bytes

        Returns:
            Tuple of (page_results, average_confidence)
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            input_path = tmp_path / "input.pdf"
            output_path = tmp_path / "output.pdf"

            input_path.write_bytes(pdf_bytes)

            subprocess.run(
                [
                    "ocrmypdf",
                    "--force-ocr",
                    "--sidecar", str(tmp_path / "text.txt"),
                    "--output-type", "pdf",
                    str(input_path),
                    str(output_path)
                ],
                capture_output=True,
                check=True
            )

            page_results = cls._extract_pages_from_pdf(output_path)

        return page_results

    @classmethod
    def _extract_pages_from_pdf(cls, pdf_path: Path) -> list[PageResult]:
        """Extract text from each page of the OCR'd PDF."""
        doc = fitz.open(str(pdf_path))
        results = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()

            results.append(PageResult(
                page_number=page_num + 1,
                text=text.strip(),
                confidence=None
            ))

        doc.close()
        return results

    @classmethod
    def extract_text_from_native_pdf(cls, pdf_bytes: bytes) -> list[PageResult]:
        """
        Extract text from native (already searchable) PDF without OCR.

        Args:
            pdf_bytes: Raw PDF bytes

        Returns:
            List of page results
        """
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        results = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()

            results.append(PageResult(
                page_number=page_num + 1,
                text=text.strip(),
                confidence=None
            ))

        doc.close()
        return results

    @classmethod
    def is_available(cls) -> bool:
        try:
            result = subprocess.run(
                ["ocrmypdf", "--version"],
                capture_output=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
