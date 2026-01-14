import re
import time
from datetime import datetime
from typing import Dict, Any
from app.services.validators.base import BaseValidator
from app.models.responses import ValidatorResult, ValidationStatus


class OntarioDriversLicenseValidator(BaseValidator):
    """
    Validate Ontario Driver's License specific requirements.

    Ontario DL specifics:
    - License number format: Letter + 4 digits + hyphen + 5 digits + hyphen + 5 digits
      Example: A1234-12345-12345
    - First letter corresponds to first letter of last name
    - License classes: G1, G2, G, M1, M2, M, etc.
    - Expiry is typically on the holder's birthday
    - Minimum age for G1: 16, G2: 17 (after 12 months), G: 18 (after 12 months)
    """

    name = "ontario_drivers_license"

    async def validate(self, document_data: Dict[str, Any]) -> ValidatorResult:
        start_time = time.perf_counter()

        issues = []
        warnings = []
        details = {"checks_performed": []}

        document_number = document_data.get("document_number", "") or ""
        last_name = document_data.get("last_name", "") or ""
        date_of_birth = document_data.get("date_of_birth")
        expiry_date = document_data.get("expiry_date")

        # Check 1: License number format
        details["checks_performed"].append("license_number_format")
        clean_number = document_number.strip().upper()
        ontario_format = r"^[A-Z]\d{4}-\d{5}-\d{5}$"

        if not clean_number:
            issues.append("Missing license number")
        elif not re.match(ontario_format, clean_number):
            # Try without hyphens
            clean_number_no_hyphen = re.sub(r"[-\s]", "", clean_number)
            if len(clean_number_no_hyphen) == 15 and clean_number_no_hyphen[0].isalpha():
                warnings.append(f"License number format non-standard but may be valid: {document_number}")
            else:
                issues.append(f"Invalid Ontario DL format. Expected: A1234-12345-12345, Got: {document_number}")
        else:
            details["license_number_valid"] = True

        # Check 2: First letter matches last name
        details["checks_performed"].append("first_letter_match")
        if clean_number and last_name:
            license_letter = clean_number[0].upper()
            last_name_letter = last_name[0].upper()
            if license_letter != last_name_letter:
                issues.append(
                    f"License first letter '{license_letter}' does not match "
                    f"last name initial '{last_name_letter}'"
                )
            else:
                details["first_letter_matches"] = True

        # Check 3: Minimum age for Ontario DL (16 for G1)
        details["checks_performed"].append("minimum_age_ontario")
        if date_of_birth:
            dob = self._parse_date(date_of_birth)
            if dob:
                today = datetime.now()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                details["calculated_age"] = age
                if age < 16:
                    issues.append(f"Person is {age} years old. Ontario requires minimum 16 for G1 license")
                elif age < 18:
                    warnings.append(f"Person is {age}. May only hold G1/G2 license (full G requires 18+)")

        # Check 4: Expiry date validation (Ontario DL expires on birthday)
        details["checks_performed"].append("expiry_on_birthday")
        if date_of_birth and expiry_date:
            dob = self._parse_date(date_of_birth)
            exp = self._parse_date(expiry_date)
            if dob and exp:
                # Check if expiry is on birthday (same month and day)
                if dob.month == exp.month and dob.day == exp.day:
                    details["expiry_on_birthday"] = True
                else:
                    warnings.append(
                        f"Expiry date ({exp.strftime('%m-%d')}) is not on birthday ({dob.strftime('%m-%d')}). "
                        "Ontario DL typically expires on holder's birthday"
                    )

        # Check 5: License validity period (Ontario DL valid for 5 years typically)
        details["checks_performed"].append("validity_period")
        issue_date_str = document_data.get("issue_date")
        if issue_date_str and expiry_date:
            issue_date = self._parse_date(issue_date_str)
            exp = self._parse_date(expiry_date)
            if issue_date and exp:
                validity_years = (exp - issue_date).days / 365
                details["validity_years"] = round(validity_years, 1)
                if validity_years > 6:
                    warnings.append(f"Validity period ({validity_years:.1f} years) exceeds typical 5-year Ontario DL term")

        # Check 6: Last 6 digits of license number match DOB in YYMMDD format
        details["checks_performed"].append("dob_encoded_in_license")
        if clean_number and date_of_birth:
            dob = self._parse_date(date_of_birth)
            if dob:
                # Extract last 6 digits from license number (remove hyphens/spaces first)
                clean_number_no_hyphen = re.sub(r"[-\s]", "", clean_number)
                last_6_digits = clean_number_no_hyphen[-6:]

                # Format DOB as YYMMDD
                expected_dob = dob.strftime("%y%m%d")
                details["license_last_6"] = last_6_digits
                details["expected_dob_yymmdd"] = expected_dob

                if last_6_digits == expected_dob:
                    details["dob_encoded_in_license"] = True
                else:
                    issues.append(
                        f"Last 6 digits of license '{last_6_digits}' do not match "
                        f"DOB in YYMMDD format '{expected_dob}'"
                    )

        execution_time = (time.perf_counter() - start_time) * 1000

        # Determine result status
        if issues:
            return self._create_result(
                status=ValidationStatus.FAILED,
                message=f"Ontario DL validation failed: {'; '.join(issues)}",
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
                message=f"Ontario DL validation passed with warnings",
                details={
                    **details,
                    "warnings": warnings
                },
                execution_time_ms=execution_time
            )
        else:
            return self._create_result(
                status=ValidationStatus.PASSED,
                message="Ontario Driver's License validation passed",
                details=details,
                execution_time_ms=execution_time
            )
