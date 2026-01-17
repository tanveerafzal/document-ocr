import re
import time
from datetime import datetime
from typing import Dict, Any, Tuple
from app.services.validators.base import BaseValidator
from app.models.responses import ValidatorResult, ValidationStatus


class TexasDriversLicenseValidator(BaseValidator):
    """
    Validate Texas Driver's License.

    Texas DL specifics:
    - Format: 8 digits (e.g., 12345678)
    - Minimum age: 16 for learner's permit, 18 for full license
    - Validity: 6 years for most adults (8 years for those 85+)
    - Expires on birthday
    - Issued by Texas Department of Public Safety (DPS)
    """

    name = "texas_drivers_license"

    def _extract_last_name(self, document_data: Dict[str, Any]) -> Tuple[str, str]:
        """Extract last name from document data."""
        last_name = document_data.get("last_name", "") or ""
        if last_name:
            return last_name.strip(), "last_name_field"

        full_name = document_data.get("full_name", "") or ""
        if full_name and "," in full_name:
            parts = full_name.split(",", 1)
            return parts[0].strip(), "full_name_parsed"

        if full_name:
            parts = full_name.strip().split()
            if len(parts) >= 2:
                return parts[-1].strip(), "full_name_last_word"

        return "", "not_found"

    async def validate(self, document_data: Dict[str, Any]) -> ValidatorResult:
        start_time = time.perf_counter()

        issues = []
        warnings = []
        details = {"checks_performed": [], "state": "Texas"}

        document_number = document_data.get("document_number", "") or ""
        date_of_birth = document_data.get("date_of_birth")
        expiry_date = document_data.get("expiry_date")
        issue_date_str = document_data.get("issue_date")

        clean_number = re.sub(r"[\s\-]", "", document_number).upper()
        details["license_number"] = clean_number

        # Check 1: License number format (8 digits)
        details["checks_performed"].append("license_number_format")
        tx_format = r"^\d{8}$"

        if not clean_number:
            issues.append("Missing license number")
        elif not re.match(tx_format, clean_number):
            issues.append(
                f"Invalid Texas DL format. Expected: 8 digits (e.g., 12345678), "
                f"Got: {document_number}"
            )
        else:
            details["format_valid"] = True

        # Check 2: Age verification
        details["checks_performed"].append("age_check")
        if date_of_birth:
            dob = self._parse_date(date_of_birth)
            if dob:
                today = datetime.now()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                details["current_age"] = age
                details["date_of_birth"] = dob.strftime("%Y-%m-%d")

                if age < 16:
                    issues.append(f"Person is {age} years old. Minimum age for Texas learner's permit is 16")
                elif age < 18:
                    warnings.append(f"Person is {age}. Provisional license restrictions may apply")

        # Check 3: Expiry check
        details["checks_performed"].append("expiry_check")
        if expiry_date:
            exp = self._parse_date(expiry_date)
            if exp:
                today = datetime.now()
                if exp < today:
                    days_expired = (today - exp).days
                    issues.append(f"Texas DL expired {days_expired} days ago")
                else:
                    days_until_expiry = (exp - today).days
                    details["days_until_expiry"] = days_until_expiry
                    if days_until_expiry < 30:
                        warnings.append(f"Texas DL expires in {days_until_expiry} days")
                    elif days_until_expiry < 60:
                        warnings.append(f"Texas DL expires soon ({days_until_expiry} days)")

        # Check 4: Expiry on birthday (Texas DLs typically expire on birthday)
        details["checks_performed"].append("expiry_on_birthday")
        if date_of_birth and expiry_date:
            dob = self._parse_date(date_of_birth)
            exp = self._parse_date(expiry_date)
            if dob and exp:
                if dob.month == exp.month and dob.day == exp.day:
                    details["expires_on_birthday"] = True
                else:
                    details["expires_on_birthday"] = False
                    warnings.append(
                        f"Texas DL typically expires on birthday. "
                        f"DOB: {dob.strftime('%m/%d')}, Expiry: {exp.strftime('%m/%d')}"
                    )

        # Check 5: Validity period (typically 6 years, 8 years for 85+)
        details["checks_performed"].append("validity_period")
        if issue_date_str and expiry_date:
            issue_date = self._parse_date(issue_date_str)
            exp = self._parse_date(expiry_date)
            if issue_date and exp:
                validity_days = (exp - issue_date).days
                validity_years = validity_days / 365.25
                details["validity_years"] = round(validity_years, 1)

                # Texas standard validity is 6 years (8 years for 85+)
                if validity_years < 5:
                    warnings.append(f"Short validity period ({validity_years:.1f} years). Standard is 6 years")
                elif validity_years > 8.5:
                    warnings.append(f"Long validity period ({validity_years:.1f} years). Standard is 6-8 years")

        execution_time = (time.perf_counter() - start_time) * 1000

        if issues:
            return self._create_result(
                status=ValidationStatus.FAILED,
                message=f"Texas DL validation failed: {'; '.join(issues)}",
                details={**details, "issues": issues, "warnings": warnings},
                execution_time_ms=execution_time
            )
        elif warnings:
            return self._create_result(
                status=ValidationStatus.WARNING,
                message="Texas DL validation passed with warnings",
                details={**details, "warnings": warnings},
                execution_time_ms=execution_time
            )
        else:
            return self._create_result(
                status=ValidationStatus.PASSED,
                message="Texas DL validation passed",
                details=details,
                execution_time_ms=execution_time
            )
