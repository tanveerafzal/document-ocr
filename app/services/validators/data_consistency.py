import time
from datetime import datetime
from typing import Dict, Any
from app.services.validators.base import BaseValidator
from app.models.responses import ValidatorResult, ValidationStatus


class DataConsistencyValidator(BaseValidator):
    """Validate logical consistency of document dates and data."""

    name = "data_consistency"

    async def validate(self, document_data: Dict[str, Any]) -> ValidatorResult:
        start_time = time.perf_counter()

        skip_result = self._skip_if_missing(
            document_data,
            ["date_of_birth", "expiry_date"]
        )
        if skip_result:
            skip_result.execution_time_ms = (time.perf_counter() - start_time) * 1000
            return skip_result

        issues = []

        try:
            dob = self._parse_date(document_data.get("date_of_birth"))
            issue_date = self._parse_date(document_data.get("issue_date"))
            expiry_date = self._parse_date(document_data.get("expiry_date"))

            # Check: DOB should be before issue date
            if dob and issue_date and dob >= issue_date:
                issues.append("Date of birth is not before issue date")

            # Check: Issue date should be before expiry date
            if issue_date and expiry_date and issue_date >= expiry_date:
                issues.append("Issue date is not before expiry date")

            # Check: DOB should be reasonable (person not > 150 years old)
            if dob:
                age = (datetime.now() - dob).days // 365
                if age > 150 or age < 0:
                    issues.append(f"Unrealistic age calculated: {age} years")

            # Check: Expiry date should be reasonable (not > 50 years from issue)
            if issue_date and expiry_date:
                validity_years = (expiry_date - issue_date).days // 365
                if validity_years > 50:
                    issues.append(f"Unusual document validity period: {validity_years} years")

            # Note: We do NOT check minimum age at issue because:
            # - Passports can be issued to children of any age (including newborns)
            # - Driver's licenses have their own age validation in specific validators

        except Exception as e:
            issues.append(f"Date parsing error: {str(e)}")

        execution_time = (time.perf_counter() - start_time) * 1000

        if issues:
            return self._create_result(
                status=ValidationStatus.FAILED,
                message="Data consistency issues found",
                details={"issues": issues},
                execution_time_ms=execution_time
            )

        return self._create_result(
            status=ValidationStatus.PASSED,
            message="All date relationships are consistent",
            execution_time_ms=execution_time
        )
