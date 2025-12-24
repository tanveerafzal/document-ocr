import time
from typing import Optional
from io import BytesIO

from fastapi import APIRouter, File, UploadFile, HTTPException, Query, Depends
from PIL import Image

from app.models.responses import OCRResponse, PageResult, DocumentExtractResponse
from app.services.image_ocr import ImageOCRService
from app.services.pdf_ocr import PDFOCRService
from app.services.document_extractor import DocumentExtractorService
from app.auth import verify_api_key

router = APIRouter(prefix="/ocr", tags=["ocr"], dependencies=[Depends(verify_api_key)])

ALLOWED_IMAGE_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/tiff",
    "image/bmp",
    "image/webp"
}

ALLOWED_PDF_TYPES = {
    "application/pdf"
}


@router.post("/image", response_model=OCRResponse)
async def extract_text_from_image(
    file: UploadFile = File(...),
    languages: Optional[str] = Query(
        default="en",
        description="Comma-separated language codes (e.g., 'en,fr,de')"
    )
) -> OCRResponse:
    """
    Extract text from an uploaded image using EasyOCR.

    Supported formats: PNG, JPG, JPEG, TIFF, BMP, WEBP
    """
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. "
                   f"Allowed types: {', '.join(ALLOWED_IMAGE_TYPES)}"
        )

    start_time = time.time()

    try:
        image_bytes = await file.read()
        lang_list = [lang.strip() for lang in languages.split(",")]

        full_text, blocks, avg_confidence = ImageOCRService.extract_text(
            image_bytes,
            languages=lang_list
        )

        processing_time = time.time() - start_time

        return OCRResponse(
            success=True,
            filename=file.filename or "unknown",
            file_type="image",
            text=full_text,
            blocks=blocks,
            pages=[PageResult(
                page_number=1,
                text=full_text,
                confidence=avg_confidence,
                blocks=blocks
            )],
            processing_time_seconds=round(processing_time, 3)
        )

    except Exception as e:
        processing_time = time.time() - start_time
        return OCRResponse(
            success=False,
            filename=file.filename or "unknown",
            file_type="image",
            processing_time_seconds=round(processing_time, 3),
            error=str(e)
        )


@router.post("/pdf", response_model=OCRResponse)
async def extract_text_from_pdf(
    file: UploadFile = File(...),
    force_ocr: bool = Query(
        default=False,
        description="Force OCR even if PDF contains text"
    )
) -> OCRResponse:
    """
    Extract text from an uploaded PDF using OCRmyPDF/Tesseract.

    Set force_ocr=true to process scanned documents.
    """
    if file.content_type not in ALLOWED_PDF_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. "
                   f"Allowed types: {', '.join(ALLOWED_PDF_TYPES)}"
        )

    start_time = time.time()

    try:
        pdf_bytes = await file.read()

        if force_ocr:
            pages = PDFOCRService.extract_text(pdf_bytes)
        else:
            pages = PDFOCRService.extract_text_from_native_pdf(pdf_bytes)
            has_text = any(page.text.strip() for page in pages)
            if not has_text:
                pages = PDFOCRService.extract_text(pdf_bytes)

        full_text = "\n\n".join(page.text for page in pages if page.text)
        processing_time = time.time() - start_time

        return OCRResponse(
            success=True,
            filename=file.filename or "unknown",
            file_type="pdf",
            text=full_text,
            pages=pages,
            processing_time_seconds=round(processing_time, 3)
        )

    except Exception as e:
        processing_time = time.time() - start_time
        return OCRResponse(
            success=False,
            filename=file.filename or "unknown",
            file_type="pdf",
            processing_time_seconds=round(processing_time, 3),
            error=str(e)
        )


@router.post("/extract/image", response_model=DocumentExtractResponse)
async def extract_document_from_image(
    file: UploadFile = File(...)
) -> DocumentExtractResponse:
    """
    Extract structured document fields from an image using Claude Vision (Haiku).

    Required fields: first_name, last_name, document_number, date_of_birth, expiry_date

    Returns extracted fields like name, document number, dates, etc.
    """
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. "
                   f"Allowed types: {', '.join(ALLOWED_IMAGE_TYPES)}"
        )

    start_time = time.time()

    try:
        image_bytes = await file.read()

        # Map content type to Claude's expected media type
        media_type_map = {
            "image/png": "image/png",
            "image/jpeg": "image/jpeg",
            "image/jpg": "image/jpeg",
            "image/webp": "image/webp",
            "image/gif": "image/gif",
            "image/tiff": "image/png",
            "image/bmp": "image/png",
        }
        media_type = media_type_map.get(file.content_type, "image/png")

        # For TIFF/BMP, convert to PNG
        if file.content_type in ["image/tiff", "image/bmp"]:
            img = Image.open(BytesIO(image_bytes))
            if img.mode != "RGB":
                img = img.convert("RGB")
            output = BytesIO()
            img.save(output, format="PNG")
            image_bytes = output.getvalue()

        extracted_fields, is_valid, missing_fields = DocumentExtractorService.extract_from_image(
            image_bytes,
            media_type=media_type
        )

        processing_time = time.time() - start_time

        return DocumentExtractResponse(
            success=is_valid,
            first_name=extracted_fields.get("first_name"),
            last_name=extracted_fields.get("last_name"),
            full_name=extracted_fields.get("full_name"),
            document_number=extracted_fields.get("document_number"),
            date_of_birth=extracted_fields.get("date_of_birth"),
            issue_date=extracted_fields.get("issue_date"),
            expiry_date=extracted_fields.get("expiry_date"),
            gender=extracted_fields.get("gender"),
            address=extracted_fields.get("address"),
            missing_fields=missing_fields if not is_valid else None,
            processing_time_seconds=round(processing_time, 3),
            error=f"Could not extract required fields: {', '.join(missing_fields)}" if not is_valid else None
        )

    except Exception as e:
        processing_time = time.time() - start_time
        return DocumentExtractResponse(
            success=False,
            processing_time_seconds=round(processing_time, 3),
            error=str(e)
        )
