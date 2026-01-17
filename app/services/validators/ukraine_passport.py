import re
import time
from datetime import datetime
from typing import Dict, Any
from app.services.validators.base import BaseValidator
from app.models.responses import ValidatorResult, ValidationStatus


class UkrainePassportValidator(BaseValidator):
    """
    Validate Ukraine Passport specific requirements.

    Ukraine Passport specifics:
    - Passport number format: 2 letters + 6 digits (e.g., AA123456)
    - MRZ country code: UKR
    - Validity period: 10 years for adults (18+), 4 years for minors
    - Issue date must be after date of birth
    """

    name = "ukraine_passport"
    COUNTRY_CODE = "UKR"

    async def validate(self, document_data: Dict[str, Any]) -> ValidatorResult:
        start_time = time.perf_counter()

        issues = []
        warnings = []
        details = {"checks_performed": [], "country": "Ukraine", "country_code": self.COUNTRY_CODE}

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

        # Check 2: Passport number format (2 letters + 6 digits)
        details["checks_performed"].append("passport_number_format")
        clean_number = re.sub(r"[\s\-]", "", document_number.strip().upper())

        # Ukraine passport: 2 letters + 6 digits
        ukraine_passport_format = r"^[A-Z]{2}\d{6}$"

        if not clean_number:
            issues.append("Missing passport number")
        elif not re.match(ukraine_passport_format, clean_number):
            if len(clean_number) == 8 and clean_number[:2].isalpha():
                warnings.append(
                    f"Passport number '{document_number}' may have format issues. "
                    "Ukraine passport: 2 letters + 6 digits (e.g., AA123456)"
                )
            else:
                issues.append(
                    f"Invalid Ukraine passport format. Expected: 2 letters + 6 digits (e.g., AA123456), "
                    f"Got: {document_number}"
                )
        else:
            details["passport_number_valid"] = True
            details["passport_prefix"] = clean_number[:2]

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

        # Check 4: Validity period (10 years for adults 18+, 4 years for minors)
        details["checks_performed"].append("validity_period")
        if issue_date_str and expiry_date:
            issue_date = self._parse_date(issue_date_str)
            exp = self._parse_date(expiry_date)
            if issue_date and exp:
                validity_days = (exp - issue_date).days
                validity_years = validity_days / 365.25
                details["validity_years"] = round(validity_years, 1)

                # Check validity based on age at issue
                if age_at_issue is not None:
                    if age_at_issue < 18:
                        # Minors: 4-year validity
                        if not (3.5 <= validity_years <= 4.5):
                            warnings.append(
                                f"Passport has {validity_years:.1f} year validity. "
                                f"Ukraine passports for minors (under 18) are typically valid for 4 years."
                            )
                        else:
                            details["validity_valid"] = True
                    else:
                        # Adults: 10-year validity
                        if not (9.5 <= validity_years <= 10.5):
                            warnings.append(
                                f"Passport has {validity_years:.1f} year validity. "
                                f"Ukraine passports for adults (18+) are typically valid for 10 years."
                            )
                        else:
                            details["validity_valid"] = True
                else:
                    # No age info, check for either 4 or 10 year validity
                    if not (3.5 <= validity_years <= 4.5) and not (9.5 <= validity_years <= 10.5):
                        warnings.append(
                            f"Passport has {validity_years:.1f} year validity. "
                            f"Ukraine passports are typically 4 years (minors) or 10 years (adults)."
                        )
                    else:
                        details["validity_valid"] = True

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
                message=f"Ukraine Passport validation failed: {'; '.join(issues)}",
                details={**details, "issues": issues, "warnings": warnings},
                execution_time_ms=execution_time
            )
        elif warnings:
            return self._create_result(
                status=ValidationStatus.WARNING,
                message="Ukraine Passport validation passed with warnings",
                details={**details, "warnings": warnings},
                execution_time_ms=execution_time
            )
        else:
            return self._create_result(
                status=ValidationStatus.PASSED,
                message="Ukraine Passport validation passed",
                details=details,
                execution_time_ms=execution_time
            )
