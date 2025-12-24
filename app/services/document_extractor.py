import os
import json
import base64
from anthropic import Anthropic
from typing import Optional, Tuple, List


REQUIRED_FIELDS = ["first_name", "last_name", "document_number", "date_of_birth", "expiry_date"]

VISION_PROMPT = """Analyze this identity document image and extract the following fields.

Return a JSON object with these exact fields:
- first_name: The person's first name
- last_name: The person's last name
- full_name: The complete name as shown on the document
- document_number: The ID/document/license number
- date_of_birth: Date of birth (format as shown in document)
- issue_date: Document issue date (format as shown in document)
- expiry_date: Document expiry date (format as shown in document)
- gender: Gender (M, F, or as shown)
- address: Full address if present

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
            "address": None
        }

        if not image_bytes:
            return empty_result, False, REQUIRED_FIELDS.copy()

        client = cls.get_client()

        # Encode image to base64
        image_base64 = base64.standard_b64encode(image_bytes).decode("utf-8")

        try:
            response = client.messages.create(
                model="claude-3-haiku-20240307",
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
                "date_of_birth", "issue_date", "expiry_date", "gender", "address"
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
