import re
import time
from datetime import datetime
from typing import Dict, Any
from app.services.validators.base import BaseValidator
from app.models.responses import ValidatorResult, ValidationStatus


class UKPassportValidator(BaseValidator):
    """
    Validate UK Passport specific requirements.

    UK Passport specifics:
    - Passport number format: 9 digits
    - MRZ country code: GBR
    - Validity period: 10 years for adults, 5 years for children under 16
    - Issue date must be after date of birth
    """

    name = "uk_passport"
    COUNTRY_CODE = "GBR"

    async def validate(self, document_data: Dict[str, Any]) -> ValidatorResult:
        start_time = time.perf_counter()

        issues = []
        warnings = []
        details = {"checks_performed": [], "country": "United Kingdom", "country_code": self.COUNTRY_CODE}

        document_number = document_data.get("document_number", "") or ""
        date_of_birth = document_data.get("date_of_birth")
        issue_date_str = document_data.get("issue_date")
        expiry_date = document_data.get("expiry_date")
        country_code = document_data.get("country_code", "") or ""

        # Check 1: Country code verification
        details["checks_performed"].append("country_code_check")
        if country_code and country_code.upper() != self.COUNTRY_CODE:
            warnings.append(
                f"Country code '{country_code}' does not match expected '{self.COUNTRY_CODE}'"
            )
        elif country_code:
            details["country_code_verified"] = True

        # Check 2: Passport number format (9 digits)
        details["checks_performed"].append("passport_number_format")
        clean_number = re.sub(r"[\s\-]", "", document_number.strip())

        uk_passport_format = r"^\d{9}$"

        if not clean_number:
            issues.append("Missing passport number")
        elif not re.match(uk_passport_format, clean_number):
            if clean_number.isdigit() and 8 <= len(clean_number) <= 10:
                warnings.append(
                    f"Passport number '{document_number}' has {len(clean_number)} digits. "
                    "UK passport numbers are typically 9 digits."
                )
            else:
                issues.append(
                    f"Invalid UK passport format. Expected: 9 digits, Got: {document_number}"
                )
        else:
            details["passport_number_valid"] = True

        # Check 3: Calculate age at issue date
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

        # Check 4: Validity period (5 years for under 16, 10 years for 16+)
        details["checks_performed"].append("validity_period")
        if issue_date_str and expiry_date:
            issue_date = self._parse_date(issue_date_str)
            exp = self._parse_date(expiry_date)
            if issue_date and exp:
                validity_days = (exp - issue_date).days
                validity_years = validity_days / 365.25
                details["validity_years"] = round(validity_years, 1)

                if age_at_issue is not None:
                    if age_at_issue < 16:
                        if not (4.5 <= validity_years <= 5.5):
                            warnings.append(
                                f"Child passport (age {age_at_issue} at issue) has {validity_years:.1f} year validity. "
                                f"Expected ~5 years for applicants under 16."
                            )
                        else:
                            details["validity_matches_age"] = True
                    else:
                        if not (9.5 <= validity_years <= 10.5):
                            warnings.append(
                                f"Adult passport (age {age_at_issue} at issue) has {validity_years:.1f} year validity. "
                                f"Expected ~10 years for applicants 16+."
                            )
                        else:
                            details["validity_matches_age"] = True

        # Check 5: Expiry check
        details["checks_performed"].append("expiry_check")
        if expiry_date:
            exp = self._parse_date(expiry_date)
            if exp:
                today = datetime.now()
                if exp < today:
                    days_expired = (today - exp).days
                    issues.append(f"Passport expired {days_expired} days ago")
                else:
                    days_until_expiry = (exp - today).days
                    details["days_until_expiry"] = days_until_expiry
                    if days_until_expiry < 180:
                        warnings.append(
                            f"Passport expires in {days_until_expiry} days. "
                            "Many countries require 6+ months validity for entry."
                        )

        execution_time = (time.perf_counter() - start_time) * 1000

        if issues:
            return self._create_result(
                status=ValidationStatus.FAILED,
                message=f"UK Passport validation failed: {'; '.join(issues)}",
                details={**details, "issues": issues, "warnings": warnings},
                execution_time_ms=execution_time
            )
        elif warnings:
            return self._create_result(
                status=ValidationStatus.WARNING,
                message="UK Passport validation passed with warnings",
                details={**details, "warnings": warnings},
                execution_time_ms=execution_time
            )
        else:
            return self._create_result(
                status=ValidationStatus.PASSED,
                message="UK Passport validation passed",
                details=details,
                execution_time_ms=execution_time
            )
