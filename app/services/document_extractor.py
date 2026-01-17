import os
import json
import base64
import logging
from anthropic import Anthropic
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = ["first_name", "last_name", "document_number", "date_of_birth", "expiry_date"]

# Claude model for document extraction - configurable via environment variable
# Options (in order of quality/cost):
#   - claude-3-haiku-20240307    (fastest, cheapest - default)
#   - claude-3-5-haiku-20241022  (faster haiku, good quality)
#   - claude-3-sonnet-20240229   (better quality)
#   - claude-3-5-sonnet-20241022 (recommended for better accuracy)
#   - claude-3-opus-20240229     (best quality, slowest, most expensive)
CLAUDE_MODEL = os.environ.get("CLAUDE_VISION_MODEL", "claude-3-haiku-20240307")
logger.info(f"Document extraction using Claude model: {CLAUDE_MODEL}")

VISION_PROMPT = """Analyze this identity document image and extract the following fields.

Return a JSON object with these exact fields:
- first_name: The person's first/given name
- last_name: The person's last name/surname/family name
- full_name: The complete name EXACTLY as shown on the document (preserve original format)
- document_number: The ID/document/license number or passport number
- date_of_birth: Date of birth (format as YYYY-MM-DD)
- issue_date: Document issue date (format as YYYY-MM-DD)
- expiry_date: Document expiry date (format as YYYY-MM-DD)
- gender: Gender (M, F, or as shown)
- address: Full address if present
- nationality: Nationality or issuing country (e.g., "CANADA", "USA", "UNITED KINGDOM", "INDIA")
- mrz: Machine Readable Zone - the 2 lines of text at the bottom of passports (if present)
- country_code: 3-letter country code from MRZ or document (e.g., "CAN", "USA", "GBR", "IND")
- document_title: The document type text shown on the card (e.g., "PASSPORT", "DRIVER'S LICENCE", "PERMANENT RESIDENT CARD", "HEALTH CARD", "PHOTO CARD")

IMPORTANT for Canadian Driver's Licences (Ontario, BC, etc.):
- Name format is "LASTNAME FIRSTNAME" or "LASTNAME, FIRSTNAME" (LAST NAME comes FIRST!)
- The FIRST word/part is the LAST NAME (surname/family name)
- The SECOND word/part is the FIRST NAME (given name)
- The first letter of Ontario driver's licence number corresponds to the LAST NAME
- Examples:
  - "SMITH JOHN" -> last_name="SMITH", first_name="JOHN"
  - "SMITH, JOHN" -> last_name="SMITH", first_name="JOHN"
  - "NADEEM ASIF" -> last_name="NADEEM", first_name="ASIF"

IMPORTANT for Manitoba Driver's Licence:
- The document number is labeled "DD/RÉF" on the card (9 digits)
- Extract the value next to "DD/RÉF" as the document_number

IMPORTANT for British Columbia (BC) Driver's Licence:
- Document number may have "NDL:" or "DL:" prefix (e.g., NDL:1234567 or DL:1234567)
- Include the prefix in the document_number if present
- The number is 7 digits

IMPORTANT for Photo Cards / Photo IDs:
- Photo Cards are provincial ID cards that are NOT driver's licences
- Look for text like "Photo Card", "Photo ID", "Identification Card"
- Extract the province/state name (e.g., "Ontario", "British Columbia", "Alberta")
- Ontario Photo Card format: Similar to health card

IMPORTANT for Canada Permanent Residence Card (PR Card):
- Look for text "PERMANENT RESIDENT" or "RÉSIDENT PERMANENT" or "PERMANENT RESIDENT CARD"
- The card says "CANADA" and "Immigration, Refugees and Citizenship Canada" or "IRCC"
- Document number format: 2 letters + 6 digits (e.g., RA123456)
- Set country_code to "CAN" for PR Cards
- This is NOT a passport - it's a residence card for permanent residents

IMPORTANT for US Driver's Licenses:
- California DL: 1 letter + 7 digits (e.g., A1234567) - first letter matches last name
- Texas DL: 8 digits (e.g., 12345678)
- Look for state name like "STATE OF CALIFORNIA", "STATE OF TEXAS", "DMV", "DPS"
- Extract the state name (e.g., "California", "Texas", "Florida")

IMPORTANT for Passports:
- Extract the MRZ (Machine Readable Zone) - the 2 lines of <<< text at the bottom
- Extract the country code from the MRZ (positions 3-5 of line 1, e.g., "P<CAN" = Canada)
- Extract the 3-letter ISO country code (e.g., CAN, USA, GBR, IND, AUS, DEU, FRA, NGA, CHN, COL, UKR, MEX, BRA, JPN, KOR, etc.)
- The country_code field is CRITICAL for passport identification - always extract it from the MRZ
- Passport number formats vary by country:
  - Canada: 2 letters + 6 digits (AB123456)
  - USA: 9 digits
  - UK: 9 digits
  - India: 1 letter + 7 digits (A1234567)
  - Australia: 1-2 letters + 7 digits
  - Germany: 9 alphanumeric
  - France: 9 alphanumeric
  - Nigeria: 1 letter + 8 digits (A12345678)
  - China: E/G/D + 8 digits (E12345678)
  - Colombia: 2 letters + 7 digits (CC1234567)
  - Ukraine: 2 letters + 6 digits (AA123456)

If a field cannot be found or is not visible, use null for that field.
Return ONLY the JSON object, no additional text or markdown formatting."""


class DocumentExtractorService:
    _client: Optional[Anthropic] = None

    @classmethod
    def get_client(cls) -> Anthropic:
        if cls._client is None:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
            cls._client = Anthropic(api_key=api_key)
        return cls._client

    @classmethod
    def validate_required_fields(cls, data: dict) -> Tuple[bool, List[str]]:
        """
        Check if all required fields are present and non-empty.

        Returns (is_valid, list of missing fields).
        """
        missing = []
        for field in REQUIRED_FIELDS:
            value = data.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(field)
        return len(missing) == 0, missing

    @classmethod
    def extract_from_image(cls, image_bytes: bytes, media_type: str = "image/png") -> Tuple[dict, bool, List[str]]:
        """
        Extract document fields directly from image using Claude Vision.

        Args:
            image_bytes: Raw image bytes
            media_type: MIME type (image/png, image/jpeg, image/webp, image/gif)

        Returns a tuple of (extracted_data, is_valid, missing_fields).
        """
        empty_result = {
            "first_name": None,
            "last_name": None,
            "full_name": None,
            "document_number": None,
            "date_of_birth": None,
            "issue_date": None,
            "expiry_date": None,
            "gender": None,
            "address": None,
            "nationality": None,
            "mrz": None,
            "country_code": None,
            "document_title": None
        }

        if not image_bytes:
            return empty_result, False, REQUIRED_FIELDS.copy()

        client = cls.get_client()

        # Encode image to base64
        image_base64 = base64.standard_b64encode(image_bytes).decode("utf-8")

        try:
            response = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=1000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": VISION_PROMPT
                            }
                        ]
                    }
                ]
            )

            result_text = response.content[0].text.strip()

            # Clean up potential markdown formatting
            if result_text.startswith("```"):
                lines = result_text.split("\n")
                result_text = "\n".join(lines[1:-1])

            extracted_data = json.loads(result_text)

            # Ensure all expected fields exist
            fields = [
                "first_name", "last_name", "full_name", "document_number",
                "date_of_birth", "issue_date", "expiry_date", "gender", "address",
                "nationality", "mrz", "country_code", "document_title"
            ]
            for field in fields:
                if field not in extracted_data:
                    extracted_data[field] = None

            # Validate required fields
            is_valid, missing_fields = cls.validate_required_fields(extracted_data)

            return extracted_data, is_valid, missing_fields

        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse AI response as JSON: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"AI vision extraction failed: {str(e)}")
