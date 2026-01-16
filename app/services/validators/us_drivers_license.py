import re
import time
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from app.services.validators.base import BaseValidator
from app.models.responses import ValidatorResult, ValidationStatus


# State-specific license formats and rules
US_STATE_FORMATS = {
    "california": {
        "name": "California",
        "format": r"^[A-Z]\d{7}$",  # Letter + 7 digits
        "format_desc": "A1234567 (1 letter + 7 digits)",
        "min_age": 16,
        "validity_years": 5,
    },
    "texas": {
        "name": "Texas",
        "format": r"^\d{8}$",  # 8 digits
        "format_desc": "12345678 (8 digits)",
        "min_age": 16,
        "validity_years": 6,
    },
    "florida": {
        "name": "Florida",
        "format": r"^[A-Z]\d{12}$",  # Letter + 12 digits
        "format_desc": "A123456789012 (1 letter + 12 digits)",
        "min_age": 16,
        "validity_years": 8,
    },
    "new_york": {
        "name": "New York",
        "format": r"^\d{9}$",  # 9 digits
        "format_desc": "123456789 (9 digits)",
        "min_age": 16,
        "validity_years": 8,
    },
    "illinois": {
        "name": "Illinois",
        "format": r"^[A-Z]\d{11,12}$",  # Letter + 11-12 digits
        "format_desc": "A12345678901 (1 letter + 11-12 digits)",
        "min_age": 16,
        "validity_years": 4,
    },
    "pennsylvania": {
        "name": "Pennsylvania",
        "format": r"^\d{8}$",  # 8 digits
        "format_desc": "12345678 (8 digits)",
        "min_age": 16,
        "validity_years": 4,
    },
    "ohio": {
        "name": "Ohio",
        "format": r"^[A-Z]{2}\d{6}$",  # 2 letters + 6 digits
        "format_desc": "AB123456 (2 letters + 6 digits)",
        "min_age": 16,
        "validity_years": 4,
    },
    "georgia": {
        "name": "Georgia",
        "format": r"^\d{9}$",  # 9 digits
        "format_desc": "123456789 (9 digits)",
        "min_age": 16,
        "validity_years": 8,
    },
    "michigan": {
        "name": "Michigan",
        "format": r"^[A-Z]\d{12}$",  # Letter + 12 digits
        "format_desc": "A123456789012 (1 letter + 12 digits)",
        "min_age": 16,
        "validity_years": 4,
    },
    "arizona": {
        "name": "Arizona",
        "format": r"^[A-Z]\d{8}$|^\d{9}$",  # Letter + 8 digits OR 9 digits
        "format_desc": "A12345678 or 123456789",
        "min_age": 16,
        "validity_years": 12,  # Until age 65
    },
    "washington": {
        "name": "Washington",
        "format": r"^[A-Z]{1,7}[A-Z0-9*]{1,11}$",  # Complex format
        "format_desc": "LASTNAME*FN*MN + numbers",
        "min_age": 16,
        "validity_years": 6,
    },
    "new_jersey": {
        "name": "New Jersey",
        "format": r"^[A-Z]\d{14}$",  # Letter + 14 digits
        "format_desc": "A12345678901234 (1 letter + 14 digits)",
        "min_age": 17,
        "validity_years": 4,
    },
}


class USDriversLicenseValidator(BaseValidator):
    """
    Validate US Driver's License requirements.

    US DL specifics:
    - Format varies by state
    - Minimum age typically 16-18 depending on state
    - Validity period varies by state (4-12 years)
    - REAL ID compliance (indicated by star symbol)
    """

    name = "us_drivers_license"

    def _detect_state(self, document_data: Dict[str, Any]) -> Optional[str]:
        """
        Try to detect the state from document data.
        Returns state key (lowercase) or None.
        """
        # Check address field for state
        address = (document_data.get("address", "") or "").upper()

        # State abbreviations and names to check
        state_indicators = {
            "california": ["CA", "CALIFORNIA"],
            "texas": ["TX", "TEXAS"],
            "florida": ["FL", "FLORIDA"],
            "new_york": ["NY", "NEW YORK"],
            "illinois": ["IL", "ILLINOIS"],
            "pennsylvania": ["PA", "PENNSYLVANIA"],
            "ohio": ["OH", "OHIO"],
            "georgia": ["GA", "GEORGIA"],
            "michigan": ["MI", "MICHIGAN"],
            "arizona": ["AZ", "ARIZONA"],
            "washington": ["WA", "WASHINGTON"],
            "new_jersey": ["NJ", "NEW JERSEY"],
        }

        for state_key, indicators in state_indicators.items():
            for indicator in indicators:
                if indicator in address:
                    return state_key

        return None

    def _try_match_state_format(self, license_number: str) -> Optional[Tuple[str, str]]:
        """
        Try to match license number against known state formats.
        Returns tuple of (state_key, state_name) or None.
        """
        clean_number = re.sub(r"[\s\-]", "", license_number).upper()

        for state_key, state_info in US_STATE_FORMATS.items():
            if re.match(state_info["format"], clean_number):
                return state_key, state_info["name"]

        return None

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
        details = {"checks_performed": []}

        document_number = document_data.get("document_number", "") or ""
        last_name, name_source = self._extract_last_name(document_data)
        date_of_birth = document_data.get("date_of_birth")
        expiry_date = document_data.get("expiry_date")
        issue_date_str = document_data.get("issue_date")

        clean_number = re.sub(r"[\s\-]", "", document_number).upper()
        details["license_number"] = clean_number

        # Check 1: Detect or infer state
        details["checks_performed"].append("state_detection")
        detected_state = self._detect_state(document_data)
        matched_state = self._try_match_state_format(clean_number)

        state_key = None
        state_info = None

        if detected_state:
            state_key = detected_state
            state_info = US_STATE_FORMATS.get(detected_state)
            details["detected_state"] = state_info["name"] if state_info else detected_state
            details["detection_method"] = "address"
        elif matched_state:
            state_key, state_name = matched_state
            state_info = US_STATE_FORMATS.get(state_key)
            details["detected_state"] = state_name
            details["detection_method"] = "format_match"
        else:
            details["detected_state"] = "Unknown"
            details["detection_method"] = "none"

        # Check 2: License number format
        details["checks_performed"].append("license_number_format")
        if not clean_number:
            issues.append("Missing license number")
        elif state_info:
            # Validate against known state format
            if not re.match(state_info["format"], clean_number):
                issues.append(
                    f"License number doesn't match {state_info['name']} format. "
                    f"Expected: {state_info['format_desc']}, Got: {document_number}"
                )
            else:
                details["format_valid"] = True
                details["format_matched"] = state_info["name"]
        else:
            # Generic US license validation (6-16 alphanumeric characters)
            generic_format = r"^[A-Z0-9]{6,16}$"
            if not re.match(generic_format, clean_number):
                issues.append(
                    f"Invalid US license format. Expected 6-16 alphanumeric characters, "
                    f"Got: {document_number}"
                )
            else:
                details["format_valid"] = True
                details["format_matched"] = "Generic US"
                warnings.append(
                    "Could not determine specific state. Using generic US format validation."
                )

        # Check 3: First letter match for applicable states
        details["checks_performed"].append("first_letter_check")
        if clean_number and last_name:
            # States where first letter typically matches last name
            letter_match_states = ["california", "florida", "michigan", "illinois", "new_jersey"]

            if state_key in letter_match_states and clean_number[0].isalpha():
                license_letter = clean_number[0].upper()
                last_name_letter = last_name[0].upper()
                details["license_first_letter"] = license_letter
                details["last_name_initial"] = last_name_letter

                if license_letter != last_name_letter:
                    warnings.append(
                        f"License first letter '{license_letter}' may not match "
                        f"last name initial '{last_name_letter}' (common in {state_info['name'] if state_info else 'this state'})"
                    )
                else:
                    details["first_letter_matches"] = True

        # Check 4: Minimum age verification
        details["checks_performed"].append("minimum_age")
        if date_of_birth:
            dob = self._parse_date(date_of_birth)
            if dob:
                today = datetime.now()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                details["current_age"] = age

                min_age = state_info["min_age"] if state_info else 16
                details["minimum_age_required"] = min_age

                if age < min_age:
                    issues.append(
                        f"Person is {age} years old. "
                        f"Minimum age for driver's license is {min_age}"
                    )
                elif age < 18:
                    warnings.append(
                        f"Person is {age}. May have restricted license (graduated licensing)"
                    )

        # Check 5: Document expiry check
        details["checks_performed"].append("expiry_check")
        if expiry_date:
            exp = self._parse_date(expiry_date)
            if exp:
                today = datetime.now()
                if exp < today:
                    days_expired = (today - exp).days
                    issues.append(f"License expired {days_expired} days ago")
                else:
                    days_until_expiry = (exp - today).days
                    details["days_until_expiry"] = days_until_expiry
                    if days_until_expiry < 30:
                        warnings.append(f"License expires in {days_until_expiry} days")

        # Check 6: Validity period check
        details["checks_performed"].append("validity_period")
        if issue_date_str and expiry_date:
            issue_date = self._parse_date(issue_date_str)
            exp = self._parse_date(expiry_date)
            if issue_date and exp:
                validity_years = (exp - issue_date).days / 365.25
                details["validity_years"] = round(validity_years, 1)

                if state_info:
                    expected_validity = state_info["validity_years"]
                    # Allow some flexibility (±1 year)
                    if validity_years > expected_validity + 2:
                        warnings.append(
                            f"Validity period ({validity_years:.1f} years) exceeds typical "
                            f"{state_info['name']} license term ({expected_validity} years)"
                        )

        # Check 7: REAL ID indicator (if detectable)
        details["checks_performed"].append("real_id_check")
        # Note: REAL ID is typically indicated by a star on the physical card
        # This is a placeholder for future enhancement with image analysis
        details["real_id_status"] = "not_verified"

        execution_time = (time.perf_counter() - start_time) * 1000

        # Determine result status
        if issues:
            return self._create_result(
                status=ValidationStatus.FAILED,
                message=f"US Driver's License validation failed: {'; '.join(issues)}",
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
                message="US Driver's License validation passed with warnings",
                details={
                    **details,
                    "warnings": warnings
                },
                execution_time_ms=execution_time
            )
        else:
            return self._create_result(
                status=ValidationStatus.PASSED,
                message=f"US Driver's License validation passed" +
                       (f" ({details.get('detected_state', 'Unknown')} format)" if details.get('detected_state') != 'Unknown' else ""),
                details=details,
                execution_time_ms=execution_time
            )
