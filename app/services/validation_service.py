import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple

from app.models.responses import (
    ValidatorResult,
    ValidationSummary,
    ValidationStatus,
)
from app.services.validators.base import BaseValidator
from app.services.validators.data_consistency import DataConsistencyValidator
from app.services.validators.document_expiry import DocumentExpiryValidator
from app.services.validators.age_validator import AgeValidator
from app.services.validators.document_format import DocumentFormatValidator
from app.services.validators.face_matching import FaceMatchingValidator

logger = logging.getLogger(__name__)


class ValidationService:
    """Orchestrates parallel validation of document data."""

    def __init__(
        self,
        minimum_age: int = 18,
        selfie_image: Optional[bytes] = None
    ):
        """
        Initialize validation service with configurable validators.

        Args:
            minimum_age: Minimum age requirement for age validation
            selfie_image: Optional selfie image bytes for face matching
        """
        self.validators: List[BaseValidator] = [
            DataConsistencyValidator(),
            DocumentExpiryValidator(),
            AgeValidator(minimum_age=minimum_age),
            DocumentFormatValidator(),
            FaceMatchingValidator(selfie_image=selfie_image),
        ]

    async def validate_document(
        self,
        document_data: Dict[str, Any]
    ) -> Tuple[ValidationSummary, List[ValidatorResult]]:
        """
        Run all validators in parallel on document data.

        Args:
            document_data: Dictionary with extracted document fields

        Returns:
            Tuple of (ValidationSummary, List[ValidatorResult])
        """
        # Run all validators in parallel using asyncio.gather
        validation_tasks = [
            validator.validate(document_data)
            for validator in self.validators
        ]

        results: List[Any] = await asyncio.gather(
            *validation_tasks,
            return_exceptions=True
        )

        # Handle any exceptions that occurred
        processed_results: List[ValidatorResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(ValidatorResult(
                    validator_name=self.validators[i].name,
                    status=ValidationStatus.FAILED,
                    message=f"Validator error: {str(result)}",
                    details={"error_type": type(result).__name__},
                    execution_time_ms=0
                ))
            else:
                processed_results.append(result)

        # Calculate summary
        summary = self._create_summary(processed_results)

        return summary, processed_results

    def _create_summary(
        self,
        results: List[ValidatorResult]
    ) -> ValidationSummary:
        """Create summary from validation results."""
        passed = sum(1 for r in results if r.status == ValidationStatus.PASSED)
        failed = sum(1 for r in results if r.status == ValidationStatus.FAILED)
        warnings = sum(1 for r in results if r.status == ValidationStatus.WARNING)
        skipped = sum(1 for r in results if r.status == ValidationStatus.SKIPPED)

        total = len(results)
        active_checks = total - skipped

        # Calculate score (0-1)
        # Passed = 1, Warning = 0.5, Failed = 0, Skipped = excluded
        if active_checks > 0:
            score = (passed + (warnings * 0.5)) / active_checks
        else:
            score = 0.0

        # Determine overall status
        if failed > 0:
            overall_status = ValidationStatus.FAILED
        elif warnings > 0:
            overall_status = ValidationStatus.WARNING
        elif passed > 0:
            overall_status = ValidationStatus.PASSED
        else:
            overall_status = ValidationStatus.SKIPPED

        return ValidationSummary(
            overall_status=overall_status,
            validation_score=round(score, 2),
            total_checks=total,
            passed_checks=passed,
            failed_checks=failed,
            warning_checks=warnings,
            skipped_checks=skipped
        )
