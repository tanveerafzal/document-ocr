"""
Fake Document Detector Service

Detects potentially fake or specimen documents by checking for:
1. Specimen/sample indicators (SPECIMEN, SAMPLE, VOID, etc.)
2. Common fake/placeholder names (John Doe, Jane Doe, etc.)
3. Placeholder data patterns (sequential numbers, all zeros, etc.)
4. Common test dates
5. Known specimen document numbers
"""

import re
import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class FakeDocumentDetector:
    """Detects fake, specimen, or test documents."""

    # Specimen/sample indicators that appear on fake documents
    SPECIMEN_KEYWORDS = [
        "specimen", "sample", "void", "not valid", "invalid",
        "for display only", "display purposes", "example",
        "test document", "test card", "demo", "demonstration",
        "facsimile", "replica", "copy", "duplicate",
        "training", "practice", "mock", "fake",
        "not for identification", "no value", "cancelled",
        "spécimen", "échantillon", "annulé",  # French
        "muestra", "anulado",  # Spanish
    ]

    # Common fake/placeholder names used in specimen documents
    FAKE_NAMES = [
        # English common fake names
        ("john", "doe"), ("jane", "doe"), ("john", "smith"), ("jane", "smith"),
        ("test", "user"), ("sample", "person"), ("example", "name"),
        ("first", "last"), ("firstname", "lastname"),
        ("any", "body"), ("some", "one"), ("no", "name"),
        ("john", "q"), ("john", "public"), ("joe", "bloggs"),
        ("richard", "roe"), ("baby", "doe"),
        ("james", "public"), ("jane", "public"),  # Common Canadian specimen names
        ("james", "quintin"), ("quintin", "public"),

        # Ontario Health Card specimen name
        ("anita", "walker"), ("anita", "jean"), ("jean", "walker"),

        # Generic placeholders
        ("your", "name"), ("full", "name"), ("given", "name"),
        ("name", "here"), ("insert", "name"),

        # French
        ("jean", "dupont"), ("marie", "dupont"),
        ("pierre", "martin"), ("paul", "martin"),

        # Common specimen names from various countries
        ("jan", "jansen"), ("max", "mustermann"),
        ("ivan", "ivanov"), ("juan", "garcia"),
    ]

    # Single fake name indicators
    FAKE_SINGLE_NAMES = [
        "specimen", "sample", "test", "demo", "void",
        "xxxxx", "nnnnn", "aaaaa", "zzzzz",
        "abcde", "qwerty", "asdfg",
        "public", "person", "citizen", "resident",  # Common specimen names
        "anybody", "someone", "noname", "anonymous",
    ]

    # Placeholder document number patterns
    FAKE_DOC_NUMBER_PATTERNS = [
        r"^0{5,}$",  # All zeros
        r"^1{5,}$",  # All ones
        r"^9{5,}$",  # All nines
        r"^X{3,}$",  # All X's
        r"^[A-Z]0{5,}$",  # Letter followed by zeros
        r"^(12345|123456|1234567|12345678|123456789)$",  # Sequential
        r"^(11111|22222|33333|44444|55555|66666|77777|88888|99999)$",  # Repeated
        r"^(AB123456|CD123456|XY123456)$",  # Common specimen patterns
        r"^(A1234567|B1234567|C1234567)$",  # Letter + sequential
        r"^(AA000000|BB000000|XX000000)$",  # Double letter + zeros
        r"^SAMPLE\d*$",  # SAMPLE followed by optional digits
        r"^TEST\d*$",  # TEST followed by optional digits
        r"^SPEC\d*$",  # SPEC followed by optional digits
    ]

    # Known specimen document numbers from various sources
    KNOWN_SPECIMEN_DOC_NUMBERS = [
        "AB123456", "CD123456", "XY123456",
        "A1234567", "B1234567", "L1234567",
        "123456789", "000000000", "999999999",
        "1234567890",  # Ontario Health Card specimen
        "5584486674",  # Ontario Health Card specimen (Anita Walker)
        "S1234567", "P1234567", "T1234567",
        "SPECIMEN", "SAMPLE", "TEST",
    ]

    # Suspicious dates (commonly used in specimens)
    SUSPICIOUS_DATES = [
        "1900-01-01", "1970-01-01", "2000-01-01", "2020-01-01",
        "1111-11-11", "2222-02-22", "1234-12-34",
        "0001-01-01", "9999-12-31",
    ]

    # Suspicious birth years for specimens (only very old/placeholder years)
    SUSPICIOUS_BIRTH_YEARS = [1900, 1901, 1911]

    # Fake/placeholder address indicators
    FAKE_ADDRESS_PATTERNS = [
        "123 main", "123 fake", "123 test", "123 sample",
        "456 main", "789 main", "100 main",
        "1234 main", "12345 main",
        "123 street", "123 avenue", "123 road",
        "fake street", "test street", "sample street",
        "anywhere", "somewhere", "nowhere", "anytown",
        "springfield",  # Common fictional town
        "123 sesame",  # Sesame Street reference
    ]

    @classmethod
    def detect(cls, extracted_data: Dict[str, Any], raw_text: str = "") -> Dict[str, Any]:
        """
        Detect if a document appears to be fake or a specimen.

        Args:
            extracted_data: Dictionary with extracted document fields
            raw_text: Optional raw text from OCR for additional analysis

        Returns:
            Dictionary with detection results:
            {
                "is_fake": bool,
                "confidence": float (0.0-1.0),
                "reasons": list of strings explaining why it's flagged,
                "checks_performed": list of check names
            }
        """
        reasons = []
        checks_performed = []
        total_score = 0.0

        # Build searchable text from all fields
        full_text = cls._build_full_text(extracted_data, raw_text)
        full_text_lower = full_text.lower()

        # Check 1: Specimen keywords
        checks_performed.append("specimen_keywords")
        specimen_score, specimen_reasons = cls._check_specimen_keywords(full_text_lower)
        total_score += specimen_score
        reasons.extend(specimen_reasons)

        # Check 2: Fake names
        checks_performed.append("fake_names")
        name_score, name_reasons = cls._check_fake_names(extracted_data)
        total_score += name_score
        reasons.extend(name_reasons)

        # Check 3: Fake document numbers
        checks_performed.append("fake_document_numbers")
        doc_num_score, doc_num_reasons = cls._check_fake_document_number(extracted_data)
        total_score += doc_num_score
        reasons.extend(doc_num_reasons)

        # Check 4: Suspicious dates
        checks_performed.append("suspicious_dates")
        date_score, date_reasons = cls._check_suspicious_dates(extracted_data)
        total_score += date_score
        reasons.extend(date_reasons)

        # Check 5: MRZ anomalies (for passports)
        checks_performed.append("mrz_anomalies")
        mrz_score, mrz_reasons = cls._check_mrz_anomalies(extracted_data)
        total_score += mrz_score
        reasons.extend(mrz_reasons)

        # Check 6: Fake addresses
        checks_performed.append("fake_addresses")
        address_score, address_reasons = cls._check_fake_address(extracted_data)
        total_score += address_score
        reasons.extend(address_reasons)

        # Normalize score (max possible ~5.0 from all checks)
        confidence = min(total_score / 2.0, 1.0)  # Scale so 2+ triggers = high confidence
        is_fake = confidence >= 0.4 or total_score >= 0.8

        result = {
            "is_fake": is_fake,
            "confidence": round(confidence, 2),
            "reasons": reasons,
            "checks_performed": checks_performed
        }

        if is_fake:
            logger.warning(f"Fake document detected: {reasons}")

        return result

    @classmethod
    def _build_full_text(cls, extracted_data: Dict[str, Any], raw_text: str = "") -> str:
        """Combine all text fields for searching."""
        parts = [raw_text] if raw_text else []
        for key, value in extracted_data.items():
            if value and isinstance(value, str):
                parts.append(value)
        return " ".join(parts)

    @classmethod
    def _check_specimen_keywords(cls, text_lower: str) -> Tuple[float, List[str]]:
        """Check for specimen/sample keywords."""
        found = []
        for keyword in cls.SPECIMEN_KEYWORDS:
            if keyword in text_lower:
                found.append(keyword)

        if found:
            score = min(len(found) * 0.5, 1.0)
            return score, [f"Specimen keyword found: {', '.join(found)}"]
        return 0.0, []

    @classmethod
    def _check_fake_names(cls, extracted_data: Dict[str, Any]) -> Tuple[float, List[str]]:
        """Check for common fake/placeholder names."""
        first_name = (extracted_data.get("first_name") or "").lower().strip()
        last_name = (extracted_data.get("last_name") or "").lower().strip()
        full_name = (extracted_data.get("full_name") or "").lower().strip()

        reasons = []
        score = 0.0

        # Check first + last name combinations
        for fake_first, fake_last in cls.FAKE_NAMES:
            if first_name == fake_first and last_name == fake_last:
                score += 1.0
                reasons.append(f"Known fake name: {fake_first.title()} {fake_last.title()}")
                break
            # Also check if names contain fake indicators
            if fake_first in first_name and fake_last in last_name:
                score += 0.7
                reasons.append(f"Suspicious name pattern: contains '{fake_first}' and '{fake_last}'")
                break

        # Check single name indicators
        for fake_single in cls.FAKE_SINGLE_NAMES:
            if fake_single in first_name or fake_single in last_name or fake_single in full_name:
                score += 0.8
                reasons.append(f"Fake name indicator: '{fake_single}'")
                break

        # Check for repeated characters in names (e.g., "AAAA BBBB")
        # Only flag if name is 4+ chars AND has 2 or fewer unique chars
        # This avoids false positives on short names like "YU", "LI", "WU"
        first_name_clean = first_name.replace(" ", "")
        if first_name_clean and len(first_name_clean) >= 4 and len(set(first_name_clean)) <= 2:
            score += 0.5
            reasons.append(f"Suspicious first name: '{first_name}' (repeated characters)")

        last_name_clean = last_name.replace(" ", "")
        if last_name_clean and len(last_name_clean) >= 4 and len(set(last_name_clean)) <= 2:
            score += 0.5
            reasons.append(f"Suspicious last name: '{last_name}' (repeated characters)")

        return score, reasons

    @classmethod
    def _check_fake_document_number(cls, extracted_data: Dict[str, Any]) -> Tuple[float, List[str]]:
        """Check for placeholder document numbers."""
        doc_number = (extracted_data.get("document_number") or "").upper().strip()
        doc_number_clean = re.sub(r"[\s\-]", "", doc_number)

        if not doc_number_clean:
            return 0.0, []

        reasons = []
        score = 0.0

        # Check against known specimen numbers
        if doc_number_clean in cls.KNOWN_SPECIMEN_DOC_NUMBERS:
            score += 1.0
            reasons.append(f"Known specimen document number: {doc_number}")

        # Check against fake patterns
        for pattern in cls.FAKE_DOC_NUMBER_PATTERNS:
            if re.match(pattern, doc_number_clean, re.IGNORECASE):
                score += 0.8
                reasons.append(f"Suspicious document number pattern: {doc_number}")
                break

        # Check for sequential digits
        if doc_number_clean.isdigit() and len(doc_number_clean) >= 5:
            digits = doc_number_clean

            # Count how many digits follow sequential pattern
            sequential_count = sum(1 for i in range(1, len(digits)) if int(digits[i]) == int(digits[i-1]) + 1)
            reverse_sequential_count = sum(1 for i in range(1, len(digits)) if int(digits[i]) == int(digits[i-1]) - 1)

            total_transitions = len(digits) - 1
            seq_ratio = max(sequential_count, reverse_sequential_count) / total_transitions if total_transitions > 0 else 0

            # Perfect sequential (12345678)
            if seq_ratio == 1.0:
                score += 0.9
                reasons.append(f"Sequential document number: {doc_number}")
            # Almost sequential (e.g., 123456790 - most digits are sequential)
            elif seq_ratio >= 0.7:
                score += 0.7
                reasons.append(f"Nearly sequential document number: {doc_number}")
            # Partially sequential (e.g., 12345000)
            elif seq_ratio >= 0.5:
                score += 0.5
                reasons.append(f"Partially sequential document number: {doc_number}")

        return score, reasons

    @classmethod
    def _check_suspicious_dates(cls, extracted_data: Dict[str, Any]) -> Tuple[float, List[str]]:
        """Check for suspicious/placeholder dates."""
        reasons = []
        score = 0.0

        date_fields = ["date_of_birth", "issue_date", "expiry_date"]

        for field in date_fields:
            date_value = extracted_data.get(field)
            if not date_value:
                continue

            date_str = str(date_value).strip()

            # Check against known suspicious dates
            if date_str in cls.SUSPICIOUS_DATES:
                score += 0.6
                reasons.append(f"Suspicious {field}: {date_str}")
                continue

            # Parse and check birth year
            if field == "date_of_birth":
                try:
                    if "-" in date_str:
                        year = int(date_str.split("-")[0])
                    elif "/" in date_str:
                        parts = date_str.split("/")
                        year = int(parts[-1]) if len(parts[-1]) == 4 else int(parts[0])
                    else:
                        continue

                    if year in cls.SUSPICIOUS_BIRTH_YEARS:
                        score += 0.4
                        reasons.append(f"Suspicious birth year: {year}")

                    # Very old birth year
                    current_year = datetime.now().year
                    if year < 1920:
                        score += 0.5
                        reasons.append(f"Unrealistic birth year: {year}")

                except (ValueError, IndexError):
                    pass

        return score, reasons

    @classmethod
    def _check_mrz_anomalies(cls, extracted_data: Dict[str, Any]) -> Tuple[float, List[str]]:
        """Check for MRZ anomalies in passports."""
        mrz = extracted_data.get("mrz") or ""
        if not mrz:
            return 0.0, []

        reasons = []
        score = 0.0

        mrz_upper = mrz.upper()

        # Check for specimen indicators in MRZ
        if "SPECIMEN" in mrz_upper or "SAMPLE" in mrz_upper:
            score += 1.0
            reasons.append("MRZ contains SPECIMEN/SAMPLE text")

        # Check for placeholder patterns in MRZ
        if "<<<<<<<<<<<" in mrz_upper.replace("<", "").replace(">", "") == "":
            # MRZ is all filler characters
            score += 0.8
            reasons.append("MRZ contains only filler characters")

        # Check for repeated patterns
        if "DOEDOE" in mrz_upper or "JOHNJOHN" in mrz_upper:
            score += 0.7
            reasons.append("MRZ contains repeated name patterns")

        return score, reasons

    @classmethod
    def _check_fake_address(cls, extracted_data: Dict[str, Any]) -> Tuple[float, List[str]]:
        """Check for fake/placeholder addresses."""
        address = (extracted_data.get("address") or "").lower().strip()
        if not address:
            return 0.0, []

        reasons = []
        score = 0.0

        # Check against known fake address patterns
        for fake_addr in cls.FAKE_ADDRESS_PATTERNS:
            if fake_addr in address:
                score += 0.8
                reasons.append(f"Fake address pattern: '{fake_addr}'")
                break

        return score, reasons
