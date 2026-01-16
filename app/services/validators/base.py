from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional, List
from app.models.responses import ValidatorResult, ValidationStatus


class BaseValidator(ABC):
    """Abstract base class for all validators."""

    name: str = "base_validator"

    @abstractmethod
    async def validate(self, document_data: Dict[str, Any]) -> ValidatorResult:
        """
        Run validation check on document data.

        Args:
            document_data: Dictionary with extracted document fields

        Returns:
            ValidatorResult with status, message, and details
        """
        pass

    def _create_result(
        self,
        status: ValidationStatus,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        execution_time_ms: float = 0
    ) -> ValidatorResult:
        """Helper to create consistent ValidatorResult."""
        return ValidatorResult(
            validator_name=self.name,
            status=status,
            message=message,
            details=details,
            execution_time_ms=execution_time_ms
        )

    def _skip_if_missing(
        self,
        document_data: Dict[str, Any],
        required_fields: List[str]
    ) -> Optional[ValidatorResult]:
        """Return SKIPPED result if required fields are missing."""
        missing = [f for f in required_fields if not document_data.get(f)]
        if missing:
            return self._create_result(
                status=ValidationStatus.SKIPPED,
                message=f"Required fields missing: {', '.join(missing)}",
                details={"missing_fields": missing}
            )
        return None

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string in common formats."""
        if not date_str:
            return None

        formats = [
            # ISO and common formats
            "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y",
            "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%Y",
            # With month names (full and abbreviated)
            "%Y-%b-%d", "%Y-%B-%d",  # 2027-Aug-07, 2027-August-07
            "%d-%b-%Y", "%d-%B-%Y",  # 07-Aug-2027, 07-August-2027
            "%b-%d-%Y", "%B-%d-%Y",  # Aug-07-2027, August-07-2027
            "%B %d, %Y", "%d %B %Y", "%b %d, %Y",
            "%d %b %Y", "%b %d %Y", "%B %d %Y",
            # Compact format
            "%Y%m%d",
            # Slash with month names
            "%Y/%b/%d", "%d/%b/%Y",
            "%Y/%B/%d", "%d/%B/%Y",
        ]

        # Normalize the date string (handle case variations)
        normalized = date_str.strip()

        for fmt in formats:
            try:
                return datetime.strptime(normalized, fmt)
            except ValueError:
                continue

        # Try with title case for month names
        try:
            normalized_title = normalized.title()
            for fmt in formats:
                try:
                    return datetime.strptime(normalized_title, fmt)
                except ValueError:
                    continue
        except:
            pass

        return None
