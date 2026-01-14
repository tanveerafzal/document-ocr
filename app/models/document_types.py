from enum import Enum
from typing import Optional, List
from pydantic import BaseModel


class DocumentType(str, Enum):
    """Supported document types for validation."""
    ONTARIO_DRIVERS_LICENSE = "ontario_drivers_license"
    BC_DRIVERS_LICENSE = "bc_drivers_license"
    ALBERTA_DRIVERS_LICENSE = "alberta_drivers_license"
    QUEBEC_DRIVERS_LICENSE = "quebec_drivers_license"
    CANADIAN_PASSPORT = "canadian_passport"
    US_DRIVERS_LICENSE = "us_drivers_license"
    US_PASSPORT = "us_passport"
    GENERIC_ID = "generic_id"
    UNKNOWN = "unknown"


class DocumentTypeInfo(BaseModel):
    """Information about detected document type."""
    document_type: DocumentType
    confidence: float  # 0-1 confidence score
    country: Optional[str] = None
    state_province: Optional[str] = None
    document_name: str
    detected_features: List[str] = []


# Document type detection patterns and rules
DOCUMENT_PATTERNS = {
    DocumentType.ONTARIO_DRIVERS_LICENSE: {
        "name": "Ontario Driver's License",
        "country": "Canada",
        "state_province": "Ontario",
        "license_format": r"^[A-Z]\d{4}-\d{5}-\d{5}$",
        "keywords": ["ontario", "driver's licence", "driver licence", "class g", "class g1", "class g2"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.BC_DRIVERS_LICENSE: {
        "name": "BC Driver's Licence",
        "country": "Canada",
        "state_province": "British Columbia",
        "license_format": r"^(DL:?)?\d{6,7}$",
        "keywords": ["british columbia", "bc", "driver's licence", "driver licence", "class 5", "class 7"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.ALBERTA_DRIVERS_LICENSE: {
        "name": "Alberta Driver's Licence",
        "country": "Canada",
        "state_province": "Alberta",
        "license_format": r"^\d{6}-?\d{3}$",
        "keywords": ["alberta", "ab", "driver's licence", "driver licence", "class 5", "class 7", "gdl"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.QUEBEC_DRIVERS_LICENSE: {
        "name": "Quebec Driver's Licence",
        "country": "Canada",
        "state_province": "Quebec",
        "license_format": r"^[A-Z]\d{4}-?\d{6}-?\d{2}$",
        "keywords": ["quebec", "qc", "permis de conduire", "driver's licence", "classe 5", "probatoire"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.CANADIAN_PASSPORT: {
        "name": "Canadian Passport",
        "country": "Canada",
        "state_province": None,
        "license_format": r"^[A-Z]{2}\d{6}$",
        "keywords": ["canada", "passport", "passeport"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.US_DRIVERS_LICENSE: {
        "name": "US Driver's License",
        "country": "United States",
        "state_province": None,
        "license_format": r"^[A-Z0-9]{6,15}$",
        "keywords": ["driver license", "driver's license", "dmv"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
}
