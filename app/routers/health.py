from fastapi import APIRouter

from app.models.responses import HealthResponse
from app.services.image_ocr import ImageOCRService
from app.services.pdf_ocr import PDFOCRService
from app.config import BUILD_NUMBER

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check the health status of the OCR service."""
    return HealthResponse(
        status="healthy",
        build=BUILD_NUMBER,
        easyocr_available=ImageOCRService.is_available(),
        tesseract_available=PDFOCRService.is_available()
    )


@router.get("/health/db")
async def db_health_check():
    """Check database connectivity and return log count."""
    from app.database import init_db, get_db_session, RequestLog

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        return {
            "status": "error",
            "message": "DATABASE_URL not set",
            "database_url": None
        }

    try:
        init_db()
        db = get_db_session()
        count = db.query(RequestLog).count()
        db.close()
        return {
            "status": "healthy",
            "message": "Database connected",
            "database_url": db_url[:50] + "...",
            "log_count": count
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "database_url": db_url[:50] + "..."
        }
