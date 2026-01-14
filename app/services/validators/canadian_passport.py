import re
import time
from datetime import datetime
from typing import Dict, Any
from app.services.validators.base import BaseValidator
from app.models.responses import ValidatorResult, ValidationStatus


class CanadianPassportValidator(BaseValidator):
    """
    Validate Canadian Passport specific requirements.

    Canadian Passport specifics:
    - Passport number format: 2 letters + 6 digits (e.g., AB123456)
    - Validity period: 5 years for children under 16, 10 years for adults (16+)
    - Issue date must be after date of birth
    - Passport cannot be issued before person is born
    - Standard validity periods: exactly 5 or 10 years
    """

    name = "canadian_passport"

    async def validate(self, document_data: Dict[str, Any]) -> ValidatorResult:
        start_time = time.perf_counter()

        issues = []
        warnings = []
        details = {"checks_performed": []}

        document_number = document_data.get("document_number", "") or ""
        date_of_birth = document_data.get("date_of_birth")
        issue_date_str = document_data.get("issue_date")
        expiry_date = document_data.get("expiry_date")

        # Check 1: Passport number format (2 letters + 6 digits)
        details["checks_performed"].append("passport_number_format")
        clean_number = document_number.strip().upper()
        # Remove any spaces or special characters
        clean_number = re.sub(r"[\s\-]", "", clean_number)

        canadian_passport_format = r"^[A-Z]{2}\d{6}$"

        if not clean_number:
            issues.append("Missing passport number")
        elif not re.match(canadian_passport_format, clean_number):
            # Check for common OCR errors - must start with 2 letters
            if len(clean_number) == 8 and clean_number[:2].isalpha():
                warnings.append(
                    f"Passport number '{document_number}' may have OCR errors in digit portion. "
                    "Expected format: AA123456"
                )
            else:
                issues.append(
                    f"Invalid Canadian passport format. Expected: AA123456 (2 letters + 6 digits), "
                    f"Got: {document_number}"
                )
        else:
            details["passport_number_valid"] = True
            details["passport_prefix"] = clean_number[:2]

        # Check 2: Calculate age at issue date
        details["checks_performed"].append("age_at_issue")
        age_at_issue = None
        if date_of_birth and issue_date_str:
            dob = self._parse_date(date_of_birth)
            issue_date = self._parse_date(issue_date_str)
            if dob and issue_date:
                age_at_issue = issue_date.year - dob.year - (
                    (issue_date.month, issue_date.day) < (dob.month, dob.day)
                )
                details["age_at_issue"] = age_at_issue

                if issue_date < dob:
                    issues.append("Issue date cannot be before date of birth")

        # Check 3: Validity period (5 years for under 16, 10 years for 16+)
        details["checks_performed"].append("validity_period")
        if issue_date_str and expiry_date:
            issue_date = self._parse_date(issue_date_str)
            exp = self._parse_date(expiry_date)
            if issue_date and exp:
                validity_days = (exp - issue_date).days
                validity_years = validity_days / 365.25
                details["validity_years"] = round(validity_years, 1)

                # Check if validity matches expected duration
                if age_at_issue is not None:
                    if age_at_issue < 16:
                        # Child passport: should be ~5 years
                        expected_years = 5
                        if not (4.5 <= validity_years <= 5.5):
                            warnings.append(
                                f"Child passport (age {age_at_issue} at issue) has {validity_years:.1f} year validity. "
                                f"Expected ~5 years for applicants under 16."
                            )
                        else:
                            details["validity_matches_age"] = True
                    else:
                        # Adult passport: should be ~10 years
                        expected_years = 10
                        if not (9.5 <= validity_years <= 10.5):
                            warnings.append(
                                f"Adult passport (age {age_at_issue} at issue) has {validity_years:.1f} year validity. "
                                f"Expected ~10 years for applicants 16+."
                            )
                        else:
                            details["validity_matches_age"] = True
                else:
                    # Can't determine age at issue, just check for reasonable validity
                    if validity_years < 4.5:
                        warnings.append(f"Unusual short validity period: {validity_years:.1f} years")
                    elif validity_years > 10.5:
                        issues.append(
                            f"Invalid validity period: {validity_years:.1f} years. "
                            "Canadian passports are valid for max 10 years."
                        )

        # Check 4: Current age check
        details["checks_performed"].append("current_age")
        if date_of_birth:
            dob = self._parse_date(date_of_birth)
            if dob:
                today = datetime.now()
                current_age = today.year - dob.year - (
                    (today.month, today.day) < (dob.month, dob.day)
                )
                details["current_age"] = current_age

                if current_age < 0:
                    issues.append("Date of birth is in the future")
                elif current_age > 120:
                    issues.append(f"Unrealistic age: {current_age} years")

        # Check 5: Issue date reasonability
        details["checks_performed"].append("issue_date_reasonable")
        if issue_date_str:
            issue_date = self._parse_date(issue_date_str)
            if issue_date:
                today = datetime.now()
                # Canadian passport program started in 1947, modern format since ~1985
                min_reasonable_date = datetime(1985, 1, 1)

                if issue_date > today:
                    issues.append("Issue date cannot be in the future")
                elif issue_date < min_reasonable_date:
                    warnings.append(
                        f"Issue date {issue_date.strftime('%Y-%m-%d')} predates modern passport format"
                    )
                else:
                    details["issue_date_reasonable"] = True

        execution_time = (time.perf_counter() - start_time) * 1000

        # Determine result status
        if issues:
            return self._create_result(
                status=ValidationStatus.FAILED,
                message=f"Canadian Passport validation failed: {'; '.join(issues)}",
                details={
                    **details,
                    "issues": issues,
                    "warnings": warnings
                },
                execution_time_ms=execution_time
            )
        elif warnings:
            return self._create_result(
                status=ValidationStatus.WARNING,
                message="Canadian Passport validation passed with warnings",
                details={
                    **details,
                    "warnings": warnings
                },
                execution_time_ms=execution_time
            )
        else:
            return self._create_result(
                status=ValidationStatus.PASSED,
                message="Canadian Passport validation passed",
                details=details,
                execution_time_ms=execution_time
            )
