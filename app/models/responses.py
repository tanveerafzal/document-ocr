from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class BoundingBox(BaseModel):
    x_min: float
    y_min: float
    x_max: float
    y_max: float


class TextBlock(BaseModel):
    text: str
    confidence: float
    bounding_box: Optional[BoundingBox] = None


class PageResult(BaseModel):
    page_number: int
    text: str
    confidence: Optional[float] = None
    blocks: Optional[list[TextBlock]] = None


class OCRResponse(BaseModel):
    success: bool
    filename: str
    file_type: str
    text: Optional[str] = None
    pages: Optional[list[PageResult]] = None
    blocks: Optional[list[TextBlock]] = None
    processing_time_seconds: float
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    build: str
    easyocr_available: bool
    tesseract_available: bool


class DocumentExtractResponse(BaseModel):
    success: bool
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    document_number: Optional[str] = None
    date_of_birth: Optional[str] = None
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    missing_fields: Optional[List[str]] = None
    processing_time_seconds: Optional[float] = None
    error: Optional[str] = None


class ValidationStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


class ValidatorResult(BaseModel):
    """Individual validation check result."""
    validator_name: str
    status: ValidationStatus
    message: str
    details: Optional[Dict[str, Any]] = None
    execution_time_ms: float


class ValidationSummary(BaseModel):
    """Overall validation summary."""
    overall_status: ValidationStatus
    validation_score: float = Field(ge=0.0, le=1.0, description="Score from 0-1")
    total_checks: int
    passed_checks: int
    failed_checks: int
    warning_checks: int
    skipped_checks: int


class DocumentValidationResponse(BaseModel):
    """Extended response with extraction and validation results."""
    success: bool
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    document_number: Optional[str] = None
    date_of_birth: Optional[str] = None
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    missing_fields: Optional[List[str]] = None
    validation_summary: Optional[ValidationSummary] = None
    validation_results: Optional[List[ValidatorResult]] = None
    processing_time_seconds: Optional[float] = None
    error: Optional[str] = None
