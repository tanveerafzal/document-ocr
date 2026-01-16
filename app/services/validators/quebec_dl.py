import re
import time
from datetime import datetime
from typing import Dict, Any, Tuple
from app.services.validators.base import BaseValidator
from app.models.responses import ValidatorResult, ValidationStatus


class QuebecDriversLicenseValidator(BaseValidator):
    """
    Validate Quebec Driver's Licence (Permis de conduire) specific requirements.

    Quebec DL specifics:
    - Licence number format: Letter + 12 digits (e.g., S1234-567890-12)
    - First letter corresponds to first letter of last name
    - Name format on licence: "LASTNAME, FIRSTNAME" or "LASTNAME FIRSTNAME"
    - Licence classes: Class 5 (passenger vehicle), Class 6 (motorcycle), etc.
    - Probationary licence for new drivers (24 months)
    - Minimum age: 16 for Class 5 Learner
    - Expiry is typically on the holder's birthday
    - Validity period: 4 years (or 8 years since 2024)
    """

    name = "quebec_drivers_license"

    def _extract_last_name(self, document_data: Dict[str, Any]) -> Tuple[str, str]:
        """
        Extract last name from document data.

        Quebec DL uses "LASTNAME FIRSTNAME" or "LASTNAME, FIRSTNAME" format.
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

        # Check 1: Licence number format (Letter + 12 digits: X1234-567890-12)
        details["checks_performed"].append("licence_number_format")
        raw_number = document_number.strip().upper()

        # Remove hyphens and spaces
        clean_number = re.sub(r"[\s\-]", "", raw_number)

        # Quebec format: Letter + 12 digits = 13 characters total
        quebec_format = r"^[A-Z]\d{12}$"

        if not clean_number:
            issues.append("Missing licence number")
        elif re.match(quebec_format, clean_number):
            details["licence_number_valid"] = True
            details["licence_letter"] = clean_number[0]
        elif len(clean_number) == 13 and clean_number[0].isalpha():
            # Close to valid format
            warnings.append(
                f"Licence number '{document_number}' may have format issues. "
                "Quebec licence: Letter + 12 digits (e.g., S1234-567890-12)"
            )
            details["licence_letter"] = clean_number[0]
        else:
            issues.append(
                f"Invalid Quebec licence format. Expected: Letter + 12 digits (e.g., S1234-567890-12), "
                f"Got: {document_number}"
            )

        details["clean_licence_number"] = clean_number

        # Check 2: First letter matches last name initial
        details["checks_performed"].append("first_letter_match")
        if clean_number and len(clean_number) >= 1 and clean_number[0].isalpha():
            licence_letter = clean_number[0].upper()
            details["licence_first_letter"] = licence_letter

            if last_name:
                last_name_initial = last_name[0].upper()
                details["last_name_initial"] = last_name_initial

                if licence_letter != last_name_initial:
                    issues.append(
                        f"Licence first letter '{licence_letter}' does not match "
                        f"last name initial '{last_name_initial}' (from {name_source})"
                    )
                else:
                    details["first_letter_matches"] = True
            else:
                warnings.append(
                    f"Cannot verify licence letter '{licence_letter}' - no last name found"
                )

        # Check 3: Minimum age for Quebec DL (16 for Class 5 Learner)
        details["checks_performed"].append("minimum_age_quebec")
        if date_of_birth:
            dob = self._parse_date(date_of_birth)
            if dob:
                today = datetime.now()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                details["calculated_age"] = age

                if age < 16:
                    issues.append(
                        f"Person is {age} years old. Quebec requires minimum 16 for Class 5 Learner"
                    )
                elif age < 18:
                    warnings.append(
                        f"Person is {age}. May hold probationary licence"
                    )

        # Check 4: Expiry date validation (Quebec DL expires on birthday)
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
                        f"({dob.strftime('%m-%d')}). Quebec DL typically expires on holder's birthday"
                    )

        # Check 5: Licence validity period (4 or 8 years)
        details["checks_performed"].append("validity_period")
        if issue_date_str and expiry_date:
            issue_date = self._parse_date(issue_date_str)
            exp = self._parse_date(expiry_date)
            if issue_date and exp:
                validity_years = (exp - issue_date).days / 365.25
                details["validity_years"] = round(validity_years, 1)

                # Quebec allows 4-year or 8-year licences
                if validity_years < 3.5:
                    warnings.append(
                        f"Short validity period ({validity_years:.1f} years). "
                        "May be a probationary or restricted licence."
                    )
                elif validity_years > 8.5:
                    warnings.append(
                        f"Validity period ({validity_years:.1f} years) exceeds maximum "
                        "8-year Quebec licence term"
                    )

        # Check 6: Document not expired
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

        # Check 7: Issue date reasonability
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
                                "Quebec requires minimum 16 for any licence"
                            )

        execution_time = (time.perf_counter() - start_time) * 1000

        # Determine result status
        if issues:
            return self._create_result(
                status=ValidationStatus.FAILED,
                message=f"Quebec Driver's Licence validation failed: {'; '.join(issues)}",
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
                message="Quebec Driver's Licence validation passed with warnings",
                details={
                    **details,
                    "warnings": warnings
                },
                execution_time_ms=execution_time
            )
        else:
            return self._create_result(
                status=ValidationStatus.PASSED,
                message="Quebec Driver's Licence validation passed",
                details=details,
                execution_time_ms=execution_time
            )
