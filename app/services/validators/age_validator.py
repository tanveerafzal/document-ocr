import time
from datetime import datetime
from typing import Dict, Any
from app.services.validators.base import BaseValidator
from app.models.responses import ValidatorResult, ValidationStatus


class AgeValidator(BaseValidator):
    """Validate if person meets minimum age requirement."""

    name = "age_validation"

    def __init__(self, minimum_age: int = 18):
        self.minimum_age = minimum_age

    async def validate(self, document_data: Dict[str, Any]) -> ValidatorResult:
        start_time = time.perf_counter()

        skip_result = self._skip_if_missing(document_data, ["date_of_birth"])
        if skip_result:
            skip_result.execution_time_ms = (time.perf_counter() - start_time) * 1000
            return skip_result

        dob = self._parse_date(document_data.get("date_of_birth"))
        execution_time = (time.perf_counter() - start_time) * 1000

        if not dob:
            return self._create_result(
                status=ValidationStatus.WARNING,
                message="Could not parse date of birth format",
                details={"raw_dob": document_data.get("date_of_birth")},
                execution_time_ms=execution_time
            )

        today = datetime.now()
        age = today.year - dob.year - (
            (today.month, today.day) < (dob.month, dob.day)
        )

        if age < self.minimum_age:
            return self._create_result(
                status=ValidationStatus.FAILED,
                message=f"Person is {age} years old, minimum required is {self.minimum_age}",
                details={
                    "calculated_age": age,
                    "minimum_age": self.minimum_age,
                    "date_of_birth": dob.strftime("%Y-%m-%d")
                },
                execution_time_ms=execution_time
            )

        return self._create_result(
            status=ValidationStatus.PASSED,
            message=f"Age verification passed ({age} years old)",
            details={
                "calculated_age": age,
                "minimum_age": self.minimum_age
            },
            execution_time_ms=execution_time
        )
