from fastapi import APIRouter

from app.models.responses import HealthResponse
from app.services.image_ocr import ImageOCRService
from app.services.pdf_ocr import PDFOCRService

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check the health status of the OCR service."""
    return HealthResponse(
        status="healthy",
        easyocr_available=ImageOCRService.is_available(),
        tesseract_available=PDFOCRService.is_available()
    )
