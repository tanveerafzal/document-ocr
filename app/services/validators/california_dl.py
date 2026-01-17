import re
import time
from datetime import datetime
from typing import Dict, Any, Tuple
from app.services.validators.base import BaseValidator
from app.models.responses import ValidatorResult, ValidationStatus


class CaliforniaDriversLicenseValidator(BaseValidator):
    """
    Validate California Driver's License.

    California DL specifics:
    - Format: 1 letter + 7 digits (e.g., A1234567)
    - First letter typically corresponds to last name initial
    - Minimum age: 16 for learner's permit, 18 for full license
    - Validity: 5 years for most adults
    - REAL ID compliant cards have a gold star
    """

    name = "california_drivers_license"

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
        details = {"checks_performed": [], "state": "California"}

        document_number = document_data.get("document_number", "") or ""
        last_name, name_source = self._extract_last_name(document_data)
        date_of_birth = document_data.get("date_of_birth")
        expiry_date = document_data.get("expiry_date")
        issue_date_str = document_data.get("issue_date")

        clean_number = re.sub(r"[\s\-]", "", document_number).upper()
        details["license_number"] = clean_number

        # Check 1: License number format (1 letter + 7 digits)
        details["checks_performed"].append("license_number_format")
        ca_format = r"^[A-Z]\d{7}$"

        if not clean_number:
            issues.append("Missing license number")
        elif not re.match(ca_format, clean_number):
            issues.append(
                f"Invalid California DL format. Expected: 1 letter + 7 digits (e.g., A1234567), "
                f"Got: {document_number}"
            )
        else:
            details["format_valid"] = True

        # Check 2: First letter matches last name initial
        details["checks_performed"].append("first_letter_check")
        if clean_number and len(clean_number) > 0 and clean_number[0].isalpha() and last_name:
            license_letter = clean_number[0].upper()
            last_name_letter = last_name[0].upper()
            details["license_first_letter"] = license_letter
            details["last_name_initial"] = last_name_letter
            details["name_extraction_source"] = name_source

            if license_letter != last_name_letter:
                warnings.append(
                    f"License first letter '{license_letter}' doesn't match "
                    f"last name initial '{last_name_letter}'"
                )
            else:
                details["first_letter_matches"] = True

        # Check 3: Age verification
        details["checks_performed"].append("age_check")
        if date_of_birth:
            dob = self._parse_date(date_of_birth)
            if dob:
                today = datetime.now()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                details["current_age"] = age
                details["date_of_birth"] = dob.strftime("%Y-%m-%d")

                if age < 16:
                    issues.append(f"Person is {age} years old. Minimum age for California learner's permit is 16")
                elif age < 18:
                    warnings.append(f"Person is {age}. Provisional license restrictions may apply")

        # Check 4: Expiry check
        details["checks_performed"].append("expiry_check")
        if expiry_date:
            exp = self._parse_date(expiry_date)
            if exp:
                today = datetime.now()
                if exp < today:
                    days_expired = (today - exp).days
                    issues.append(f"California DL expired {days_expired} days ago")
                else:
                    days_until_expiry = (exp - today).days
                    details["days_until_expiry"] = days_until_expiry
                    if days_until_expiry < 30:
                        warnings.append(f"California DL expires in {days_until_expiry} days")
                    elif days_until_expiry < 60:
                        warnings.append(f"California DL expires soon ({days_until_expiry} days)")

        # Check 5: Expiry on birthday (California DLs typically expire on birthday)
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
                        f"California DL typically expires on birthday. "
                        f"DOB: {dob.strftime('%m/%d')}, Expiry: {exp.strftime('%m/%d')}"
                    )

        # Check 6: Validity period (typically 5 years for adults under 70)
        details["checks_performed"].append("validity_period")
        if issue_date_str and expiry_date:
            issue_date = self._parse_date(issue_date_str)
            exp = self._parse_date(expiry_date)
            if issue_date and exp:
                validity_days = (exp - issue_date).days
                validity_years = validity_days / 365.25
                details["validity_years"] = round(validity_years, 1)

                # California standard validity is 5 years
                if validity_years < 4:
                    warnings.append(f"Short validity period ({validity_years:.1f} years). Standard is 5 years")
                elif validity_years > 6:
                    warnings.append(f"Long validity period ({validity_years:.1f} years). Standard is 5 years")

        execution_time = (time.perf_counter() - start_time) * 1000

        if issues:
            return self._create_result(
                status=ValidationStatus.FAILED,
                message=f"California DL validation failed: {'; '.join(issues)}",
                details={**details, "issues": issues, "warnings": warnings},
                execution_time_ms=execution_time
            )
        elif warnings:
            return self._create_result(
                status=ValidationStatus.WARNING,
                message="California DL validation passed with warnings",
                details={**details, "warnings": warnings},
                execution_time_ms=execution_time
            )
        else:
            return self._create_result(
                status=ValidationStatus.PASSED,
                message="California DL validation passed",
                details=details,
                execution_time_ms=execution_time
            )
