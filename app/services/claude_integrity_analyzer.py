"""
Claude Vision Document Integrity Analyzer

Uses Claude's vision capabilities to analyze document authenticity by examining:
1. Photo tampering signs (edges, blending, lighting inconsistencies)
2. Screen capture detection (photo of screen displaying an ID)

This provides accurate fraud detection leveraging Claude's ability to
understand visual context holistically.
"""

import os
import json
import base64
import logging
from anthropic import Anthropic
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# Use a capable model for integrity analysis
CLAUDE_INTEGRITY_MODEL = os.environ.get("CLAUDE_INTEGRITY_MODEL", "claude-sonnet-4-20250514")

INTEGRITY_ANALYSIS_PROMPT = """You are a document forensics expert. Analyze this ID document for:
1. SPECIMEN/SAMPLE documents (educational examples, not real IDs)
2. Photo tampering (photo was replaced/edited)
3. Screen capture (photo of a screen showing an ID)

## 1. SPECIMEN/SAMPLE DOCUMENT DETECTION (IMPORTANT!)
These are educational/example documents, NOT real IDs. Flag as specimen if you see:
- **Visual markers**: Red boxes, arrows, circles, or callouts pointing to fields
- **Overlay text**: "SPECIMEN", "SAMPLE", "VOID", "EXAMPLE", "NOT VALID" watermarks
- **Placeholder names**: "PUBLIC", "DOE", "SMITH", "SAMPLE", "TEST" as names
- **Fake addresses**: "123 MAIN STREET" or similar generic addresses
- **Sequential numbers**: Document numbers like "123456789", "987654321"
- **Instructional annotations**: Labels explaining document fields
- **Multiple views**: Same document shown multiple times with annotations

## 2. PHOTO TAMPERING - Only flag if OBVIOUS:
- Clear cut lines or unnatural borders around the photo
- Photo clearly pasted on (visible edges, wrong perspective)
- Dramatic lighting mismatch (shadows going opposite direction)

## 3. SCREEN CAPTURE - Only flag if OBVIOUS:
- Clearly visible screen pixels (RGB subpixel pattern)
- Visible monitor bezel or frame
- Obvious moire patterns from photographing a screen

## WHAT IS NOT FRAUD (do NOT flag):
- Normal JPEG compression artifacts
- Slight color/lighting variations from scanning
- Normal wear and tear, faded documents
- Flash reflections on laminated cards
- Slightly blurry photos

## GUIDELINES:
- ALWAYS flag specimen/sample documents - they are not valid for identification
- For real documents, default to NOT fraudulent unless evidence is clear
- Specimen documents should get "reject" recommendation

Return JSON:
{
    "specimen_document": {
        "is_specimen": boolean (true if this is a sample/specimen document),
        "confidence": float (0.0-1.0),
        "findings": [list of specimen indicators found],
        "details": {
            "visual_markers": {"detected": boolean, "description": string or null},
            "overlay_text": {"detected": boolean, "description": string or null},
            "placeholder_data": {"detected": boolean, "description": string or null}
        }
    },
    "photo_tampering": {
        "is_suspicious": boolean,
        "confidence": float (0.0-1.0),
        "findings": [list of issues],
        "details": {
            "edge_artifacts": {"detected": boolean, "description": string or null},
            "blending_issues": {"detected": boolean, "description": string or null},
            "lighting_mismatch": {"detected": boolean, "description": string or null},
            "color_mismatch": {"detected": boolean, "description": string or null},
            "resolution_mismatch": {"detected": boolean, "description": string or null}
        }
    },
    "screen_capture": {
        "is_suspicious": boolean,
        "confidence": float (0.0-1.0),
        "findings": [list of issues],
        "details": {
            "screen_pixels": {"detected": boolean, "description": string or null},
            "screen_glare": {"detected": boolean, "description": string or null},
            "refresh_lines": {"detected": boolean, "description": string or null},
            "bezel_visible": {"detected": boolean, "description": string or null}
        }
    },
    "overall_assessment": {
        "is_likely_fraudulent": boolean (true for specimens OR tampering OR screen capture),
        "fraud_confidence": float (0.0-1.0),
        "risk_level": string ("low", "medium", "high", "critical"),
        "summary": string (brief assessment - mention if specimen),
        "recommended_action": string ("accept", "review", "reject")
    }
}

Return ONLY the JSON object, no additional text."""


class ClaudeIntegrityAnalyzer:
    """Uses Claude Vision to analyze document integrity and detect fraud."""

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
    def analyze(cls, image_bytes: bytes, media_type: str = "image/png") -> Dict[str, Any]:
        """
        Analyze document image for signs of tampering or fraud using Claude Vision.

        Args:
            image_bytes: Raw image bytes
            media_type: MIME type (image/png, image/jpeg, image/webp, image/gif)

        Returns:
            Dictionary with detailed integrity analysis results
        """
        default_result = {
            "specimen_document": {
                "is_specimen": False,
                "confidence": 0.0,
                "findings": [],
                "details": {}
            },
            "photo_tampering": {
                "is_suspicious": False,
                "confidence": 0.0,
                "findings": [],
                "details": {}
            },
            "screen_capture": {
                "is_suspicious": False,
                "confidence": 0.0,
                "findings": [],
                "details": {}
            },
            "overall_assessment": {
                "is_likely_fraudulent": False,
                "fraud_confidence": 0.0,
                "risk_level": "low",
                "summary": "Analysis could not be completed",
                "recommended_action": "review"
            },
            "analysis_completed": False,
            "error": None
        }

        if not image_bytes:
            default_result["error"] = "No image provided"
            return default_result

        client = cls.get_client()

        # Encode image to base64
        image_base64 = base64.standard_b64encode(image_bytes).decode("utf-8")

        logger.info(f"Running Claude integrity analysis using model: {CLAUDE_INTEGRITY_MODEL}")

        try:
            response = client.messages.create(
                model=CLAUDE_INTEGRITY_MODEL,
                max_tokens=2000,
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
                                "text": INTEGRITY_ANALYSIS_PROMPT
                            }
                        ]
                    }
                ]
            )

            result_text = response.content[0].text.strip()

            # Clean up potential markdown formatting
            if result_text.startswith("```"):
                lines = result_text.split("\n")
                # Remove first line (```json) and last line (```)
                result_text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

            analysis_result = json.loads(result_text)
            analysis_result["analysis_completed"] = True
            analysis_result["error"] = None

            # Log key findings
            if analysis_result.get("overall_assessment", {}).get("is_likely_fraudulent"):
                logger.warning(f"Claude detected potential fraud: {analysis_result['overall_assessment'].get('summary')}")

            return analysis_result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {str(e)}")
            default_result["error"] = f"Failed to parse analysis response: {str(e)}"
            return default_result
        except Exception as e:
            logger.error(f"Claude integrity analysis failed: {str(e)}")
            default_result["error"] = f"Analysis failed: {str(e)}"
            return default_result

    @classmethod
    def get_summary(cls, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract a simplified summary from the full analysis result.

        Returns:
            Dictionary with key findings and overall assessment
        """
        if not analysis_result.get("analysis_completed"):
            return {
                "is_fraudulent": False,
                "confidence": 0.0,
                "risk_level": "unknown",
                "issues_detected": [],
                "recommendation": "review",
                "error": analysis_result.get("error")
            }

        issues = []

        # Check specimen document
        specimen = analysis_result.get("specimen_document", {})
        if specimen.get("is_specimen"):
            issues.append({
                "type": "specimen_document",
                "confidence": specimen.get("confidence", 0),
                "findings": specimen.get("findings", [])
            })

        # Check photo tampering
        photo = analysis_result.get("photo_tampering", {})
        if photo.get("is_suspicious"):
            issues.append({
                "type": "photo_tampering",
                "confidence": photo.get("confidence", 0),
                "findings": photo.get("findings", [])
            })

        # Check screen capture
        screen = analysis_result.get("screen_capture", {})
        if screen.get("is_suspicious"):
            issues.append({
                "type": "screen_capture",
                "confidence": screen.get("confidence", 0),
                "findings": screen.get("findings", [])
            })

        overall = analysis_result.get("overall_assessment", {})

        return {
            "is_fraudulent": overall.get("is_likely_fraudulent", False),
            "confidence": overall.get("fraud_confidence", 0),
            "risk_level": overall.get("risk_level", "unknown"),
            "issues_detected": issues,
            "recommendation": overall.get("recommended_action", "review"),
            "summary": overall.get("summary", "")
        }
