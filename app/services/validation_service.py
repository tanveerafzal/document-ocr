import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import threading

from app.models.responses import (
    ValidatorResult,
    ValidationSummary,
    ValidationStatus,
)
from app.models.document_types import DocumentType, DocumentTypeInfo
from app.services.validators.base import BaseValidator
from app.services.validators.data_consistency import DataConsistencyValidator
from app.services.validators.document_expiry import DocumentExpiryValidator
from app.services.validators.age_validator import AgeValidator
from app.services.validators.document_format import DocumentFormatValidator
from app.services.validators.face_matching import FaceMatchingValidator
from app.services.validators.ontario_dl import OntarioDriversLicenseValidator
from app.services.validators.ontario_health_card import OntarioHealthCardValidator
from app.services.validators.bc_dl import BCDriversLicenseValidator
from app.services.validators.alberta_dl import AlbertaDriversLicenseValidator
from app.services.validators.quebec_dl import QuebecDriversLicenseValidator
from app.services.validators.manitoba_dl import ManitobaDriversLicenseValidator
from app.services.validators.saskatchewan_dl import SaskatchewanDriversLicenseValidator
from app.services.validators.nova_scotia_dl import NovaScotiaDriversLicenseValidator
from app.services.validators.new_brunswick_dl import NewBrunswickDriversLicenseValidator
from app.services.validators.pei_dl import PEIDriversLicenseValidator
from app.services.validators.newfoundland_dl import NewfoundlandDriversLicenseValidator
from app.services.validators.nwt_dl import NWTDriversLicenseValidator
from app.services.validators.nunavut_dl import NunavutDriversLicenseValidator
from app.services.validators.yukon_dl import YukonDriversLicenseValidator
from app.services.validators.canadian_passport import CanadianPassportValidator
from app.services.validators.us_drivers_license import USDriversLicenseValidator
from app.services.document_type_detector import DocumentTypeDetector

# Configure logging for this module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Validator descriptions for logging
VALIDATOR_DESCRIPTIONS = {
    "data_consistency": "Checking date relationships (DOB < Issue Date < Expiry Date)",
    "document_expiry": "Checking if document is expired",
    "age_validation": "Checking if person meets minimum age requirement",
    "document_format": "Checking if document number matches known formats",
    "face_matching": "Checking face match between document and selfie",
    "ontario_drivers_license": "Validating Ontario DL: format, name match, age, expiry on birthday, DOB in last 6 digits",
    "ontario_health_card": "Validating Ontario Health Card: 10-digit format, Luhn checksum, version code, expiry check",
    "bc_drivers_license": "Validating BC DL: 7-digit format, age (16+ for L, 17+ for N), expiry on birthday, validity period",
    "alberta_drivers_license": "Validating Alberta DL: 9-digit format (XXXXXX-XXX), age (14+ for Learner), expiry on birthday",
    "quebec_drivers_license": "Validating Quebec DL: Letter + 12 digits, name match, age (16+), expiry on birthday",
    "manitoba_drivers_license": "Validating Manitoba DL: 4 letters + 6 digits (ABCD-123-456), name match, age (16+), expiry on birthday",
    "saskatchewan_drivers_license": "Validating Saskatchewan DL: 8-digit format, age (16+), expiry on birthday",
    "nova_scotia_drivers_license": "Validating Nova Scotia DL: 5 letters + 9 digits, surname prefix, age (16+), expiry on birthday",
    "new_brunswick_drivers_license": "Validating New Brunswick DL: 7-digit format, age (16+), expiry on birthday",
    "pei_drivers_license": "Validating PEI DL: 1-6 digit format, age (16+), expiry on birthday",
    "newfoundland_drivers_license": "Validating Newfoundland DL: Letter + 9 digits, name match, age (16+), expiry on birthday",
    "nwt_drivers_license": "Validating NWT DL: 6-digit format, age (15+), expiry on birthday",
    "nunavut_drivers_license": "Validating Nunavut DL: 6-digit format, age (15+), expiry on birthday",
    "yukon_drivers_license": "Validating Yukon DL: 6-digit format, age (15+), expiry on birthday",
    "canadian_passport": "Validating Canadian Passport: format (AA123456), validity period (5yr child/10yr adult), age checks",
    "us_drivers_license": "Validating US DL: state-specific format, age requirements, validity period, expiry check",
}


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
        self.minimum_age = minimum_age
        self.selfie_image = selfie_image

        # Base validators that run for all document types
        self.base_validators: List[BaseValidator] = [
            DataConsistencyValidator(),
            DocumentExpiryValidator(),
            AgeValidator(minimum_age=minimum_age),
            DocumentFormatValidator(),
            FaceMatchingValidator(selfie_image=selfie_image),
        ]

        # Document-type specific validators
        self.document_type_validators: Dict[DocumentType, List[BaseValidator]] = {
            # Canadian Provinces
            DocumentType.ONTARIO_DRIVERS_LICENSE: [
                OntarioDriversLicenseValidator(),
            ],
            DocumentType.ONTARIO_HEALTH_CARD: [
                OntarioHealthCardValidator(),
            ],
            DocumentType.BC_DRIVERS_LICENSE: [
                BCDriversLicenseValidator(),
            ],
            DocumentType.ALBERTA_DRIVERS_LICENSE: [
                AlbertaDriversLicenseValidator(),
            ],
            DocumentType.QUEBEC_DRIVERS_LICENSE: [
                QuebecDriversLicenseValidator(),
            ],
            DocumentType.MANITOBA_DRIVERS_LICENSE: [
                ManitobaDriversLicenseValidator(),
            ],
            DocumentType.SASKATCHEWAN_DRIVERS_LICENSE: [
                SaskatchewanDriversLicenseValidator(),
            ],
            DocumentType.NOVA_SCOTIA_DRIVERS_LICENSE: [
                NovaScotiaDriversLicenseValidator(),
            ],
            DocumentType.NEW_BRUNSWICK_DRIVERS_LICENSE: [
                NewBrunswickDriversLicenseValidator(),
            ],
            DocumentType.PEI_DRIVERS_LICENSE: [
                PEIDriversLicenseValidator(),
            ],
            DocumentType.NEWFOUNDLAND_DRIVERS_LICENSE: [
                NewfoundlandDriversLicenseValidator(),
            ],
            # Canadian Territories
            DocumentType.NWT_DRIVERS_LICENSE: [
                NWTDriversLicenseValidator(),
            ],
            DocumentType.NUNAVUT_DRIVERS_LICENSE: [
                NunavutDriversLicenseValidator(),
            ],
            DocumentType.YUKON_DRIVERS_LICENSE: [
                YukonDriversLicenseValidator(),
            ],
            # Other Documents
            DocumentType.CANADIAN_PASSPORT: [
                CanadianPassportValidator(),
            ],
            DocumentType.US_DRIVERS_LICENSE: [
                USDriversLicenseValidator(),
            ],
        }

    async def validate_document(
        self,
        document_data: Dict[str, Any],
        request_id: str = ""
    ) -> Tuple[ValidationSummary, List[ValidatorResult], Optional[DocumentTypeInfo]]:
        """
        Run all validators in parallel on document data.

        Args:
            document_data: Dictionary with extracted document fields
            request_id: Optional request ID for logging correlation

        Returns:
            Tuple of (ValidationSummary, List[ValidatorResult], DocumentTypeInfo)
        """
        log_prefix = f"[{request_id}]" if request_id else ""

        # Step 1: Detect document type
        print(f"{log_prefix} ========== DOCUMENT VALIDATION STARTED ==========")
        logger.info(f"{log_prefix} ========== DOCUMENT VALIDATION STARTED ==========")

        logger.info(f"{log_prefix} Step 1: Detecting document type...")
        print(f"{log_prefix} Step 1: Detecting document type...")

        document_type_info = DocumentTypeDetector.detect(document_data, request_id)

        doc_type_msg = (
            f"{log_prefix}   Detected: {document_type_info.document_name} "
            f"(confidence: {document_type_info.confidence:.0%})"
        )
        logger.info(doc_type_msg)
        print(doc_type_msg)

        if document_type_info.detected_features:
            features_msg = f"{log_prefix}   Features: {', '.join(document_type_info.detected_features)}"
            logger.info(features_msg)
            print(features_msg)

        # Step 2: Build validator list based on document type
        logger.info(f"{log_prefix} Step 2: Building validation checks...")
        print(f"{log_prefix} Step 2: Building validation checks...")

        validators = list(self.base_validators)

        # Add document-type specific validators
        if document_type_info.document_type in self.document_type_validators:
            type_specific = self.document_type_validators[document_type_info.document_type]
            validators.extend(type_specific)
            logger.info(
                f"{log_prefix}   Added {len(type_specific)} {document_type_info.document_name}-specific checks"
            )
            print(
                f"{log_prefix}   Added {len(type_specific)} {document_type_info.document_name}-specific checks"
            )

        logger.info(f"{log_prefix} Step 3: Running {len(validators)} validation checks in PARALLEL THREADS:")
        print(f"{log_prefix} Step 3: Running {len(validators)} validation checks in PARALLEL THREADS:")

        # Log what each validator will check
        for validator in validators:
            description = VALIDATOR_DESCRIPTIONS.get(validator.name, "Document-specific validation")
            logger.info(f"{log_prefix}   -> {validator.name}: {description}")
            print(f"{log_prefix}   -> {validator.name}: {description}")

        # Run all validators in parallel using ThreadPoolExecutor
        # This ensures true parallel execution in separate threads
        def run_validator_in_thread(validator: BaseValidator) -> ValidatorResult:
            """Run async validator in a new event loop within a thread."""
            thread_name = threading.current_thread().name
            logger.debug(f"{log_prefix}   [{validator.name}] Running in thread: {thread_name}")
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                return loop.run_until_complete(validator.validate(document_data))
            finally:
                loop.close()

        # Use ThreadPoolExecutor for true parallel execution
        with ThreadPoolExecutor(max_workers=len(validators), thread_name_prefix="validator") as executor:
            futures = [executor.submit(run_validator_in_thread, v) for v in validators]
            results: List[Any] = []
            for future in futures:
                try:
                    results.append(future.result())
                except Exception as e:
                    results.append(e)

        # Log results header
        logger.info(f"{log_prefix} ---------- VALIDATION RESULTS ----------")
        print(f"{log_prefix} ---------- VALIDATION RESULTS ----------")

        # Handle any exceptions that occurred and log each result
        processed_results: List[ValidatorResult] = []
        for i, result in enumerate(results):
            validator_name = validators[i].name

            if isinstance(result, Exception):
                log_msg = f"{log_prefix}   [FAIL] {validator_name}: ERROR - {str(result)}"
                logger.error(log_msg)
                print(log_msg)
                processed_results.append(ValidatorResult(
                    validator_name=validator_name,
                    status=ValidationStatus.FAILED,
                    message=f"Validator error: {str(result)}",
                    details={"error_type": type(result).__name__},
                    execution_time_ms=0
                ))
            else:
                # Log each validator result with clear status
                status_icon = self._get_status_icon(result.status)
                log_msg = (
                    f"{log_prefix}   {status_icon} {validator_name}: "
                    f"{result.message} ({result.execution_time_ms:.2f}ms)"
                )
                logger.info(log_msg)
                print(log_msg)
                processed_results.append(result)

        # Calculate summary
        summary = self._create_summary(processed_results)

        # Log summary with clear banner
        summary_msg = (
            f"{log_prefix} ========== VALIDATION COMPLETE ==========\n"
            f"{log_prefix}   Document Type: {document_type_info.document_name}\n"
            f"{log_prefix}   Overall Status: {summary.overall_status.value.upper()}\n"
            f"{log_prefix}   Validation Score: {summary.validation_score}\n"
            f"{log_prefix}   Passed: {summary.passed_checks} | "
            f"Failed: {summary.failed_checks} | "
            f"Warnings: {summary.warning_checks} | "
            f"Skipped: {summary.skipped_checks}\n"
            f"{log_prefix} ==========================================="
        )
        logger.info(summary_msg)
        print(summary_msg)

        return summary, processed_results, document_type_info

    def _get_status_icon(self, status: ValidationStatus) -> str:
        """Get a status indicator for logging."""
        icons = {
            ValidationStatus.PASSED: "[PASS]",
            ValidationStatus.FAILED: "[FAIL]",
            ValidationStatus.WARNING: "[WARN]",
            ValidationStatus.SKIPPED: "[SKIP]",
        }
        return icons.get(status, "[????]")

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
