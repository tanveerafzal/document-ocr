import re
import time
from datetime import datetime
from typing import Dict, Any
from app.services.validators.base import BaseValidator
from app.models.responses import ValidatorResult, ValidationStatus


class CanadaPRCardValidator(BaseValidator):
    """
    Validate Canada Permanent Residence Card.

    This validator handles Canadian PR Cards and performs:
    - Document number format validation (2 letters + 6 digits)
    - Date validations (issue date, expiry date, date of birth)
    - Expiry check (PR cards are valid for 5 years)
    """

    name = "canada_pr_card"

    async def validate(self, document_data: Dict[str, Any]) -> ValidatorResult:
        start_time = time.perf_counter()

        issues = []
        warnings = []
        details = {"checks_performed": []}

        document_number = document_data.get("document_number", "") or ""
        date_of_birth = document_data.get("date_of_birth")
        issue_date_str = document_data.get("issue_date")
        expiry_date = document_data.get("expiry_date")

        # Check 1: Document number format (2 letters + 6 digits)
        details["checks_performed"].append("document_number_format")
        clean_number = re.sub(r"[\s\-]", "", document_number.strip().upper())

        if not clean_number:
            issues.append("Missing document number")
        else:
            # PR Card format: 2 letters + 6 digits (e.g., AB123456)
            pr_card_pattern = r"^[A-Z]{2}\d{6}$"
            if re.match(pr_card_pattern, clean_number):
                details["document_number_valid"] = True
                details["document_number_format"] = "Valid PR Card format (2 letters + 6 digits)"
            else:
                warnings.append(f"Document number '{document_number}' does not match expected PR Card format (2 letters + 6 digits)")
                details["document_number_valid"] = False

        # Check 2: Date of birth validation
        details["checks_performed"].append("date_of_birth_check")
        if date_of_birth:
            dob = self._parse_date(date_of_birth)
            if dob:
                today = datetime.now()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                details["calculated_age"] = age

                if dob > today:
                    issues.append("Date of birth cannot be in the future")
                elif age < 0:
                    issues.append("Invalid date of birth")
                elif age < 18:
                    warnings.append(f"Holder is under 18 years old (age: {age})")

        # Check 3: Issue date validation
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

        # Check 4: Expiry check
        details["checks_performed"].append("expiry_check")
        if expiry_date:
            exp = self._parse_date(expiry_date)
            if exp:
                today = datetime.now()
                if exp < today:
                    days_expired = (today - exp).days
                    issues.append(f"PR Card expired {days_expired} days ago")
                else:
                    days_until_expiry = (exp - today).days
                    details["days_until_expiry"] = days_until_expiry
                    if days_until_expiry < 180:
                        warnings.append(f"PR Card expires in {days_until_expiry} days - renewal recommended within 6 months of expiry")
                    elif days_until_expiry < 365:
                        warnings.append(f"PR Card expires in {days_until_expiry} days")

        # Check 5: Validity period (PR cards are typically valid for 5 years)
        details["checks_performed"].append("validity_period")
        if issue_date_str and expiry_date:
            issue_date = self._parse_date(issue_date_str)
            exp = self._parse_date(expiry_date)
            if issue_date and exp:
                validity_days = (exp - issue_date).days
                validity_years = validity_days / 365.25
                details["validity_years"] = round(validity_years, 1)

                if validity_years < 4:
                    warnings.append(f"PR Card has shorter than expected validity ({validity_years:.1f} years, expected ~5 years)")
                elif validity_years > 6:
                    warnings.append(f"PR Card has longer than expected validity ({validity_years:.1f} years)")

        execution_time = (time.perf_counter() - start_time) * 1000

        if issues:
            return self._create_result(
                status=ValidationStatus.FAILED,
                message=f"PR Card validation failed: {'; '.join(issues)}",
                details={**details, "issues": issues, "warnings": warnings},
                execution_time_ms=execution_time
            )
        elif warnings:
            return self._create_result(
                status=ValidationStatus.WARNING,
                message="PR Card validation passed with warnings",
                details={**details, "warnings": warnings},
                execution_time_ms=execution_time
            )
        else:
            return self._create_result(
                status=ValidationStatus.PASSED,
                message="PR Card validation passed",
                details=details,
                execution_time_ms=execution_time
            )
