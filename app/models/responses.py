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


class FakeDocumentResult(BaseModel):
    """Fake/specimen document detection result."""
    is_fake: bool
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence that document is fake (0-1)")
    reasons: List[str] = Field(default_factory=list, description="Reasons why document was flagged")
    checks_performed: List[str] = Field(default_factory=list, description="List of checks performed")


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
    fake_detection: Optional[FakeDocumentResult] = None
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


class DocumentTypeResult(BaseModel):
    """Detected document type information."""
    document_type: str
    document_name: str
    confidence: float
    country: Optional[str] = None
    state_province: Optional[str] = None


class DocumentValidationResponse(BaseModel):
    """Extended response with extraction and validation results."""
    success: bool
    document_type: Optional[DocumentTypeResult] = None
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
    fake_detection: Optional[FakeDocumentResult] = None
    validation_summary: Optional[ValidationSummary] = None
    validation_results: Optional[List[ValidatorResult]] = None
    processing_time_seconds: Optional[float] = None
    error: Optional[str] = None
