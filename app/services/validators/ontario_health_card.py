import re
import time
from datetime import datetime
from typing import Dict, Any, Tuple
from app.services.validators.base import BaseValidator
from app.models.responses import ValidatorResult, ValidationStatus


class OntarioHealthCardValidator(BaseValidator):
    """
    Validate Ontario Health Card (OHIP) specific requirements.

    Ontario Health Card specifics:
    - Format: 10 digits + 2-letter version code (e.g., 1234567890AB)
    - May be formatted as XXXX-XXX-XXX-XX or XXXX-XXX-XXX XX
    - The 10-digit health number uses Luhn algorithm (mod 10 checksum)
    - Version code: 2 uppercase letters
      - Letters I, O, Q, U are NOT allowed (to avoid confusion with numbers)
      - Valid letters: A, B, C, D, E, F, G, H, J, K, L, M, N, P, R, S, T, V, W, X, Y, Z
      - Increments: AA → AB → ... → AH → AJ (skips AI) → ... → ZZ
      - Changes when card is renewed, replaced, or info is updated
    - Card expires every 5 years (photo health card)
    - Red and white cards (old) have no expiry but are being phased out
    """

    name = "ontario_health_card"

    def _luhn_checksum(self, number: str) -> bool:
        """
        Validate a number using the Luhn algorithm (mod 10).

        The Luhn algorithm:
        1. From the rightmost digit, double every second digit
        2. If doubling results in a number > 9, subtract 9
        3. Sum all digits
        4. If total mod 10 equals 0, the number is valid

        Args:
            number: String of digits to validate

        Returns:
            True if valid Luhn checksum, False otherwise
        """
        if not number.isdigit():
            return False

        digits = [int(d) for d in number]
        # Reverse for easier processing (start from rightmost)
        digits = digits[::-1]

        checksum = 0
        for i, digit in enumerate(digits):
            if i % 2 == 1:  # Double every second digit (0-indexed, so odd positions)
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit

        return checksum % 10 == 0

    def _parse_health_card_number(self, document_number: str) -> Tuple[str, str, bool]:
        """
        Parse Ontario Health Card number into health number and version code.

        Args:
            document_number: Raw document number string

        Returns:
            Tuple of (health_number, version_code, is_valid_format)
        """
        if not document_number:
            return "", "", False

        # Remove all spaces, hyphens, and other separators
        clean = re.sub(r"[\s\-]", "", document_number.upper())

        # Try to extract 10 digits and 2 letters
        # Format could be: 1234567890AB or with separators
        match = re.match(r"^(\d{10})([A-Z]{2})$", clean)
        if match:
            return match.group(1), match.group(2), True

        # Try format without version code (old cards or partial)
        if re.match(r"^\d{10}$", clean):
            return clean, "", True

        # Try to extract digits and letters separately
        digits = re.sub(r"[^\d]", "", clean)
        letters = re.sub(r"[^A-Z]", "", clean)

        if len(digits) == 10 and len(letters) == 2:
            return digits, letters, True
        elif len(digits) == 10 and len(letters) == 0:
            return digits, "", True

        return clean, "", False

    # Letters excluded from version codes (to avoid confusion with numbers)
    INVALID_VERSION_LETTERS = {'I', 'O', 'Q', 'U'}

    def _validate_version_code(self, version_code: str) -> Tuple[bool, str]:
        """
        Validate the 2-letter version code.

        Ontario Health Card version codes:
        - Must be 2 uppercase letters
        - Cannot contain I, O, Q, U (excluded to avoid confusion)
        - Increments: AA → AB → ... → AZ → BA → BB → ... → ZZ (skipping invalid letters)

        Args:
            version_code: The 2-letter version code

        Returns:
            Tuple of (is_valid, message)
        """
        if not version_code:
            return True, "No version code (may be old-style card)"

        if len(version_code) != 2:
            return False, f"Version code must be 2 letters, got {len(version_code)}"

        if not version_code.isalpha():
            return False, f"Version code must be letters only, got '{version_code}'"

        # Check for invalid letters (I, O, Q, U are not used)
        invalid_found = [c for c in version_code.upper() if c in self.INVALID_VERSION_LETTERS]
        if invalid_found:
            return False, (
                f"Version code contains invalid letter(s): {', '.join(invalid_found)}. "
                f"Letters I, O, Q, U are not used in Ontario Health Card version codes."
            )

        return True, f"Valid version code: {version_code}"

    async def validate(self, document_data: Dict[str, Any]) -> ValidatorResult:
        start_time = time.perf_counter()

        issues = []
        warnings = []
        details = {"checks_performed": []}

        document_number = document_data.get("document_number", "") or ""
        date_of_birth = document_data.get("date_of_birth")
        expiry_date = document_data.get("expiry_date")

        # Check 1: Parse and validate format
        details["checks_performed"].append("health_card_format")
        health_number, version_code, is_valid_format = self._parse_health_card_number(document_number)

        details["raw_document_number"] = document_number
        details["health_number"] = health_number
        details["version_code"] = version_code if version_code else "none"

        if not document_number:
            issues.append("Missing health card number")
        elif not is_valid_format:
            issues.append(
                f"Invalid Ontario Health Card format. Expected: 10 digits + 2-letter version code "
                f"(e.g., 1234567890AB), Got: {document_number}"
            )
        else:
            details["format_valid"] = True

        # Check 2: Luhn checksum validation
        details["checks_performed"].append("luhn_checksum")
        if health_number and len(health_number) == 10:
            is_valid_luhn = self._luhn_checksum(health_number)
            details["luhn_valid"] = is_valid_luhn

            if not is_valid_luhn:
                issues.append(
                    f"Health card number '{health_number}' failed Luhn checksum validation. "
                    "The number may be incorrectly entered or invalid."
                )
            else:
                details["luhn_checksum_passed"] = True

        # Check 3: Version code validation
        details["checks_performed"].append("version_code_validation")
        if is_valid_format:
            version_valid, version_message = self._validate_version_code(version_code)
            details["version_code_valid"] = version_valid
            details["version_code_message"] = version_message

            if not version_code:
                warnings.append(
                    "No version code found. This may be an old-style (red and white) health card "
                    "which is being phased out."
                )
            elif not version_valid:
                issues.append(f"Invalid version code: {version_message}")

        # Check 4: Expiry date validation
        details["checks_performed"].append("expiry_check")
        if expiry_date:
            exp = self._parse_date(expiry_date)
            if exp:
                today = datetime.now()
                if exp < today:
                    days_expired = (today - exp).days
                    issues.append(f"Health card expired {days_expired} days ago")
                else:
                    days_until_expiry = (exp - today).days
                    details["days_until_expiry"] = days_until_expiry
                    if days_until_expiry < 90:
                        warnings.append(
                            f"Health card expires in {days_until_expiry} days. "
                            "Consider renewing soon."
                        )
        else:
            # Old red and white cards don't have expiry
            if not version_code:
                warnings.append(
                    "No expiry date. Old-style health cards without photo are being phased out. "
                    "Please update to a photo health card."
                )

        # Check 5: Age validation (must be born to have health card)
        details["checks_performed"].append("age_validation")
        if date_of_birth:
            dob = self._parse_date(date_of_birth)
            if dob:
                today = datetime.now()
                if dob > today:
                    issues.append("Date of birth cannot be in the future")
                else:
                    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                    details["calculated_age"] = age

        execution_time = (time.perf_counter() - start_time) * 1000

        # Determine result status
        if issues:
            return self._create_result(
                status=ValidationStatus.FAILED,
                message=f"Ontario Health Card validation failed: {'; '.join(issues)}",
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
                message="Ontario Health Card validation passed with warnings",
                details={
                    **details,
                    "warnings": warnings
                },
                execution_time_ms=execution_time
            )
        else:
            return self._create_result(
                status=ValidationStatus.PASSED,
                message="Ontario Health Card validation passed",
                details=details,
                execution_time_ms=execution_time
            )
