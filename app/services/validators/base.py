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
            "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y",
            "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%Y",
            "%B %d, %Y", "%d %B %Y", "%b %d, %Y",
            "%d %b %Y", "%Y%m%d"
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        return None
