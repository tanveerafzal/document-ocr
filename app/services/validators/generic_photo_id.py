import re
import time
from datetime import datetime
from typing import Dict, Any
from app.services.validators.base import BaseValidator
from app.models.responses import ValidatorResult, ValidationStatus


class GenericPhotoIDValidator(BaseValidator):
    """
    Validate Photo Card / Photo ID documents.

    This validator handles Photo Cards and Photo IDs from various provinces/states.
    It performs basic validation:
    - Document number format (alphanumeric)
    - Date validations (issue date, expiry date, date of birth)
    - Expiry check
    """

    name = "generic_photo_id"

    async def validate(self, document_data: Dict[str, Any]) -> ValidatorResult:
        start_time = time.perf_counter()

        issues = []
        warnings = []
        details = {"checks_performed": []}

        document_number = document_data.get("document_number", "") or ""
        date_of_birth = document_data.get("date_of_birth")
        issue_date_str = document_data.get("issue_date")
        expiry_date = document_data.get("expiry_date")

        # Check 1: Document number present
        details["checks_performed"].append("document_number_check")
        clean_number = re.sub(r"[\s\-]", "", document_number.strip().upper())

        if not clean_number:
            issues.append("Missing document number")
        elif len(clean_number) < 4:
            warnings.append(f"Document number '{document_number}' seems too short")
        else:
            details["document_number_valid"] = True
            details["document_number_length"] = len(clean_number)

        # Check 2: Date of birth validation
        details["checks_performed"].append("date_of_birth_check")
        if date_of_birth:
            dob = self._parse_date(date_of_birth)
            if dob:
                today = datetime.now()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                details["calculated_age"] = age

                if dob > today:
                    issues.append("Date of birth cannot be in the future")
                elif age < 0:
                    issues.append("Invalid date of birth")

        # Check 3: Issue date validation
        details["checks_performed"].append("issue_date_check")
        if issue_date_str:
            issue_date = self._parse_date(issue_date_str)
            if issue_date:
                today = datetime.now()
                if issue_date > today:
                    issues.append("Issue date cannot be in the future")
                elif date_of_birth:
                    dob = self._parse_date(date_of_birth)
                    if dob and issue_date < dob:
                        issues.append("Issue date cannot be before date of birth")

        # Check 4: Expiry check
        details["checks_performed"].append("expiry_check")
        if expiry_date:
            exp = self._parse_date(expiry_date)
            if exp:
                today = datetime.now()
                if exp < today:
                    days_expired = (today - exp).days
                    issues.append(f"Photo ID expired {days_expired} days ago")
                else:
                    days_until_expiry = (exp - today).days
                    details["days_until_expiry"] = days_until_expiry
                    if days_until_expiry < 30:
                        warnings.append(f"Photo ID expires in {days_until_expiry} days")

        # Check 5: Validity period
        details["checks_performed"].append("validity_period")
        if issue_date_str and expiry_date:
            issue_date = self._parse_date(issue_date_str)
            exp = self._parse_date(expiry_date)
            if issue_date and exp:
                validity_days = (exp - issue_date).days
                validity_years = validity_days / 365.25
                details["validity_years"] = round(validity_years, 1)

                if validity_years < 1:
                    warnings.append(f"Photo ID has very short validity ({validity_years:.1f} years)")
                elif validity_years > 10:
                    warnings.append(f"Photo ID has unusually long validity ({validity_years:.1f} years)")

        execution_time = (time.perf_counter() - start_time) * 1000

        if issues:
            return self._create_result(
                status=ValidationStatus.FAILED,
                message=f"Photo ID validation failed: {'; '.join(issues)}",
                details={**details, "issues": issues, "warnings": warnings},
                execution_time_ms=execution_time
            )
        elif warnings:
            return self._create_result(
                status=ValidationStatus.WARNING,
                message="Photo ID validation passed with warnings",
                details={**details, "warnings": warnings},
                execution_time_ms=execution_time
            )
        else:
            return self._create_result(
                status=ValidationStatus.PASSED,
                message="Photo ID validation passed",
                details=details,
                execution_time_ms=execution_time
            )
