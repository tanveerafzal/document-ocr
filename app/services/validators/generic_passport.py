import re
import time
from datetime import datetime
from typing import Dict, Any
from app.services.validators.base import BaseValidator
from app.models.responses import ValidatorResult, ValidationStatus
from app.models.document_types import COUNTRY_CODES


class GenericPassportValidator(BaseValidator):
    """
    Validate international passports based on country code.

    This validator handles passports from any country that doesn't have
    a specific validator implemented. It performs basic validation:
    - Country code verification against known ISO 3166-1 alpha-3 codes
    - Document number format (alphanumeric, 6-12 characters)
    - Date validations (issue date, expiry date)
    - Standard validity period checks (typically 5-10 years)
    """

    name = "generic_passport"

    async def validate(self, document_data: Dict[str, Any]) -> ValidatorResult:
        start_time = time.perf_counter()

        issues = []
        warnings = []
        details = {"checks_performed": []}

        document_number = document_data.get("document_number", "") or ""
        date_of_birth = document_data.get("date_of_birth")
        issue_date_str = document_data.get("issue_date")
        expiry_date = document_data.get("expiry_date")
        country_code = (document_data.get("country_code", "") or "").upper()

        # Check 1: Country code verification
        details["checks_performed"].append("country_code_check")
        if country_code:
            if country_code in COUNTRY_CODES:
                details["country_code"] = country_code
                details["country"] = COUNTRY_CODES[country_code]
                details["country_code_valid"] = True
            else:
                warnings.append(
                    f"Country code '{country_code}' is not a recognized ISO 3166-1 alpha-3 code"
                )
                details["country_code"] = country_code
                details["country_code_valid"] = False
        else:
            warnings.append("No country code found on passport")

        # Check 2: Passport number format (generic: alphanumeric, 6-12 characters)
        details["checks_performed"].append("passport_number_format")
        clean_number = re.sub(r"[\s\-]", "", document_number.strip().upper())

        # Generic passport format: alphanumeric, 6-12 characters
        generic_passport_format = r"^[A-Z0-9]{6,12}$"

        if not clean_number:
            issues.append("Missing passport number")
        elif not re.match(generic_passport_format, clean_number):
            if len(clean_number) < 6:
                warnings.append(
                    f"Passport number '{document_number}' seems too short. "
                    "Most passports have 6-12 alphanumeric characters."
                )
            elif len(clean_number) > 12:
                warnings.append(
                    f"Passport number '{document_number}' seems too long. "
                    "Most passports have 6-12 alphanumeric characters."
                )
            else:
                warnings.append(
                    f"Passport number '{document_number}' may have format issues."
                )
        else:
            details["passport_number_valid"] = True
            details["passport_number_length"] = len(clean_number)

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

        # Check 4: Validity period (typically 5-10 years for most countries)
        details["checks_performed"].append("validity_period")
        if issue_date_str and expiry_date:
            issue_date = self._parse_date(issue_date_str)
            exp = self._parse_date(expiry_date)
            if issue_date and exp:
                validity_days = (exp - issue_date).days
                validity_years = validity_days / 365.25
                details["validity_years"] = round(validity_years, 1)

                # Most passports are valid for 5-10 years
                if validity_years < 1:
                    warnings.append(
                        f"Passport has very short validity ({validity_years:.1f} years). "
                        "This may indicate an issue."
                    )
                elif validity_years > 12:
                    warnings.append(
                        f"Passport has unusually long validity ({validity_years:.1f} years). "
                        "Most passports are valid for 5-10 years."
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

        # Build result message
        country_name = details.get("country", "International")

        if issues:
            return self._create_result(
                status=ValidationStatus.FAILED,
                message=f"{country_name} Passport validation failed: {'; '.join(issues)}",
                details={**details, "issues": issues, "warnings": warnings},
                execution_time_ms=execution_time
            )
        elif warnings:
            return self._create_result(
                status=ValidationStatus.WARNING,
                message=f"{country_name} Passport validation passed with warnings",
                details={**details, "warnings": warnings},
                execution_time_ms=execution_time
            )
        else:
            return self._create_result(
                status=ValidationStatus.PASSED,
                message=f"{country_name} Passport validation passed",
                details=details,
                execution_time_ms=execution_time
            )
