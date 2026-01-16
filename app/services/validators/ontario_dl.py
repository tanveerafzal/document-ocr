import re
import time
from datetime import datetime
from typing import Dict, Any
from app.services.validators.base import BaseValidator
from app.models.responses import ValidatorResult, ValidationStatus
from app.services.verifik_client import verifik_client, VerifikValidationStatus


class OntarioDriversLicenseValidator(BaseValidator):
    """
    Validate Ontario Driver's License specific requirements.

    Ontario DL specifics:
    - License number format: Letter + 4 digits + hyphen + 5 digits + hyphen + 5 digits
      Example: A1234-12345-12345
    - First letter corresponds to first letter of last name
    - Name format on license: "LASTNAME, FIRSTNAME"
    - License classes: G1, G2, G, M1, M2, M, etc.
    - Expiry is typically on the holder's birthday
    - Last 6 digits encode DOB in YYMMDD format
      - For female license holders, 50 is added to the month (e.g., June/06 becomes 56)
    - Minimum age for G1: 16, G2: 17 (after 12 months), G: 18 (after 12 months)
    """

    name = "ontario_drivers_license"

    def _extract_last_name(self, document_data: Dict[str, Any]) -> tuple[str, str]:
        """
        Extract last name from document data.

        Ontario DL uses "LASTNAME FIRSTNAME" or "LASTNAME, FIRSTNAME" format.
        The FIRST word is always the LAST NAME on Ontario DL.
        The first letter of the license number MUST match the last name.

        Returns tuple of (last_name, source) where source indicates where it came from.
        """
        # For Ontario DL, prioritize full_name since it shows the authoritative format
        full_name = document_data.get("full_name", "") or ""

        if full_name:
            # Check for comma format: "LASTNAME, FIRSTNAME"
            if "," in full_name:
                parts = full_name.split(",", 1)
                last_name = parts[0].strip()
                if last_name:
                    return last_name, "full_name_comma_format"
            else:
                # No comma: "LASTNAME FIRSTNAME" - FIRST word is last name on Ontario DL
                parts = full_name.strip().split()
                if len(parts) >= 1:
                    return parts[0].strip(), "full_name_first_word"

        # Fall back to dedicated last_name field
        last_name = document_data.get("last_name", "") or ""
        if last_name:
            return last_name.strip(), "last_name_field"

        return "", "not_found"

    async def validate(self, document_data: Dict[str, Any]) -> ValidatorResult:
        start_time = time.perf_counter()

        issues = []
        warnings = []
        details = {"checks_performed": []}

        document_number = document_data.get("document_number", "") or ""
        last_name, name_source = self._extract_last_name(document_data)
        details["last_name_source"] = name_source
        if last_name:
            details["extracted_last_name"] = last_name
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

        # Check 2: First letter of license number matches last name initial
        details["checks_performed"].append("first_letter_match")
        if clean_number:
            license_letter = clean_number[0].upper()
            details["license_first_letter"] = license_letter

            if last_name:
                last_name_letter = last_name[0].upper()
                details["last_name_initial"] = last_name_letter

                if license_letter != last_name_letter:
                    issues.append(
                        f"License first letter '{license_letter}' does not match "
                        f"last name initial '{last_name_letter}' (from {name_source})"
                    )
                else:
                    details["first_letter_matches"] = True
            else:
                warnings.append(
                    f"Cannot verify license letter '{license_letter}' - no last name found. "
                    "Ontario DL format: 'LASTNAME, FIRSTNAME'"
                )

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
        # For female license holders, 50 is added to the month (e.g., June/06 becomes 56)
        details["checks_performed"].append("dob_encoded_in_license")
        if clean_number and date_of_birth:
            dob = self._parse_date(date_of_birth)
            if dob:
                # Extract last 6 digits from license number (remove hyphens/spaces first)
                clean_number_no_hyphen = re.sub(r"[-\s]", "", clean_number)
                last_6_digits = clean_number_no_hyphen[-6:]

                # Format DOB as YYMMDD (male encoding)
                expected_dob_male = dob.strftime("%y%m%d")
                # Female encoding: add 50 to month (06 -> 56)
                female_month = dob.month + 50
                expected_dob_female = f"{dob.strftime('%y')}{female_month:02d}{dob.strftime('%d')}"

                details["license_last_6"] = last_6_digits
                details["expected_dob_male"] = expected_dob_male
                details["expected_dob_female"] = expected_dob_female

                # Get gender from document if available
                gender = (document_data.get("gender", "") or "").upper().strip()
                details["document_gender"] = gender if gender else "not_provided"

                if last_6_digits == expected_dob_male:
                    details["dob_encoded_in_license"] = True
                    details["detected_encoding"] = "male"
                    # If gender is provided, check consistency
                    if gender and gender in ["F", "FEMALE"]:
                        warnings.append(
                            f"License uses male DOB encoding but gender is '{gender}'. "
                            "Expected female encoding with month +50."
                        )
                elif last_6_digits == expected_dob_female:
                    details["dob_encoded_in_license"] = True
                    details["detected_encoding"] = "female"
                    # If gender is provided, check consistency
                    if gender and gender in ["M", "MALE"]:
                        warnings.append(
                            f"License uses female DOB encoding (month +50) but gender is '{gender}'."
                        )
                else:
                    issues.append(
                        f"Last 6 digits of license '{last_6_digits}' do not match "
                        f"DOB encoding. Expected '{expected_dob_male}' (male) or "
                        f"'{expected_dob_female}' (female with month +50)"
                    )

        # Check 7: Verifik API validation (only if no issues so far)
        details["checks_performed"].append("verifik_api_validation")
        verifik_result = None

        if not issues and verifik_client.is_enabled():
            verifik_result = await verifik_client.validate_ontario_dl(clean_number)
            details["verifik_api_enabled"] = True
            details["verifik_api_status"] = verifik_result.status.value

            if verifik_result.status == VerifikValidationStatus.VALID:
                details["verifik_api_validated"] = True
                if verifik_result.details:
                    details["verifik_api_data"] = verifik_result.details
            elif verifik_result.status == VerifikValidationStatus.INVALID:
                issues.append(f"Verifik API: {verifik_result.message}")
                details["verifik_api_validated"] = False
            elif verifik_result.status == VerifikValidationStatus.ERROR:
                warnings.append(f"Verifik API: {verifik_result.message}")
                details["verifik_api_error"] = verifik_result.message
        else:
            details["verifik_api_enabled"] = verifik_client.is_enabled()
            if issues:
                details["verifik_api_skipped_reason"] = "local_validation_failed"

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
