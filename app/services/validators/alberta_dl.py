import re
import time
from datetime import datetime
from typing import Dict, Any, Tuple
from app.services.validators.base import BaseValidator
from app.models.responses import ValidatorResult, ValidationStatus


class AlbertaDriversLicenseValidator(BaseValidator):
    """
    Validate Alberta Driver's Licence specific requirements.

    Alberta DL specifics:
    - Licence number format: 9 digits, often shown as XXXXXX-XXX (e.g., 123456-789)
    - Name format on licence: "LASTNAME, FIRSTNAME" or "LASTNAME FIRSTNAME"
    - Licence classes: Class 7 Learner (GDL), Class 5 GDL, Class 5 (full)
    - Minimum age: 14 for Class 7 Learner, 16 for Class 5 GDL
    - Expiry is typically on the holder's birthday
    - Validity period: 5 years for most licences
    - GDL (Graduated Driver Licensing) program applies to new drivers
    """

    name = "alberta_drivers_license"

    def _extract_last_name(self, document_data: Dict[str, Any]) -> Tuple[str, str]:
        """
        Extract last name from document data.

        Alberta DL uses "LASTNAME FIRSTNAME" or "LASTNAME, FIRSTNAME" format.
        Returns tuple of (last_name, source) where source indicates where it came from.
        """
        full_name = document_data.get("full_name", "") or ""

        if full_name:
            # Check for comma format: "LASTNAME, FIRSTNAME"
            if "," in full_name:
                parts = full_name.split(",", 1)
                last_name = parts[0].strip()
                if last_name:
                    return last_name, "full_name_comma_format"
            else:
                # No comma: "LASTNAME FIRSTNAME" - FIRST word is last name
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
        issue_date_str = document_data.get("issue_date")

        # Check 1: Licence number format (9 digits, may have hyphen: XXXXXX-XXX)
        details["checks_performed"].append("licence_number_format")
        raw_number = document_number.strip().upper()

        # Remove hyphens and spaces
        clean_number = re.sub(r"[\s\-]", "", raw_number)

        # Alberta format: 9 digits
        alberta_format = r"^\d{9}$"

        if not clean_number:
            issues.append("Missing licence number")
        elif re.match(alberta_format, clean_number):
            details["licence_number_valid"] = True
            details["licence_digits"] = 9
        elif clean_number.isdigit() and 8 <= len(clean_number) <= 10:
            warnings.append(
                f"Licence number '{document_number}' has {len(clean_number)} digits. "
                "Alberta licence typically has 9 digits (XXXXXX-XXX)."
            )
            details["licence_digits"] = len(clean_number)
        else:
            issues.append(
                f"Invalid Alberta licence format. Expected: 9 digits (e.g., 123456-789), "
                f"Got: {document_number}"
            )

        details["clean_licence_number"] = clean_number

        # Check 2: Minimum age for Alberta DL (14 for Class 7 Learner)
        details["checks_performed"].append("minimum_age_alberta")
        if date_of_birth:
            dob = self._parse_date(date_of_birth)
            if dob:
                today = datetime.now()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                details["calculated_age"] = age

                if age < 14:
                    issues.append(
                        f"Person is {age} years old. Alberta requires minimum 14 for Class 7 Learner"
                    )
                elif age < 16:
                    warnings.append(
                        f"Person is {age}. Can only hold Class 7 Learner (GDL) licence"
                    )
                elif age < 18:
                    warnings.append(
                        f"Person is {age}. Likely holds Class 5 GDL (probationary) licence"
                    )

        # Check 3: Expiry date validation (Alberta DL expires on birthday)
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
                        f"({dob.strftime('%m-%d')}). Alberta DL typically expires on holder's birthday"
                    )

        # Check 4: Licence validity period (typically 5 years)
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
                        "May be a learner or probationary licence."
                    )
                elif validity_years > 6:
                    warnings.append(
                        f"Validity period ({validity_years:.1f} years) exceeds typical "
                        "5-year Alberta licence term"
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
                        if age_at_issue < 14:
                            issues.append(
                                f"Person was {age_at_issue} at issue date. "
                                "Alberta requires minimum 14 for any licence"
                            )

        execution_time = (time.perf_counter() - start_time) * 1000

        # Determine result status
        if issues:
            return self._create_result(
                status=ValidationStatus.FAILED,
                message=f"Alberta Driver's Licence validation failed: {'; '.join(issues)}",
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
                message="Alberta Driver's Licence validation passed with warnings",
                details={
                    **details,
                    "warnings": warnings
                },
                execution_time_ms=execution_time
            )
        else:
            return self._create_result(
                status=ValidationStatus.PASSED,
                message="Alberta Driver's Licence validation passed",
                details=details,
                execution_time_ms=execution_time
            )
