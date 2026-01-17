from enum import Enum
from typing import Optional, List
from pydantic import BaseModel


class DocumentType(str, Enum):
    """Supported document types for validation."""
    # Canadian Provinces
    ONTARIO_DRIVERS_LICENSE = "ontario_drivers_license"
    ONTARIO_HEALTH_CARD = "ontario_health_card"
    BC_DRIVERS_LICENSE = "bc_drivers_license"
    ALBERTA_DRIVERS_LICENSE = "alberta_drivers_license"
    QUEBEC_DRIVERS_LICENSE = "quebec_drivers_license"
    MANITOBA_DRIVERS_LICENSE = "manitoba_drivers_license"
    SASKATCHEWAN_DRIVERS_LICENSE = "saskatchewan_drivers_license"
    NOVA_SCOTIA_DRIVERS_LICENSE = "nova_scotia_drivers_license"
    NEW_BRUNSWICK_DRIVERS_LICENSE = "new_brunswick_drivers_license"
    PEI_DRIVERS_LICENSE = "pei_drivers_license"
    NEWFOUNDLAND_DRIVERS_LICENSE = "newfoundland_drivers_license"
    # Canadian Territories
    NWT_DRIVERS_LICENSE = "nwt_drivers_license"
    NUNAVUT_DRIVERS_LICENSE = "nunavut_drivers_license"
    YUKON_DRIVERS_LICENSE = "yukon_drivers_license"
    # Other Documents
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
    DocumentType.ONTARIO_HEALTH_CARD: {
        "name": "Ontario Health Card",
        "country": "Canada",
        "state_province": "Ontario",
        "license_format": r"^\d{10}[A-Z]{2}$",
        "keywords": ["ontario", "health card", "ohip", "ministry of health", "carte santé"],
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
    DocumentType.MANITOBA_DRIVERS_LICENSE: {
        "name": "Manitoba Driver's Licence",
        "country": "Canada",
        "state_province": "Manitoba",
        "license_format": r"^[A-Z]{2}-?[A-Z]{2}-?\d{3}-?\d{3}$",
        "keywords": ["manitoba", "mb", "driver's licence", "driver licence", "class 5"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.SASKATCHEWAN_DRIVERS_LICENSE: {
        "name": "Saskatchewan Driver's Licence",
        "country": "Canada",
        "state_province": "Saskatchewan",
        "license_format": r"^\d{8}$",
        "keywords": ["saskatchewan", "sk", "sgi", "driver's licence", "driver licence", "class 5", "class 7"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.NOVA_SCOTIA_DRIVERS_LICENSE: {
        "name": "Nova Scotia Driver's Licence",
        "country": "Canada",
        "state_province": "Nova Scotia",
        "license_format": r"^[A-Z]{5}\d{9}$",
        "keywords": ["nova scotia", "ns", "driver's licence", "driver licence", "class 5", "class 7"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.NEW_BRUNSWICK_DRIVERS_LICENSE: {
        "name": "New Brunswick Driver's Licence",
        "country": "Canada",
        "state_province": "New Brunswick",
        "license_format": r"^\d{7}$",
        "keywords": ["new brunswick", "nouveau-brunswick", "nb", "driver's licence", "permis de conduire", "class 5", "class 7"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.PEI_DRIVERS_LICENSE: {
        "name": "PEI Driver's Licence",
        "country": "Canada",
        "state_province": "Prince Edward Island",
        "license_format": r"^\d{1,6}$",
        "keywords": ["prince edward island", "pei", "pe", "driver's licence", "driver licence", "class 5", "class 7"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.NEWFOUNDLAND_DRIVERS_LICENSE: {
        "name": "Newfoundland Driver's Licence",
        "country": "Canada",
        "state_province": "Newfoundland and Labrador",
        "license_format": r"^[A-Z]\d{9}$",
        "keywords": ["newfoundland", "labrador", "nl", "driver's licence", "driver licence", "class 5", "class 7"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.NWT_DRIVERS_LICENSE: {
        "name": "NWT Driver's Licence",
        "country": "Canada",
        "state_province": "Northwest Territories",
        "license_format": r"^\d{6}$",
        "keywords": ["northwest territories", "nwt", "nt", "driver's licence", "driver licence", "class 5", "class 7"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.NUNAVUT_DRIVERS_LICENSE: {
        "name": "Nunavut Driver's Licence",
        "country": "Canada",
        "state_province": "Nunavut",
        "license_format": r"^\d{6}$",
        "keywords": ["nunavut", "nu", "driver's licence", "driver licence", "class 5", "class 7"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.YUKON_DRIVERS_LICENSE: {
        "name": "Yukon Driver's Licence",
        "country": "Canada",
        "state_province": "Yukon",
        "license_format": r"^\d{6}$",
        "keywords": ["yukon", "yt", "yk", "driver's licence", "driver licence", "class 5", "class 7"],
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
