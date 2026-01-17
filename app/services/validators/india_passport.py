import re
import time
from datetime import datetime
from typing import Dict, Any
from app.services.validators.base import BaseValidator
from app.models.responses import ValidatorResult, ValidationStatus


class IndiaPassportValidator(BaseValidator):
    """
    Validate India Passport specific requirements.

    India Passport specifics:
    - Passport number format: 1 letter + 7 digits (e.g., A1234567)
    - First letter indicates passport type and issuing office
    - MRZ country code: IND
    - Validity period: 10 years for adults, 5 years for minors (under 18)
    - Issue date must be after date of birth
    """

    name = "india_passport"
    COUNTRY_CODE = "IND"

    async def validate(self, document_data: Dict[str, Any]) -> ValidatorResult:
        start_time = time.perf_counter()

        issues = []
        warnings = []
        details = {"checks_performed": [], "country": "India", "country_code": self.COUNTRY_CODE}

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

        # Check 2: Passport number format (1 letter + 7 digits)
        details["checks_performed"].append("passport_number_format")
        clean_number = re.sub(r"[\s\-]", "", document_number.strip().upper())

        india_passport_format = r"^[A-Z]\d{7}$"

        if not clean_number:
            issues.append("Missing passport number")
        elif not re.match(india_passport_format, clean_number):
            if len(clean_number) == 8 and clean_number[0].isalpha():
                warnings.append(
                    f"Passport number '{document_number}' may have format issues. "
                    "India passport: 1 letter + 7 digits (e.g., A1234567)"
                )
            else:
                issues.append(
                    f"Invalid India passport format. Expected: 1 letter + 7 digits (e.g., A1234567), "
                    f"Got: {document_number}"
                )
        else:
            details["passport_number_valid"] = True
            details["passport_prefix"] = clean_number[0]

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

        # Check 4: Validity period (5 years for under 18, 10 years for 18+)
        details["checks_performed"].append("validity_period")
        if issue_date_str and expiry_date:
            issue_date = self._parse_date(issue_date_str)
            exp = self._parse_date(expiry_date)
            if issue_date and exp:
                validity_days = (exp - issue_date).days
                validity_years = validity_days / 365.25
                details["validity_years"] = round(validity_years, 1)

                if age_at_issue is not None:
                    if age_at_issue < 18:
                        if not (4.5 <= validity_years <= 5.5):
                            warnings.append(
                                f"Minor passport (age {age_at_issue} at issue) has {validity_years:.1f} year validity. "
                                f"Expected ~5 years for applicants under 18."
                            )
                        else:
                            details["validity_matches_age"] = True
                    else:
                        if not (9.5 <= validity_years <= 10.5):
                            warnings.append(
                                f"Adult passport (age {age_at_issue} at issue) has {validity_years:.1f} year validity. "
                                f"Expected ~10 years for applicants 18+."
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
                message=f"India Passport validation failed: {'; '.join(issues)}",
                details={**details, "issues": issues, "warnings": warnings},
                execution_time_ms=execution_time
            )
        elif warnings:
            return self._create_result(
                status=ValidationStatus.WARNING,
                message="India Passport validation passed with warnings",
                details={**details, "warnings": warnings},
                execution_time_ms=execution_time
            )
        else:
            return self._create_result(
                status=ValidationStatus.PASSED,
                message="India Passport validation passed",
                details=details,
                execution_time_ms=execution_time
            )
