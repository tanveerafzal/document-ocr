import time
from datetime import datetime
from typing import Dict, Any
from app.services.validators.base import BaseValidator
from app.models.responses import ValidatorResult, ValidationStatus


class DocumentExpiryValidator(BaseValidator):
    """Check if the document has expired."""

    name = "document_expiry"

    async def validate(self, document_data: Dict[str, Any]) -> ValidatorResult:
        start_time = time.perf_counter()

        skip_result = self._skip_if_missing(document_data, ["expiry_date"])
        if skip_result:
            skip_result.execution_time_ms = (time.perf_counter() - start_time) * 1000
            return skip_result

        expiry_date = self._parse_date(document_data.get("expiry_date"))
        execution_time = (time.perf_counter() - start_time) * 1000

        if not expiry_date:
            return self._create_result(
                status=ValidationStatus.WARNING,
                message="Could not parse expiry date format",
                details={"raw_expiry_date": document_data.get("expiry_date")},
                execution_time_ms=execution_time
            )

        now = datetime.now()
        days_until_expiry = (expiry_date - now).days

        if days_until_expiry < 0:
            return self._create_result(
                status=ValidationStatus.FAILED,
                message=f"Document expired {abs(days_until_expiry)} days ago",
                details={
                    "expiry_date": expiry_date.strftime("%Y-%m-%d"),
                    "days_expired": abs(days_until_expiry)
                },
                execution_time_ms=execution_time
            )
        elif days_until_expiry < 30:
            return self._create_result(
                status=ValidationStatus.WARNING,
                message=f"Document expires in {days_until_expiry} days",
                details={
                    "expiry_date": expiry_date.strftime("%Y-%m-%d"),
                    "days_until_expiry": days_until_expiry
                },
                execution_time_ms=execution_time
            )

        return self._create_result(
            status=ValidationStatus.PASSED,
            message=f"Document valid for {days_until_expiry} days",
            details={
                "expiry_date": expiry_date.strftime("%Y-%m-%d"),
                "days_until_expiry": days_until_expiry
            },
            execution_time_ms=execution_time
        )
