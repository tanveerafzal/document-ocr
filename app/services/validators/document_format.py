import re
import time
from typing import Dict, Any, List, Tuple
from app.services.validators.base import BaseValidator
from app.models.responses import ValidatorResult, ValidationStatus


class DocumentFormatValidator(BaseValidator):
    """Validate document number matches known patterns."""

    name = "document_format"

    # Known document number patterns by type/country
    PATTERNS: List[Tuple[str, str, str]] = [
        # (name, pattern, description)
        # Canadian Documents
        ("CA_ONTARIO_DL", r"^[A-Z]\d{4}-?\d{5}-?\d{5}$", "Ontario Driver's Licence"),
        ("CA_BC_DL", r"^(DL:?)?\d{6,7}$", "BC Driver's Licence"),
        ("CA_ALBERTA_DL", r"^\d{6}-?\d{3}$", "Alberta Driver's Licence"),
        ("CA_QUEBEC_DL", r"^[A-Z]\d{12}$", "Quebec Driver's Licence"),
        ("CA_PASSPORT", r"^[A-Z]{2}\d{6}$", "Canadian Passport"),
        # US Documents
        ("US_PASSPORT", r"^[A-Z]\d{8}$", "US Passport"),
        ("US_DL_CALIFORNIA", r"^[A-Z]\d{7}$", "California Driver's License"),
        ("US_DL_TEXAS", r"^\d{8}$", "Texas Driver's License"),
        ("US_DL_FLORIDA", r"^[A-Z]\d{12}$", "Florida Driver's License"),
        ("US_DL_NEW_YORK", r"^\d{9}$", "New York Driver's License"),
        ("US_DL_OHIO", r"^[A-Z]{2}\d{6}$", "Ohio Driver's License"),
        ("US_DRIVERS_LICENSE", r"^[A-Z]{1,2}\d{6,14}$", "US Driver's License (generic)"),
        # UK/EU Documents
        ("UK_PASSPORT", r"^\d{9}$", "UK Passport"),
        ("UK_DRIVERS_LICENSE", r"^[A-Z]{5}\d{6}[A-Z]{2}\d{2}$", "UK Driver's License"),
        ("EU_ID", r"^[A-Z]{2}\d{7}$", "European ID Card"),
        # Generic patterns (should be last as fallback)
        ("GENERIC_NUMERIC", r"^\d{6,12}$", "Generic numeric ID"),
        ("GENERIC_ALPHANUMERIC", r"^[A-Z0-9]{6,15}$", "Generic alphanumeric ID"),
    ]

    async def validate(self, document_data: Dict[str, Any]) -> ValidatorResult:
        start_time = time.perf_counter()

        skip_result = self._skip_if_missing(document_data, ["document_number"])
        if skip_result:
            skip_result.execution_time_ms = (time.perf_counter() - start_time) * 1000
            return skip_result

        doc_number = document_data.get("document_number", "").strip().upper()
        # Clean version without spaces/dashes for matching
        doc_number_clean = re.sub(r"[\s\-]", "", doc_number)

        matched_patterns = []
        for name, pattern, description in self.PATTERNS:
            if re.match(pattern, doc_number) or re.match(pattern, doc_number_clean):
                matched_patterns.append({
                    "pattern_name": name,
                    "description": description
                })

        execution_time = (time.perf_counter() - start_time) * 1000

        if matched_patterns:
            return self._create_result(
                status=ValidationStatus.PASSED,
                message=f"Document number matches {len(matched_patterns)} known format(s)",
                details={
                    "document_number": doc_number,
                    "matched_patterns": matched_patterns
                },
                execution_time_ms=execution_time
            )

        # If no pattern matches, issue a warning (not necessarily invalid)
        return self._create_result(
            status=ValidationStatus.WARNING,
            message="Document number does not match common formats",
            details={
                "document_number": doc_number,
                "note": "May still be valid - format not in known patterns"
            },
            execution_time_ms=execution_time
        )
