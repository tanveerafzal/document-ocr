import re
import time
from datetime import datetime
from typing import Dict, Any, Tuple
from app.services.validators.base import BaseValidator
from app.models.responses import ValidatorResult, ValidationStatus
from app.services.verifik_client import verifik_client, VerifikValidationStatus


class BCDriversLicenseValidator(BaseValidator):
    """
    Validate British Columbia Driver's Licence specific requirements.

    BC DL specifics:
    - Licence number format: "DL:" or "NDL:" prefix + 7 digits (e.g., DL:1234567 or NDL:1234567)
    - May also appear as just 7 digits without prefix
    - "NDL:" prefix indicates BC Driver's Licence (N = Novice or New)
    - Name format on licence: "LASTNAME FIRSTNAME" or "LASTNAME, FIRSTNAME"
    - Licence classes: Class 7L (Learner), Class 7 (Novice/N), Class 5 (Full)
    - Minimum age: 16 for Class 7L, must hold 7L for 12 months before Class 7
    - Expiry is typically on the holder's birthday
    - Validity period: 5 years for most licences, 2 years for new drivers
    """

    name = "bc_drivers_license"

    def _extract_last_name(self, document_data: Dict[str, Any]) -> Tuple[str, str]:
        """
        Extract last name from document data.

        BC DL uses "LASTNAME, FIRSTNAME MIDDLENAME" format.
        Returns tuple of (last_name, source) where source indicates where it came from.
        """
        # For BC DL, prioritize full_name in "LASTNAME, FIRSTNAME" format
        full_name = document_data.get("full_name", "") or ""
        if full_name and "," in full_name:
            parts = full_name.split(",", 1)
            last_name = parts[0].strip()
            if last_name:
                return last_name, "full_name_parsed"

        # Fall back to dedicated last_name field
        last_name = document_data.get("last_name", "") or ""
        if last_name:
            return last_name.strip(), "last_name_field"

        # Try full_name without comma
        if full_name:
            parts = full_name.strip().split()
            if len(parts) >= 2:
                return parts[-1].strip(), "full_name_last_word"

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
        issue_date_str = document_data.get("issue_date")

        # Check 1: Licence number format (DL:XXXXXXX, NDL:XXXXXXX, or 7 digits)
        details["checks_performed"].append("licence_number_format")
        raw_number = document_number.strip().upper()

        # Remove "NDL:" or "DL:" prefix if present
        if raw_number.startswith("NDL:"):
            clean_number = raw_number[4:].strip()
            details["has_ndl_prefix"] = True
            details["prefix_type"] = "NDL"
        elif raw_number.startswith("NDL"):
            clean_number = raw_number[3:].strip()
            details["has_ndl_prefix"] = True
            details["prefix_type"] = "NDL"
        elif raw_number.startswith("DL:"):
            clean_number = raw_number[3:].strip()
            details["has_dl_prefix"] = True
            details["prefix_type"] = "DL"
        elif raw_number.startswith("DL"):
            clean_number = raw_number[2:].strip()
            details["has_dl_prefix"] = True
            details["prefix_type"] = "DL"
        else:
            clean_number = re.sub(r"[\s\-]", "", raw_number)
            details["has_dl_prefix"] = False
            details["has_ndl_prefix"] = False

        # BC format: 7 digits
        bc_format_7 = r"^\d{7}$"
        bc_format_6 = r"^\d{6}$"

        if not clean_number:
            issues.append("Missing licence number")
        elif re.match(bc_format_6, clean_number):
            details["licence_number_valid"] = True
            details["licence_digits"] = 6
        elif re.match(bc_format_7, clean_number):
            details["licence_number_valid"] = True
            details["licence_digits"] = 7
        elif clean_number.isdigit() and 5 <= len(clean_number) <= 8:
            warnings.append(
                f"Licence number '{document_number}' has {len(clean_number)} digits. "
                "BC licence typically has 6 digits (DL:XXXXXX) or 7 digits."
            )
            details["licence_digits"] = len(clean_number)
        else:
            issues.append(
                f"Invalid BC licence format. Expected: DL:XXXXXX (6 digits) or 7 digits, "
                f"Got: {document_number}"
            )

        details["clean_licence_number"] = clean_number

        # Check 2: Minimum age for BC DL (16 for Class 7L Learner)
        details["checks_performed"].append("minimum_age_bc")
        if date_of_birth:
            dob = self._parse_date(date_of_birth)
            if dob:
                today = datetime.now()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                details["calculated_age"] = age

                if age < 16:
                    issues.append(
                        f"Person is {age} years old. BC requires minimum 16 for Class 7L (Learner)"
                    )
                elif age < 17:
                    warnings.append(
                        f"Person is {age}. Can only hold Class 7L (Learner) licence"
                    )
                elif age < 19:
                    warnings.append(
                        f"Person is {age}. May hold Class 7 (Novice/N) or Class 7L"
                    )

        # Check 3: Expiry date validation (BC DL expires on birthday)
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
                        f"Expiry date ({exp.strftime('%m-%d')}) is not on birthday "
                        f"({dob.strftime('%m-%d')}). BC DL typically expires on holder's birthday"
                    )

        # Check 4: Licence validity period (typically 5 years, 2 years for new drivers)
        details["checks_performed"].append("validity_period")
        if issue_date_str and expiry_date:
            issue_date = self._parse_date(issue_date_str)
            exp = self._parse_date(expiry_date)
            if issue_date and exp:
                validity_years = (exp - issue_date).days / 365.25
                details["validity_years"] = round(validity_years, 1)

                if validity_years < 1.5:
                    warnings.append(
                        f"Short validity period ({validity_years:.1f} years). "
                        "May be a new driver or restricted licence."
                    )
                elif validity_years > 6:
                    warnings.append(
                        f"Validity period ({validity_years:.1f} years) exceeds typical "
                        "5-year BC licence term"
                    )

        # Check 5: Document not expired
        details["checks_performed"].append("expiry_check")
        if expiry_date:
            exp = self._parse_date(expiry_date)
            if exp:
                today = datetime.now()
                if exp < today:
                    days_expired = (today - exp).days
                    issues.append(f"Licence expired {days_expired} days ago")
                else:
                    days_until_expiry = (exp - today).days
                    details["days_until_expiry"] = days_until_expiry
                    if days_until_expiry < 30:
                        warnings.append(f"Licence expires in {days_until_expiry} days")

        # Check 6: Issue date reasonability
        details["checks_performed"].append("issue_date_check")
        if issue_date_str:
            issue_date = self._parse_date(issue_date_str)
            if issue_date:
                today = datetime.now()
                if issue_date > today:
                    issues.append("Issue date cannot be in the future")
                elif date_of_birth:
                    dob = self._parse_date(date_of_birth)
                    if dob and issue_date < dob:
                        issues.append("Issue date cannot be before date of birth")
                    elif dob:
                        age_at_issue = issue_date.year - dob.year - (
                            (issue_date.month, issue_date.day) < (dob.month, dob.day)
                        )
                        details["age_at_issue"] = age_at_issue
                        if age_at_issue < 16:
                            issues.append(
                                f"Person was {age_at_issue} at issue date. "
                                "BC requires minimum 16 for any licence"
                            )

        # Check 7: Verifik API validation (only if no issues so far)
        details["checks_performed"].append("verifik_api_validation")
        verifik_result = None

        if not issues and verifik_client.is_enabled():
            # Last name is mandatory for BC DL Verifik validation
            if not last_name:
                issues.append("Last name is required for BC DL validation via Verifik API")
                details["verifik_api_enabled"] = True
                details["verifik_api_validated"] = False
                details["verifik_api_error"] = "missing_last_name"
            else:
                verifik_result = await verifik_client.validate_bc_dl(clean_number, last_name)
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
                message=f"BC Driver's Licence validation failed: {'; '.join(issues)}",
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
                message="BC Driver's Licence validation passed with warnings",
                details={
                    **details,
                    "warnings": warnings
                },
                execution_time_ms=execution_time
            )
        else:
            return self._create_result(
                status=ValidationStatus.PASSED,
                message="BC Driver's Licence validation passed",
                details=details,
                execution_time_ms=execution_time
            )
