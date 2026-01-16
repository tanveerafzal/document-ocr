import logging
import httpx
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from app.config import VERIFIK_API_ENABLED, VERIFIK_API_TOKEN, VERIFIK_API_BASE_URL

logger = logging.getLogger(__name__)


class VerifikValidationStatus(Enum):
    """Status of Verifik API validation."""
    VALID = "valid"
    INVALID = "invalid"
    ERROR = "error"
    DISABLED = "disabled"
    SKIPPED = "skipped"


@dataclass
class VerifikValidationResult:
    """Result from Verifik API validation."""
    status: VerifikValidationStatus
    message: str
    details: Optional[Dict[str, Any]] = None
    raw_response: Optional[Dict[str, Any]] = None


class VerifikClient:
    """Client for Verifik API to validate Canadian driver's licenses."""

    def __init__(self):
        self.enabled = VERIFIK_API_ENABLED
        self.token = VERIFIK_API_TOKEN
        self.base_url = VERIFIK_API_BASE_URL
        self.timeout = 30.0  # 30 seconds timeout

    def is_enabled(self) -> bool:
        """Check if Verifik API validation is enabled."""
        return self.enabled and bool(self.token)

    async def validate_ontario_dl(
        self,
        document_number: str
    ) -> VerifikValidationResult:
        """
        Validate Ontario driver's license using Verifik API.

        Args:
            document_number: The Ontario DL number

        Returns:
            VerifikValidationResult with validation status
        """
        if not self.is_enabled():
            return VerifikValidationResult(
                status=VerifikValidationStatus.DISABLED,
                message="Verifik API validation is disabled"
            )

        url = f"{self.base_url}/ca/ontario/driver-license"
        params = {"documentNumber": document_number}

        return await self._make_request(url, params, "Ontario DL")

    async def validate_bc_dl(
        self,
        document_number: str,
        last_name: str
    ) -> VerifikValidationResult:
        """
        Validate BC driver's license using Verifik API.

        Args:
            document_number: The BC DL number
            last_name: The last name on the license (required)

        Returns:
            VerifikValidationResult with validation status
        """
        if not self.is_enabled():
            return VerifikValidationResult(
                status=VerifikValidationStatus.DISABLED,
                message="Verifik API validation is disabled"
            )

        url = f"{self.base_url}/ca/british-columbia/driver-license"
        params = {
            "documentNumber": document_number,
            "lastName": last_name
        }

        return await self._make_request(url, params, "BC DL")

    async def _make_request(
        self,
        url: str,
        params: Dict[str, str],
        document_type: str
    ) -> VerifikValidationResult:
        """
        Make HTTP request to Verifik API.

        Args:
            url: The API endpoint URL
            params: Query parameters
            document_type: Type of document for logging

        Returns:
            VerifikValidationResult with validation status
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }

        logger.info(f"Verifik API: Validating {document_type} with params: {params}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params, headers=headers)

                logger.info(f"Verifik API: Response status {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Verifik API: Response data: {data}")

                    # Check if the response indicates a valid document
                    # Verifik typically returns a "data" object with document details if valid
                    if "data" in data and data.get("data"):
                        return VerifikValidationResult(
                            status=VerifikValidationStatus.VALID,
                            message=f"{document_type} validated successfully via Verifik API",
                            details=data.get("data"),
                            raw_response=data
                        )
                    else:
                        return VerifikValidationResult(
                            status=VerifikValidationStatus.INVALID,
                            message=f"{document_type} not found or invalid in Verifik database",
                            raw_response=data
                        )

                elif response.status_code == 404:
                    return VerifikValidationResult(
                        status=VerifikValidationStatus.INVALID,
                        message=f"{document_type} not found in Verifik database",
                        raw_response=response.json() if response.content else None
                    )

                elif response.status_code == 401:
                    logger.error("Verifik API: Authentication failed - invalid token")
                    return VerifikValidationResult(
                        status=VerifikValidationStatus.ERROR,
                        message="Verifik API authentication failed",
                        details={"http_status": 401}
                    )

                elif response.status_code == 429:
                    logger.warning("Verifik API: Rate limit exceeded")
                    return VerifikValidationResult(
                        status=VerifikValidationStatus.ERROR,
                        message="Verifik API rate limit exceeded",
                        details={"http_status": 429}
                    )

                else:
                    logger.error(f"Verifik API: Unexpected status {response.status_code}")
                    return VerifikValidationResult(
                        status=VerifikValidationStatus.ERROR,
                        message=f"Verifik API returned unexpected status: {response.status_code}",
                        details={"http_status": response.status_code},
                        raw_response=response.json() if response.content else None
                    )

        except httpx.TimeoutException:
            logger.error(f"Verifik API: Request timeout for {document_type}")
            return VerifikValidationResult(
                status=VerifikValidationStatus.ERROR,
                message="Verifik API request timed out",
                details={"error": "timeout"}
            )

        except httpx.RequestError as e:
            logger.error(f"Verifik API: Request error for {document_type}: {str(e)}")
            return VerifikValidationResult(
                status=VerifikValidationStatus.ERROR,
                message=f"Verifik API request failed: {str(e)}",
                details={"error": str(e)}
            )

        except Exception as e:
            logger.error(f"Verifik API: Unexpected error for {document_type}: {str(e)}")
            return VerifikValidationResult(
                status=VerifikValidationStatus.ERROR,
                message=f"Verifik API unexpected error: {str(e)}",
                details={"error": str(e)}
            )


# Singleton instance
verifik_client = VerifikClient()
