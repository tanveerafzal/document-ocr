from pydantic import BaseModel
from typing import Optional, List


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
