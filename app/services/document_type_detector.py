import re
import logging
from typing import Dict, Any, Optional

from app.models.document_types import DocumentType, DocumentTypeInfo, DOCUMENT_PATTERNS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentTypeDetector:
    """Detects the type of ID document based on extracted fields and patterns."""

    @classmethod
    def detect(cls, extracted_data: Dict[str, Any], request_id: str = "") -> DocumentTypeInfo:
        """
        Detect document type from extracted fields.

        Args:
            extracted_data: Dictionary with extracted document fields
            request_id: Optional request ID for logging

        Returns:
            DocumentTypeInfo with detected type and confidence
        """
        log_prefix = f"[{request_id}]" if request_id else ""

        logger.info(f"{log_prefix} ========== DOCUMENT TYPE DETECTION ==========")

        document_number = extracted_data.get("document_number", "") or ""
        address = extracted_data.get("address", "") or ""
        full_text = cls._build_full_text(extracted_data)

        best_match: Optional[DocumentTypeInfo] = None
        best_score = 0.0

        for doc_type, patterns in DOCUMENT_PATTERNS.items():
            score, features = cls._calculate_match_score(
                doc_type, patterns, document_number, address, full_text
            )

            logger.info(f"{log_prefix}   Checking {patterns['name']}: score={score:.2f}, features={features}")

            if score > best_score:
                best_score = score
                best_match = DocumentTypeInfo(
                    document_type=doc_type,
                    confidence=score,
                    country=patterns.get("country"),
                    state_province=patterns.get("state_province"),
                    document_name=patterns["name"],
                    detected_features=features
                )

        # If no good match found, return unknown
        if best_match is None or best_score < 0.3:
            logger.info(f"{log_prefix}   Result: UNKNOWN (no confident match)")
            return DocumentTypeInfo(
                document_type=DocumentType.UNKNOWN,
                confidence=0.0,
                country=None,
                state_province=None,
                document_name="Unknown Document",
                detected_features=[]
            )

        logger.info(f"{log_prefix}   Result: {best_match.document_name} (confidence: {best_match.confidence:.2f})")
        logger.info(f"{log_prefix} =============================================")

        return best_match

    @classmethod
    def _build_full_text(cls, data: Dict[str, Any]) -> str:
        """Combine all text fields for keyword searching."""
        parts = []
        for key, value in data.items():
            if value and isinstance(value, str):
                parts.append(value.lower())
        return " ".join(parts)

    @classmethod
    def _calculate_match_score(
        cls,
        doc_type: DocumentType,
        patterns: Dict[str, Any],
        document_number: str,
        address: str,
        full_text: str
    ) -> tuple[float, list[str]]:
        """
        Calculate how well the document matches a specific type.

        Returns (score, detected_features)
        """
        score = 0.0
        features = []

        # Check document number format
        license_format = patterns.get("license_format")
        if license_format and document_number:
            clean_number = document_number.strip().upper()
            if re.match(license_format, clean_number):
                score += 0.4
                features.append(f"document_number_format_match")

        # Check keywords in text
        keywords = patterns.get("keywords", [])
        matched_keywords = []
        for keyword in keywords:
            if keyword.lower() in full_text.lower():
                matched_keywords.append(keyword)

        if matched_keywords:
            keyword_score = min(len(matched_keywords) * 0.15, 0.45)
            score += keyword_score
            features.append(f"keywords_found: {', '.join(matched_keywords)}")

        # Ontario-specific: Check for Ontario address
        if doc_type == DocumentType.ONTARIO_DRIVERS_LICENSE:
            ontario_indicators = ["ontario", " on ", ", on", "on,", "toronto", "ottawa", "mississauga"]
            for indicator in ontario_indicators:
                if indicator.lower() in address.lower() or indicator.lower() in full_text.lower():
                    score += 0.15
                    features.append(f"ontario_address_indicator: {indicator}")
                    break

        return score, features

    @classmethod
    def is_ontario_drivers_license(cls, extracted_data: Dict[str, Any]) -> bool:
        """Quick check if document is likely an Ontario Driver's License."""
        doc_info = cls.detect(extracted_data)
        return doc_info.document_type == DocumentType.ONTARIO_DRIVERS_LICENSE and doc_info.confidence >= 0.5
