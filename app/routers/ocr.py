import time
import logging
from typing import Optional, Union
from io import BytesIO
from datetime import datetime

from fastapi import APIRouter, File, UploadFile, HTTPException, Query, Depends, Request
from fastapi.responses import Response
from PIL import Image
import fitz
import zipfile

from app.models.responses import (
    OCRResponse,
    PageResult,
    DocumentExtractResponse,
    DocumentValidationResponse,
    DocumentTypeResult,
    ValidationStatus,
)
from app.services.image_ocr import ImageOCRService
from app.services.pdf_ocr import PDFOCRService
from app.services.document_extractor import DocumentExtractorService
from app.services.validation_service import ValidationService
from app.auth import verify_api_key

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    logger.info(f"Received image OCR request: {file.filename}, Content-Type: {file.content_type}")
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


ALLOWED_EXTRACT_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_PDF_TYPES


@router.post("/extract/image", response_model=Union[DocumentExtractResponse, DocumentValidationResponse])
async def extract_document_from_image(
    request: Request,
    file: UploadFile = File(...),
    validate: bool = Query(
        default=False,
        description="Run validation checks after extraction (parallel execution)"
    ),
    minimum_age: int = Query(
        default=18,
        ge=1,
        le=120,
        description="Minimum age requirement for age validation"
    )
) -> Union[DocumentExtractResponse, DocumentValidationResponse]:
    """
    Extract structured document fields from an image or PDF using Claude Vision (Haiku).

    Supported formats: PNG, JPG, JPEG, TIFF, BMP, WEBP, PDF

    Required fields: first_name, last_name, document_number, date_of_birth, expiry_date

    Optional: Set validate=true to run parallel validation checks (data consistency,
    document expiry, age verification, document format validation).

    Returns extracted fields like name, document number, dates, etc.
    """
    request_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
    client_ip = request.client.host if request.client else "unknown"

    # Log request
    logger.info(f"[{request_id}] REQUEST Received: /ocr/extract/image")
    logger.info(f"[{request_id}]   Client IP: {client_ip}")
    logger.info(f"[{request_id}]   Filename: {file.filename}")
    logger.info(f"[{request_id}]   Content-Type: {file.content_type}")
    logger.info(f"[{request_id}]   Validate: {validate}, Min Age: {minimum_age}")

    if file.content_type not in ALLOWED_EXTRACT_TYPES:
        logger.warning(f"[{request_id}]   Rejected: Unsupported file type")
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. "
                   f"Allowed types: {', '.join(ALLOWED_EXTRACT_TYPES)}"
        )

    start_time = time.time()

    try:
        file_bytes = await file.read()
        file_size_kb = len(file_bytes) / 1024
        logger.info(f"[{request_id}]   File size: {file_size_kb:.2f} KB")

        # Handle PDF files - convert first page to image
        if file.content_type == "application/pdf":
            logger.info(f"[{request_id}]   Processing PDF - converting first page to image")
            pdf_doc = fitz.open(stream=file_bytes, filetype="pdf")
            if len(pdf_doc) == 0:
                raise ValueError("PDF has no pages")
            page = pdf_doc[0]
            # Render at 2x resolution for better quality
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat)
            image_bytes = pix.tobytes("png")
            pdf_doc.close()
            media_type = "image/png"
            detected_format = "PNG (from PDF)"
        else:
            image_bytes = file_bytes
            # Detect actual image format from bytes (don't trust client Content-Type)
            img = Image.open(BytesIO(image_bytes))
            detected_format = img.format.upper() if img.format else None

            # Map detected format to Claude's expected media type
            format_to_media_type = {
                "PNG": "image/png",
                "JPEG": "image/jpeg",
                "JPG": "image/jpeg",
                "WEBP": "image/webp",
                "GIF": "image/gif",
                "TIFF": "image/png",  # Will be converted
                "BMP": "image/png",   # Will be converted
            }
            media_type = format_to_media_type.get(detected_format, "image/png")

            # For TIFF/BMP, convert to PNG (img already opened above)
            if detected_format in ["TIFF", "BMP"]:
                if img.mode != "RGB":
                    img = img.convert("RGB")
                output = BytesIO()
                img.save(output, format="PNG")
                image_bytes = output.getvalue()

        logger.info(f"[{request_id}]   Detected format: {detected_format}")

        extracted_fields, is_valid, missing_fields = DocumentExtractorService.extract_from_image(
            image_bytes,
            media_type=media_type
        )

        # Run validation if requested
        validation_summary = None
        validation_results = None
        document_type_info = None
        if validate:
            validation_service = ValidationService(minimum_age=minimum_age)
            validation_summary, validation_results, document_type_info = await validation_service.validate_document(
                extracted_fields,
                request_id=request_id
            )

        processing_time = time.time() - start_time

        # Determine overall success
        if validate:
            # With validation: success requires both extraction and validation to pass
            overall_success = is_valid and validation_summary.overall_status != ValidationStatus.FAILED

            # Build document type result
            doc_type_result = None
            if document_type_info:
                doc_type_result = DocumentTypeResult(
                    document_type=document_type_info.document_type,
                    document_name=document_type_info.document_name,
                    confidence=document_type_info.confidence,
                    country=document_type_info.country,
                    state_province=document_type_info.state_province
                )

            response = DocumentValidationResponse(
                success=overall_success,
                document_type=doc_type_result,
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
                validation_summary=validation_summary,
                validation_results=validation_results,
                processing_time_seconds=round(processing_time, 3),
                error=f"Could not extract required fields: {', '.join(missing_fields)}" if not is_valid else None
            )
        else:
            response = DocumentExtractResponse(
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

        # Log response
        logger.info(f"[{request_id}] RESPONSE:")
        logger.info(f"[{request_id}]   Success: {response.success}")
        logger.info(f"[{request_id}]   Name: {response.first_name} {response.last_name}")
        logger.info(f"[{request_id}]   Doc#: {response.document_number}")
        logger.info(f"[{request_id}]   DOB: {response.date_of_birth}")
        logger.info(f"[{request_id}]   Processing time: {response.processing_time_seconds}s")
        if not is_valid:
            logger.info(f"[{request_id}]   Missing fields: {missing_fields}")

        return response

    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"[{request_id}] ERROR: {str(e)}")
        logger.error(f"[{request_id}]   Processing time: {round(processing_time, 3)}s")

        return DocumentExtractResponse(
            success=False,
            processing_time_seconds=round(processing_time, 3),
            error=str(e)
        )


@router.post("/pdf-to-image")
async def convert_pdf_to_image(
    file: UploadFile = File(...),
    page: Optional[int] = Query(
        default=None,
        description="Page number to convert (1-indexed). If not specified, returns all pages as ZIP."
    ),
    scale: float = Query(
        default=2.0,
        ge=0.5,
        le=4.0,
        description="Scale factor for image resolution (0.5-4.0). Default 2.0 for good quality."
    ),
    format: str = Query(
        default="png",
        pattern="^(png|jpeg)$",
        description="Output image format: 'png' or 'jpeg'"
    )
):
    """
    Convert PDF pages to images.

    - **Single page**: Specify `page` parameter to get one image directly
    - **All pages**: Omit `page` parameter to get a ZIP file with all pages

    Returns PNG or JPEG image(s) based on format parameter.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail=f"Expected PDF file, got: {file.content_type}"
        )

    try:
        pdf_bytes = await file.read()
        pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        total_pages = len(pdf_doc)

        if total_pages == 0:
            pdf_doc.close()
            raise HTTPException(status_code=400, detail="PDF has no pages")

        mat = fitz.Matrix(scale, scale)
        output_format = format.upper()
        content_type = f"image/{format}"

        # Single page requested
        if page is not None:
            if page < 1 or page > total_pages:
                pdf_doc.close()
                raise HTTPException(
                    status_code=400,
                    detail=f"Page {page} out of range. PDF has {total_pages} page(s)."
                )

            pdf_page = pdf_doc[page - 1]
            pix = pdf_page.get_pixmap(matrix=mat)

            if output_format == "JPEG":
                image_bytes = pix.tobytes("jpeg")
            else:
                image_bytes = pix.tobytes("png")

            pdf_doc.close()

            filename = f"{file.filename or 'document'}_page_{page}.{format}"
            return Response(
                content=image_bytes,
                media_type=content_type,
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )

        # All pages - return as ZIP
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for i in range(total_pages):
                pdf_page = pdf_doc[i]
                pix = pdf_page.get_pixmap(matrix=mat)

                if output_format == "JPEG":
                    image_bytes = pix.tobytes("jpeg")
                else:
                    image_bytes = pix.tobytes("png")

                zip_file.writestr(f"page_{i + 1}.{format}", image_bytes)

        pdf_doc.close()
        zip_buffer.seek(0)

        zip_filename = f"{file.filename or 'document'}_images.zip"
        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={zip_filename}"}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF conversion failed: {str(e)}")
