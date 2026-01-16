import re
import time
from datetime import datetime
from typing import Dict, Any, Tuple
from app.services.validators.base import BaseValidator
from app.models.responses import ValidatorResult, ValidationStatus


class PEIDriversLicenseValidator(BaseValidator):
    """
    Validate Prince Edward Island Driver's Licence specific requirements.

    PEI DL specifics:
    - Licence number format: 1-6 digits (e.g., 123456)
    - Name format on licence: "LASTNAME FIRSTNAME" or "LASTNAME, FIRSTNAME"
    - Licence classes: Class 7 (Learner), Class 5 (Full)
    - Minimum age: 16 for Class 7 Learner
    - Expiry is typically on the holder's birthday
    - Validity period: 3-5 years for most licences
    - Smallest Canadian province by population
    """

    name = "pei_drivers_license"

    def _extract_last_name(self, document_data: Dict[str, Any]) -> Tuple[str, str]:
        """
        Extract last name from document data.

        PEI DL uses "LASTNAME FIRSTNAME" or "LASTNAME, FIRSTNAME" format.
        Returns tuple of (last_name, source) where source indicates where it came from.
        """
        full_name = document_data.get("full_name", "") or ""

        if full_name:
            if "," in full_name:
                parts = full_name.split(",", 1)
                last_name = parts[0].strip()
                if last_name:
                    return last_name, "full_name_comma_format"
            else:
                parts = full_name.strip().split()
                if len(parts) >= 1:
                    return parts[0].strip(), "full_name_first_word"

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

        # Check 1: Licence number format (1-6 digits)
        details["checks_performed"].append("licence_number_format")
        raw_number = document_number.strip().upper()
        clean_number = re.sub(r"[\s\-]", "", raw_number)

        # PEI format: 1-6 digits (smaller population = shorter numbers)
        pei_format = r"^\d{1,6}$"

        if not clean_number:
            issues.append("Missing licence number")
        elif re.match(pei_format, clean_number):
            details["licence_number_valid"] = True
            details["licence_digits"] = len(clean_number)
        elif clean_number.isdigit() and len(clean_number) <= 8:
            warnings.append(
                f"Licence number '{document_number}' has {len(clean_number)} digits. "
                "PEI licence typically has 1-6 digits."
            )
            details["licence_digits"] = len(clean_number)
        else:
            issues.append(
                f"Invalid PEI licence format. Expected: 1-6 digits, "
                f"Got: {document_number}"
            )

        details["clean_licence_number"] = clean_number

        # Check 2: Minimum age for PEI DL (16 for Class 7 Learner)
        details["checks_performed"].append("minimum_age_pei")
        if date_of_birth:
            dob = self._parse_date(date_of_birth)
            if dob:
                today = datetime.now()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                details["calculated_age"] = age

                if age < 16:
                    issues.append(
                        f"Person is {age} years old. PEI requires minimum 16 for Class 7 Learner"
                    )
                elif age < 17:
                    warnings.append(
                        f"Person is {age}. Holds Class 7 (Learner) licence"
                    )

        # Check 3: Expiry date validation (PEI DL expires on birthday)
        details["checks_performed"].append("expiry_on_birthday")
        if date_of_birth and expiry_date:
            dob = self._parse_date(date_of_birth)
            exp = self._parse_date(expiry_date)
            if dob and exp:
                if dob.month == exp.month and dob.day == exp.day:
                    details["expiry_on_birthday"] = True
                else:
                    warnings.append(
                        f"Expiry date ({exp.strftime('%m-%d')}) is not on birthday "
                        f"({dob.strftime('%m-%d')}). PEI DL typically expires on holder's birthday"
                    )

        # Check 4: Licence validity period (typically 3-5 years in PEI)
        details["checks_performed"].append("validity_period")
        if issue_date_str and expiry_date:
            issue_date = self._parse_date(issue_date_str)
            exp = self._parse_date(expiry_date)
            if issue_date and exp:
                validity_years = (exp - issue_date).days / 365.25
                details["validity_years"] = round(validity_years, 1)

                if validity_years < 1:
                    warnings.append(
                        f"Short validity period ({validity_years:.1f} years). "
                        "May be a learner licence."
                    )
                elif validity_years > 6:
                    warnings.append(
                        f"Validity period ({validity_years:.1f} years) exceeds typical "
                        "5-year PEI licence term"
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
                                "PEI requires minimum 16 for any licence"
                            )

        execution_time = (time.perf_counter() - start_time) * 1000

        if issues:
            return self._create_result(
                status=ValidationStatus.FAILED,
                message=f"PEI Driver's Licence validation failed: {'; '.join(issues)}",
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
                message="PEI Driver's Licence validation passed with warnings",
                details={
                    **details,
                    "warnings": warnings
                },
                execution_time_ms=execution_time
            )
        else:
            return self._create_result(
                status=ValidationStatus.PASSED,
                message="PEI Driver's Licence validation passed",
                details=details,
                execution_time_ms=execution_time
            )
