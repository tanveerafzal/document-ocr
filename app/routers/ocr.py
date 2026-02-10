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
    FakeDocumentResult,
    DocumentIntegrityResult,
    IntegrityTestResponse,
    ClaudeAnalysisResult,
    ClaudeAnalysisSummary,
    ClaudeAnalysisIssue,
    ClaudeSpecimenDocumentAnalysis,
    ClaudePhotoTamperingAnalysis,
    ClaudeScreenCaptureAnalysis,
    ClaudeOverallAssessment,
    ValidationStatus,
)
from app.services.image_ocr import ImageOCRService
from app.services.pdf_ocr import PDFOCRService
from app.services.document_extractor import DocumentExtractorService
from app.services.validation_service import ValidationService
from app.services.fake_document_detector import FakeDocumentDetector
from app.services.claude_integrity_analyzer import ClaudeIntegrityAnalyzer
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
    ),
    device_type: Optional[str] = Query(
        default=None,
        alias="deviceType",
        description="Device type ('mobile' or 'desktop') for model selection. Mobile uses cheaper model, desktop uses expensive model for better accuracy."
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
        logger.info(f"[{request_id}]   Device type: {device_type or 'not specified'}")

        extracted_fields, is_valid, missing_fields = DocumentExtractorService.extract_from_image(
            image_bytes,
            media_type=media_type,
            device_type=device_type
        )

        # Run fake document detection
        fake_detection_result = FakeDocumentDetector.detect(extracted_fields)
        fake_detection = FakeDocumentResult(
            is_fake=fake_detection_result["is_fake"],
            confidence=fake_detection_result["confidence"],
            reasons=fake_detection_result["reasons"],
            checks_performed=fake_detection_result["checks_performed"]
        )

        if fake_detection.is_fake:
            logger.warning(f"[{request_id}]   FAKE DOCUMENT DETECTED: {fake_detection.reasons}")

        # Calculate overall document integrity
        # Note: For photo tampering and print attack detection, use the /ocr/test/integrity
        # endpoint with Claude Vision analysis which is more accurate
        integrity_issues = []
        if fake_detection.is_fake:
            integrity_issues.append("fake_document")

        # Integrity score: 1.0 means fully valid, lower scores indicate issues
        integrity_score = 1.0
        integrity_score -= fake_detection.confidence
        integrity_score = max(0.0, integrity_score)

        document_integrity = DocumentIntegrityResult(
            is_valid=len(integrity_issues) == 0,
            fake_detection=fake_detection,
            integrity_score=round(integrity_score, 2)
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
        # Document must pass extraction, integrity checks (not fake, not printed, not tampered)
        integrity_passed = document_integrity.is_valid

        if validate:
            # With validation: success requires extraction, validation to pass, and integrity checks
            overall_success = is_valid and validation_summary.overall_status != ValidationStatus.FAILED and integrity_passed

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

            # Build error message
            error_msg = None
            if not is_valid:
                error_msg = f"Could not extract required fields: {', '.join(missing_fields)}"
            elif not integrity_passed:
                error_msg = f"Document integrity check failed: {', '.join(integrity_issues)}"

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
                fake_detection=fake_detection,
                document_integrity=document_integrity,
                validation_summary=validation_summary,
                validation_results=validation_results,
                processing_time_seconds=round(processing_time, 3),
                error=error_msg
            )
        else:
            # Without validation: success requires extraction and integrity checks
            overall_success = is_valid and integrity_passed

            # Build error message
            error_msg = None
            if not is_valid:
                error_msg = f"Could not extract required fields: {', '.join(missing_fields)}"
            elif not integrity_passed:
                error_msg = f"Document integrity check failed: {', '.join(integrity_issues)}"

            response = DocumentExtractResponse(
                success=overall_success,
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
                fake_detection=fake_detection,
                document_integrity=document_integrity,
                processing_time_seconds=round(processing_time, 3),
                error=error_msg
            )

        # Log response
        logger.info(f"[{request_id}] RESPONSE:")
        logger.info(f"[{request_id}]   Success: {response.success}")
        logger.info(f"[{request_id}]   Name: {response.first_name} {response.last_name}")
        logger.info(f"[{request_id}]   Doc#: {response.document_number}")
        logger.info(f"[{request_id}]   DOB: {response.date_of_birth}")
        logger.info(f"[{request_id}]   Fake Detection: is_fake={fake_detection.is_fake}, confidence={fake_detection.confidence}")
        logger.info(f"[{request_id}]   Document Integrity: is_valid={document_integrity.is_valid}, score={document_integrity.integrity_score}")
        logger.info(f"[{request_id}]   Processing time: {response.processing_time_seconds}s")
        if not is_valid:
            logger.info(f"[{request_id}]   Missing fields: {missing_fields}")
        if not integrity_passed:
            logger.info(f"[{request_id}]   Integrity issues: {integrity_issues}")

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


@router.post("/test/integrity", response_model=IntegrityTestResponse)
async def test_document_integrity(
    request: Request,
    file: UploadFile = File(...)
) -> IntegrityTestResponse:
    """
    Test endpoint for document integrity detection using Claude Vision AI.

    This endpoint analyzes document images for signs of fraud, tampering, or forgery
    without performing OCR or field extraction. Use this for testing document authenticity.

    **Claude Vision Analysis detects:**
    - **Specimen/Sample documents**: Educational examples with visual markers, placeholder names
    - **Photo tampering**: Edge artifacts, blending issues, lighting/color mismatches
    - **Screen captures**: Pixel patterns, screen glare, refresh lines

    **Returns:**
    - Risk level (low/medium/high/critical)
    - Recommended action (accept/review/reject)
    - Detailed findings for each check

    Supported formats: PNG, JPG, JPEG, TIFF, BMP, WEBP, PDF
    """
    request_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
    client_ip = request.client.host if request.client else "unknown"

    logger.info(f"[{request_id}] INTEGRITY TEST REQUEST: /ocr/test/integrity")
    logger.info(f"[{request_id}]   Client IP: {client_ip}")
    logger.info(f"[{request_id}]   Filename: {file.filename}")

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
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat)
            image_bytes = pix.tobytes("png")
            pdf_doc.close()
            detected_format = "PNG (from PDF)"
        else:
            image_bytes = file_bytes
            img = Image.open(BytesIO(image_bytes))
            detected_format = img.format.upper() if img.format else "Unknown"

            # Convert TIFF/BMP to PNG for processing
            if detected_format in ["TIFF", "BMP"]:
                if img.mode != "RGB":
                    img = img.convert("RGB")
                output = BytesIO()
                img.save(output, format="PNG")
                image_bytes = output.getvalue()

        # Get image info
        img = Image.open(BytesIO(image_bytes))
        image_info = {
            "width": img.size[0],
            "height": img.size[1],
            "format": detected_format,
            "mode": img.mode,
            "file_size_kb": round(file_size_kb, 2)
        }

        logger.info(f"[{request_id}]   Image: {img.size[0]}x{img.size[1]} {detected_format}")

        # Run Claude Vision analysis
        logger.info(f"[{request_id}]   Running Claude Vision integrity analysis...")

        # Determine media type for Claude
        img_format = detected_format.upper()
        if "PNG" in img_format:
            media_type = "image/png"
        elif "JPEG" in img_format or "JPG" in img_format:
            media_type = "image/jpeg"
        elif "WEBP" in img_format:
            media_type = "image/webp"
        else:
            media_type = "image/png"

        claude_result = ClaudeIntegrityAnalyzer.analyze(image_bytes, media_type)

        # Build Claude analysis response model
        claude_analysis = None
        claude_summary = None

        if claude_result.get("analysis_completed"):
            # Build specimen document analysis
            specimen_data = claude_result.get("specimen_document", {})
            claude_specimen = ClaudeSpecimenDocumentAnalysis(
                is_specimen=specimen_data.get("is_specimen", False),
                confidence=specimen_data.get("confidence", 0),
                findings=specimen_data.get("findings", []),
                details=specimen_data.get("details")
            )

            # Build photo tampering analysis
            photo_data = claude_result.get("photo_tampering", {})
            claude_photo = ClaudePhotoTamperingAnalysis(
                is_suspicious=photo_data.get("is_suspicious", False),
                confidence=photo_data.get("confidence", 0),
                findings=photo_data.get("findings", []),
                details=photo_data.get("details")
            )

            # Build screen capture analysis
            screen_data = claude_result.get("screen_capture", {})
            claude_screen = ClaudeScreenCaptureAnalysis(
                is_suspicious=screen_data.get("is_suspicious", False),
                confidence=screen_data.get("confidence", 0),
                findings=screen_data.get("findings", []),
                details=screen_data.get("details")
            )

            # Build overall assessment
            overall_data = claude_result.get("overall_assessment", {})
            claude_overall = ClaudeOverallAssessment(
                is_likely_fraudulent=overall_data.get("is_likely_fraudulent", False),
                fraud_confidence=overall_data.get("fraud_confidence", 0),
                risk_level=overall_data.get("risk_level", "unknown"),
                summary=overall_data.get("summary", ""),
                recommended_action=overall_data.get("recommended_action", "review")
            )

            claude_analysis = ClaudeAnalysisResult(
                analysis_completed=True,
                specimen_document=claude_specimen,
                photo_tampering=claude_photo,
                screen_capture=claude_screen,
                overall_assessment=claude_overall,
                error=None
            )

            # Build summary
            summary_result = ClaudeIntegrityAnalyzer.get_summary(claude_result)
            issues_detected = [
                ClaudeAnalysisIssue(
                    type=issue["type"],
                    confidence=issue["confidence"],
                    findings=issue["findings"]
                )
                for issue in summary_result.get("issues_detected", [])
            ]

            claude_summary = ClaudeAnalysisSummary(
                is_fraudulent=summary_result.get("is_fraudulent", False),
                confidence=summary_result.get("confidence", 0),
                risk_level=summary_result.get("risk_level", "unknown"),
                issues_detected=issues_detected,
                recommendation=summary_result.get("recommendation", "review"),
                summary=summary_result.get("summary"),
                error=summary_result.get("error")
            )

            logger.info(f"[{request_id}]   Claude Analysis: is_fraudulent={claude_summary.is_fraudulent}, risk_level={claude_summary.risk_level}")
            if claude_summary.is_fraudulent:
                logger.warning(f"[{request_id}]   CLAUDE DETECTED FRAUD: {claude_summary.summary}")
        else:
            claude_analysis = ClaudeAnalysisResult(
                analysis_completed=False,
                error=claude_result.get("error", "Analysis failed")
            )
            logger.error(f"[{request_id}]   Claude analysis failed: {claude_result.get('error')}")

        # Calculate overall integrity based on Claude's assessment
        integrity_issues = []
        if claude_summary and claude_summary.is_fraudulent:
            integrity_issues.append("fraud_detected")

        integrity_score = 1.0
        if claude_summary:
            integrity_score -= claude_summary.confidence
        integrity_score = max(0.0, integrity_score)

        document_integrity = DocumentIntegrityResult(
            is_valid=len(integrity_issues) == 0,
            fake_detection=None,
            integrity_score=round(integrity_score, 2)
        )

        processing_time = time.time() - start_time

        logger.info(f"[{request_id}]   Integrity: is_valid={document_integrity.is_valid}, score={document_integrity.integrity_score}")
        logger.info(f"[{request_id}]   Processing time: {round(processing_time, 3)}s")

        return IntegrityTestResponse(
            success=True,
            claude_analysis=claude_analysis,
            claude_summary=claude_summary,
            document_integrity=document_integrity,
            image_info=image_info,
            processing_time_seconds=round(processing_time, 3),
            error=None
        )

    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"[{request_id}] ERROR: {str(e)}")

        return IntegrityTestResponse(
            success=False,
            processing_time_seconds=round(processing_time, 3),
            error=str(e)
        )
