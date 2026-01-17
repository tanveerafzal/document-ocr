import re
import time
from datetime import datetime
from typing import Dict, Any
from app.services.validators.base import BaseValidator
from app.models.responses import ValidatorResult, ValidationStatus


class ChinaPassportValidator(BaseValidator):
    """
    Validate China Passport specific requirements.

    China Passport specifics:
    - Passport number format:
      - E + 8 digits for ordinary passport (e.g., E12345678)
      - G + 8 digits for official passport
      - D + 8 digits for diplomatic passport
    - MRZ country code: CHN
    - Validity period: 10 years for adults (16+), 5 years for minors
    - Issue date must be after date of birth
    """

    name = "china_passport"
    COUNTRY_CODE = "CHN"

    async def validate(self, document_data: Dict[str, Any]) -> ValidatorResult:
        start_time = time.perf_counter()

        issues = []
        warnings = []
        details = {"checks_performed": [], "country": "China", "country_code": self.COUNTRY_CODE}

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

        # Check 2: Passport number format (E/G/D + 8 digits)
        details["checks_performed"].append("passport_number_format")
        clean_number = re.sub(r"[\s\-]", "", document_number.strip().upper())

        # China passport: E (ordinary), G (official), D (diplomatic) + 8 digits
        china_passport_format = r"^[EGD]\d{8}$"

        if not clean_number:
            issues.append("Missing passport number")
        elif not re.match(china_passport_format, clean_number):
            if len(clean_number) == 9 and clean_number[0] in "EGD":
                warnings.append(
                    f"Passport number '{document_number}' may have format issues. "
                    "China passport: E/G/D + 8 digits (e.g., E12345678)"
                )
            else:
                issues.append(
                    f"Invalid China passport format. Expected: E/G/D + 8 digits (e.g., E12345678), "
                    f"Got: {document_number}"
                )
        else:
            details["passport_number_valid"] = True
            prefix = clean_number[0]
            details["passport_prefix"] = prefix
            if prefix == "E":
                details["passport_type"] = "Ordinary"
            elif prefix == "G":
                details["passport_type"] = "Official"
            elif prefix == "D":
                details["passport_type"] = "Diplomatic"

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

        # Check 4: Validity period (5 years for minors under 16, 10 years for adults)
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
                    if age_at_issue < 16:
                        # Minors: 5-year validity
                        if not (4.5 <= validity_years <= 5.5):
                            warnings.append(
                                f"Passport has {validity_years:.1f} year validity. "
                                f"China passports for minors (under 16) are typically valid for 5 years."
                            )
                        else:
                            details["validity_valid"] = True
                    else:
                        # Adults: 10-year validity
                        if not (9.5 <= validity_years <= 10.5):
                            warnings.append(
                                f"Passport has {validity_years:.1f} year validity. "
                                f"China passports for adults (16+) are typically valid for 10 years."
                            )
                        else:
                            details["validity_valid"] = True
                else:
                    # No age info, check for either 5 or 10 year validity
                    if not (4.5 <= validity_years <= 5.5) and not (9.5 <= validity_years <= 10.5):
                        warnings.append(
                            f"Passport has {validity_years:.1f} year validity. "
                            f"China passports are typically 5 years (minors) or 10 years (adults)."
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
                message=f"China Passport validation failed: {'; '.join(issues)}",
                details={**details, "issues": issues, "warnings": warnings},
                execution_time_ms=execution_time
            )
        elif warnings:
            return self._create_result(
                status=ValidationStatus.WARNING,
                message="China Passport validation passed with warnings",
                details={**details, "warnings": warnings},
                execution_time_ms=execution_time
            )
        else:
            return self._create_result(
                status=ValidationStatus.PASSED,
                message="China Passport validation passed",
                details=details,
                execution_time_ms=execution_time
            )
