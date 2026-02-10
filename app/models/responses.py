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


class DocumentIntegrityResult(BaseModel):
    """Combined document integrity check results."""
    is_valid: bool = Field(description="Overall document integrity status (True if passes all checks)")
    fake_detection: Optional[FakeDocumentResult] = Field(default=None, description="Specimen/fake document detection")
    integrity_score: float = Field(ge=0.0, le=1.0, description="Overall integrity score (0-1, higher is better)")


class ClaudeAnalysisIssue(BaseModel):
    """Individual issue detected by Claude analysis."""
    type: str = Field(description="Type of issue: specimen_document, photo_tampering, or screen_capture")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence level for this issue")
    findings: List[str] = Field(default_factory=list, description="Specific findings for this issue")


class ClaudeAnalysisSummary(BaseModel):
    """Summary of Claude's document integrity analysis."""
    is_fraudulent: bool = Field(description="Whether Claude believes the document is fraudulent")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in fraud assessment")
    risk_level: str = Field(description="Risk level: low, medium, high, critical, or unknown")
    issues_detected: List[ClaudeAnalysisIssue] = Field(default_factory=list, description="List of issues detected")
    recommendation: str = Field(description="Recommended action: accept, review, or reject")
    summary: Optional[str] = Field(default=None, description="Brief summary of findings")
    error: Optional[str] = Field(default=None, description="Error message if analysis failed")


class ClaudeAnalysisDetail(BaseModel):
    """Detailed detection result from Claude."""
    detected: bool
    description: Optional[str] = None


class ClaudeSpecimenDocumentAnalysis(BaseModel):
    """Claude's specimen/sample document detection analysis."""
    is_specimen: bool
    confidence: float = Field(ge=0.0, le=1.0)
    findings: List[str] = Field(default_factory=list)
    details: Optional[Dict[str, ClaudeAnalysisDetail]] = None


class ClaudePhotoTamperingAnalysis(BaseModel):
    """Claude's photo tampering analysis."""
    is_suspicious: bool
    confidence: float = Field(ge=0.0, le=1.0)
    findings: List[str] = Field(default_factory=list)
    details: Optional[Dict[str, ClaudeAnalysisDetail]] = None


class ClaudeScreenCaptureAnalysis(BaseModel):
    """Claude's screen capture detection analysis."""
    is_suspicious: bool
    confidence: float = Field(ge=0.0, le=1.0)
    findings: List[str] = Field(default_factory=list)
    details: Optional[Dict[str, ClaudeAnalysisDetail]] = None


class ClaudeOverallAssessment(BaseModel):
    """Claude's overall fraud assessment."""
    is_likely_fraudulent: bool
    fraud_confidence: float = Field(ge=0.0, le=1.0)
    risk_level: str
    summary: str
    recommended_action: str


class ClaudeAnalysisResult(BaseModel):
    """Full Claude vision analysis result."""
    analysis_completed: bool = Field(description="Whether analysis was completed successfully")
    specimen_document: Optional[ClaudeSpecimenDocumentAnalysis] = None
    photo_tampering: Optional[ClaudePhotoTamperingAnalysis] = None
    screen_capture: Optional[ClaudeScreenCaptureAnalysis] = None
    overall_assessment: Optional[ClaudeOverallAssessment] = None
    error: Optional[str] = Field(default=None, description="Error message if analysis failed")


class IntegrityTestResponse(BaseModel):
    """Response for the integrity test endpoint using Claude Vision."""
    success: bool
    claude_analysis: Optional[ClaudeAnalysisResult] = Field(default=None, description="Claude vision-based integrity analysis")
    claude_summary: Optional[ClaudeAnalysisSummary] = Field(default=None, description="Summary of Claude analysis")
    document_integrity: Optional[DocumentIntegrityResult] = None
    image_info: Optional[Dict[str, Any]] = Field(default=None, description="Basic image information")
    processing_time_seconds: Optional[float] = None
    error: Optional[str] = None


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
    document_integrity: Optional[DocumentIntegrityResult] = None
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
    document_integrity: Optional[DocumentIntegrityResult] = None
    validation_summary: Optional[ValidationSummary] = None
    validation_results: Optional[List[ValidatorResult]] = None
    processing_time_seconds: Optional[float] = None
    error: Optional[str] = None
