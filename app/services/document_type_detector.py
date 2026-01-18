import re
import logging
from typing import Dict, Any, Optional

from app.models.document_types import DocumentType, DocumentTypeInfo, DOCUMENT_PATTERNS, COUNTRY_CODES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentTypeDetector:
    """Detects the type of ID document based on extracted fields and patterns."""

    # Keywords for each document category
    PASSPORT_KEYWORDS = ["passport", "passeport", "pasaporte", "reisepass", "паспорт", "passport no", "passport number"]

    DL_KEYWORDS = ["driver", "licence", "license", "permis", "conduire", "operator"]

    HEALTH_CARD_KEYWORDS = ["health card", "health insurance", "ohip", "carte santé", "carte soleil"]

    PHOTO_ID_KEYWORDS = [
        "photo card", "photo id", "photocard", "photo identification", "identification card",
        "identity card", "id card", "bc services card", "bcid", "bc identification",
        "services card", "bc card", "enhanced id", "provincial id", "government id", "non-driver"
    ]

    PR_CARD_KEYWORDS = [
        "permanent resident", "permanent residence", "résident permanent",
        "pr card", "carte rp", "carte de résident", "resident card",
        "immigration, refugees", "ircc", "immigration canada",
        "government of canada", "gouvernement du canada"  # PR cards show this header
    ]

    # Province mappings
    PROVINCE_MAPPING = {
        "ontario": "Ontario",
        "british columbia": "British Columbia",
        "alberta": "Alberta",
        "quebec": "Quebec",
        "québec": "quebec",  # French spelling with accent
        "manitoba": "Manitoba",
        "saskatchewan": "Saskatchewan",
        "nova scotia": "Nova Scotia",
        "new brunswick": "New Brunswick",
        "prince edward island": "Prince Edward Island",
        "newfoundland": "Newfoundland and Labrador",
        "northwest territories": "Northwest Territories",
        "nunavut": "Nunavut",
        "yukon": "Yukon",
    }

    PROVINCE_ABBREV = {
        " on ": "ontario", ", on": "ontario", "on,": "ontario", "ont": "ontario",
        " bc ": "british columbia", ", bc": "british columbia", "b.c.": "british columbia",
        " ab ": "alberta", ", ab": "alberta", "alta": "alberta",
        " qc ": "quebec", ", qc": "quebec", "(qc)": "quebec", "que": "quebec",
        "permis de conduire": "quebec",  # Quebec-specific French text
        " mb ": "manitoba", ", mb": "manitoba",
        " sk ": "saskatchewan", ", sk": "saskatchewan", "sask": "saskatchewan",
        " ns ": "nova scotia", ", ns": "nova scotia",
        " nb ": "new brunswick", ", nb": "new brunswick",
        " pe ": "prince edward island", ", pe": "prince edward island", "pei": "prince edward island",
        " nl ": "newfoundland", ", nl": "newfoundland", "nfld": "newfoundland",
        " nt ": "northwest territories", ", nt": "northwest territories", "nwt": "northwest territories",
        " nu ": "nunavut", ", nu": "nunavut",
        " yt ": "yukon", ", yt": "yukon",
    }

    # Document type mappings for keyword-based detection
    DL_TYPES = {
        "ontario": (DocumentType.ONTARIO_DRIVERS_LICENSE, "Ontario", "Ontario Driver's License"),
        "british columbia": (DocumentType.BC_DRIVERS_LICENSE, "British Columbia", "BC Driver's Licence"),
        "alberta": (DocumentType.ALBERTA_DRIVERS_LICENSE, "Alberta", "Alberta Driver's Licence"),
        "quebec": (DocumentType.QUEBEC_DRIVERS_LICENSE, "Quebec", "Quebec Driver's Licence"),
        "manitoba": (DocumentType.MANITOBA_DRIVERS_LICENSE, "Manitoba", "Manitoba Driver's Licence"),
        "saskatchewan": (DocumentType.SASKATCHEWAN_DRIVERS_LICENSE, "Saskatchewan", "Saskatchewan Driver's Licence"),
        "nova scotia": (DocumentType.NOVA_SCOTIA_DRIVERS_LICENSE, "Nova Scotia", "Nova Scotia Driver's Licence"),
        "new brunswick": (DocumentType.NEW_BRUNSWICK_DRIVERS_LICENSE, "New Brunswick", "New Brunswick Driver's Licence"),
        "prince edward island": (DocumentType.PEI_DRIVERS_LICENSE, "Prince Edward Island", "PEI Driver's Licence"),
        "newfoundland": (DocumentType.NEWFOUNDLAND_DRIVERS_LICENSE, "Newfoundland and Labrador", "Newfoundland Driver's Licence"),
        "northwest territories": (DocumentType.NWT_DRIVERS_LICENSE, "Northwest Territories", "NWT Driver's Licence"),
        "nunavut": (DocumentType.NUNAVUT_DRIVERS_LICENSE, "Nunavut", "Nunavut Driver's Licence"),
        "yukon": (DocumentType.YUKON_DRIVERS_LICENSE, "Yukon", "Yukon Driver's Licence"),
    }

    PHOTO_ID_TYPES = {
        "ontario": (DocumentType.ONTARIO_PHOTO_CARD, "Ontario", "Ontario Photo Card"),
        "british columbia": (DocumentType.BC_PHOTO_ID, "British Columbia", "BC Photo ID"),
        "alberta": (DocumentType.ALBERTA_PHOTO_ID, "Alberta", "Alberta Photo ID"),
    }

    # US State mappings
    US_STATE_MAPPING = {
        "california": "California",
        "texas": "Texas",
        "florida": "Florida",
        "new york": "New York",
        "illinois": "Illinois",
        "pennsylvania": "Pennsylvania",
        "ohio": "Ohio",
        "georgia": "Georgia",
        "michigan": "Michigan",
        "arizona": "Arizona",
        "washington": "Washington",
        "new jersey": "New Jersey",
        "nevada": "Nevada",
        "colorado": "Colorado",
        "oregon": "Oregon",
    }

    US_STATE_ABBREV = {
        " ca ": "california", ", ca": "california", "ca,": "california",
        " tx ": "texas", ", tx": "texas", "tx,": "texas",
        " fl ": "florida", ", fl": "florida", "fl,": "florida",
        " ny ": "new york", ", ny": "new york", "ny,": "new york",
        " il ": "illinois", ", il": "illinois", "il,": "illinois",
        " pa ": "pennsylvania", ", pa": "pennsylvania", "pa,": "pennsylvania",
        " oh ": "ohio", ", oh": "ohio", "oh,": "ohio",
        " ga ": "georgia", ", ga": "georgia", "ga,": "georgia",
        " mi ": "michigan", ", mi": "michigan", "mi,": "michigan",
        " az ": "arizona", ", az": "arizona", "az,": "arizona",
        " wa ": "washington", ", wa": "washington", "wa,": "washington",
        " nj ": "new jersey", ", nj": "new jersey", "nj,": "new jersey",
        " nv ": "nevada", ", nv": "nevada", "nv,": "nevada",
        " co ": "colorado", ", co": "colorado", "co,": "colorado",
        " or ": "oregon", ", or": "oregon", "or,": "oregon",
    }

    # US State DL types
    US_DL_TYPES = {
        "california": (DocumentType.CALIFORNIA_DRIVERS_LICENSE, "California", "California Driver's License"),
        "texas": (DocumentType.TEXAS_DRIVERS_LICENSE, "Texas", "Texas Driver's License"),
    }

    # Document number format patterns for fallback detection
    DOC_NUMBER_FORMATS = {
        # Ontario DL: Letter + 4 digits + hyphen + 5 digits + hyphen + 5 digits (e.g., M2754-10739-26003)
        DocumentType.ONTARIO_DRIVERS_LICENSE: {
            "pattern": r"^[A-Z]\d{4}-?\d{5}-?\d{5}$",
            "country": "Canada",
            "state_province": "Ontario",
            "name": "Ontario Driver's License"
        },
        # BC DL: Optional DL:/NDL: prefix + 7 digits
        DocumentType.BC_DRIVERS_LICENSE: {
            "pattern": r"^(NDL:?|DL:?)?\d{6,7}$",
            "country": "Canada",
            "state_province": "British Columbia",
            "name": "BC Driver's Licence"
        },
        # Alberta DL: 6 digits + optional hyphen + 3 digits (e.g., 134711-320 or 134711320)
        DocumentType.ALBERTA_DRIVERS_LICENSE: {
            "pattern": r"^\d{6}-?\d{3}$",
            "country": "Canada",
            "state_province": "Alberta",
            "name": "Alberta Driver's Licence"
        },
        # Quebec DL: Letter + 4 digits + 6 digits + 2 digits (e.g., A1234-567890-12)
        DocumentType.QUEBEC_DRIVERS_LICENSE: {
            "pattern": r"^[A-Z]\d{4}-?\d{6}-?\d{2}$",
            "country": "Canada",
            "state_province": "Quebec",
            "name": "Quebec Driver's Licence"
        },
        # Manitoba DL: 9 digits (DD/RÉF number)
        DocumentType.MANITOBA_DRIVERS_LICENSE: {
            "pattern": r"^\d{9}$",
            "country": "Canada",
            "state_province": "Manitoba",
            "name": "Manitoba Driver's Licence"
        },
        # Saskatchewan DL: 8 digits
        DocumentType.SASKATCHEWAN_DRIVERS_LICENSE: {
            "pattern": r"^\d{8}$",
            "country": "Canada",
            "state_province": "Saskatchewan",
            "name": "Saskatchewan Driver's Licence"
        },
        # Nova Scotia DL: 5 letters + 9 digits
        DocumentType.NOVA_SCOTIA_DRIVERS_LICENSE: {
            "pattern": r"^[A-Z]{5}\d{9}$",
            "country": "Canada",
            "state_province": "Nova Scotia",
            "name": "Nova Scotia Driver's Licence"
        },
        # New Brunswick DL: 7 digits
        DocumentType.NEW_BRUNSWICK_DRIVERS_LICENSE: {
            "pattern": r"^\d{7}$",
            "country": "Canada",
            "state_province": "New Brunswick",
            "name": "New Brunswick Driver's Licence"
        },
        # Newfoundland DL: Letter + 9 digits
        DocumentType.NEWFOUNDLAND_DRIVERS_LICENSE: {
            "pattern": r"^[A-Z]\d{9}$",
            "country": "Canada",
            "state_province": "Newfoundland and Labrador",
            "name": "Newfoundland Driver's Licence"
        },
        # Ontario Health Card: 10 digits + 2 letters (e.g., 1234567890AB)
        DocumentType.ONTARIO_HEALTH_CARD: {
            "pattern": r"^\d{10}[A-Z]{2}$",
            "country": "Canada",
            "state_province": "Ontario",
            "name": "Ontario Health Card"
        },
        # Canadian Passport: 2 letters + 6 digits
        DocumentType.CANADIAN_PASSPORT: {
            "pattern": r"^[A-Z]{2}\d{6}$",
            "country": "Canada",
            "state_province": None,
            "name": "Canadian Passport"
        },
        # Canada PR Card: 2 letters + 6 digits (similar to passport)
        DocumentType.CANADA_PR_CARD: {
            "pattern": r"^[A-Z]{2}\d{6}$",
            "country": "Canada",
            "state_province": None,
            "name": "Canada Permanent Residence Card"
        },
        # California DL: 1 letter + 7 digits (e.g., A1234567)
        DocumentType.CALIFORNIA_DRIVERS_LICENSE: {
            "pattern": r"^[A-Z]\d{7}$",
            "country": "United States",
            "state_province": "California",
            "name": "California Driver's License"
        },
        # Texas DL: 8 digits (e.g., 12345678)
        DocumentType.TEXAS_DRIVERS_LICENSE: {
            "pattern": r"^\d{8}$",
            "country": "United States",
            "state_province": "Texas",
            "name": "Texas Driver's License"
        },
    }

    @classmethod
    def detect(cls, extracted_data: Dict[str, Any], request_id: str = "") -> DocumentTypeInfo:
        """
        Detect document type from extracted fields.

        Detection order:
        1. Keywords + province/state/country (highest priority)
        2. Document number format (fallback)
        3. Pattern matching (final fallback)

        Args:
            extracted_data: Dictionary with extracted document fields
            request_id: Optional request ID for logging

        Returns:
            DocumentTypeInfo with detected type and confidence
        """
        log_prefix = f"[{request_id}]" if request_id else ""

        logger.info(f"{log_prefix} ========== DOCUMENT TYPE DETECTION ==========")

        document_number = extracted_data.get("document_number", "") or ""
        address = extracted_data.get("address", "") or ""
        country_code = (extracted_data.get("country_code", "") or "").upper()
        document_title = (extracted_data.get("document_title", "") or "").lower()
        full_text = cls._build_full_text(extracted_data)
        full_text_lower = full_text.lower()
        clean_doc_number = re.sub(r"[\s\-]", "", document_number.strip().upper())

        # Detect keywords
        has_passport_keyword = any(kw in full_text_lower for kw in cls.PASSPORT_KEYWORDS)
        has_dl_keyword = any(kw in full_text_lower for kw in cls.DL_KEYWORDS)
        has_health_card_keyword = any(kw in full_text_lower for kw in cls.HEALTH_CARD_KEYWORDS)
        has_photo_id_keyword = any(kw in full_text_lower for kw in cls.PHOTO_ID_KEYWORDS)
        has_pr_card_keyword = any(kw in full_text_lower for kw in cls.PR_CARD_KEYWORDS)

        # Special check: "permanent" is a strong indicator of PR card (not passport)
        has_permanent_keyword = "permanent" in full_text_lower or "permanent" in document_title

        # Check document_title for specific document types
        is_pr_card_by_title = "permanent resident" in document_title or "résident permanent" in document_title
        is_passport_by_title = "passport" in document_title and "permanent" not in document_title
        is_dl_by_title = "driver" in document_title or "licence" in document_title or "license" in document_title
        is_health_card_by_title = "health" in document_title
        is_photo_id_by_title = "photo" in document_title or "identification" in document_title or "identity" in document_title or "services card" in document_title or "bcid" in document_title

        # Detect province (Canada)
        detected_province = cls._detect_province(full_text_lower)

        # Detect US state
        detected_us_state = cls._detect_us_state(full_text_lower)

        # Detect country (check for Canada indicators)
        # Note: PR cards may have nationality (e.g., IND) as country_code, but are still Canadian documents
        has_government_of_canada = "government of canada" in full_text_lower or "gouvernement du canada" in full_text_lower
        is_canada = (
            "canada" in full_text_lower or
            country_code == "CAN" or
            detected_province is not None or
            has_government_of_canada
        )

        # Detect US indicators
        is_usa = (
            "united states" in full_text_lower or
            "usa" in full_text_lower or
            country_code == "USA" or
            detected_us_state is not None
        )

        logger.info(f"{log_prefix}   Keywords: passport={has_passport_keyword}, dl={has_dl_keyword}, "
                    f"health_card={has_health_card_keyword}, photo_id={has_photo_id_keyword}, pr_card={has_pr_card_keyword}, permanent={has_permanent_keyword}")
        logger.info(f"{log_prefix}   Document title: '{document_title}'")
        logger.info(f"{log_prefix}   By title: PR={is_pr_card_by_title}, photo_id={is_photo_id_by_title}, dl={is_dl_by_title}")
        logger.info(f"{log_prefix}   Province: {detected_province}, US State: {detected_us_state}")
        logger.info(f"{log_prefix}   Country code: {country_code}, Is Canada: {is_canada}, Is USA: {is_usa}")

        # ============================================================
        # STEP 1: KEYWORD-BASED DETECTION (highest priority)
        # ============================================================
        logger.info(f"{log_prefix}   STEP 1: Checking keywords + province/country...")

        # 1a. PERMANENT RESIDENCE CARD
        # Check for PR card keywords OR "permanent" keyword OR document_title indicates PR card
        if (has_pr_card_keyword or has_permanent_keyword or is_pr_card_by_title) and is_canada:
            logger.info(f"{log_prefix}   Detected Canada PR Card based on PR keyword + Canada")
            return DocumentTypeInfo(
                document_type=DocumentType.CANADA_PR_CARD.value,
                document_type_enum=DocumentType.CANADA_PR_CARD,
                confidence=0.9,
                country="Canada",
                state_province=None,
                document_name="Canada Permanent Residence Card",
                detected_features=["pr_card_keyword_found", "country: Canada"]
            )

        # 1b. PHOTO CARD / PHOTO ID
        # Check for Photo ID keywords OR document_title indicates Photo ID
        if (has_photo_id_keyword or is_photo_id_by_title) and not has_passport_keyword and not has_dl_keyword:
            logger.info(f"{log_prefix}   Photo Card/ID keyword found")

            if detected_province and detected_province in cls.PHOTO_ID_TYPES:
                doc_type, state_province, doc_name = cls.PHOTO_ID_TYPES[detected_province]
                logger.info(f"{log_prefix}   Detected {doc_name} based on Photo ID keyword + province '{detected_province}'")
                return DocumentTypeInfo(
                    document_type=doc_type.value,
                    document_type_enum=doc_type,
                    confidence=0.9,
                    country="Canada",
                    state_province=state_province,
                    document_name=doc_name,
                    detected_features=["photo_id_keyword_found", f"province: {detected_province}"]
                )
            else:
                logger.info(f"{log_prefix}   Detected Generic Photo ID (no specific province)")
                return DocumentTypeInfo(
                    document_type=DocumentType.GENERIC_PHOTO_ID.value,
                    document_type_enum=DocumentType.GENERIC_PHOTO_ID,
                    confidence=0.7,
                    country=None,
                    state_province=None,
                    document_name="Photo ID",
                    detected_features=["photo_id_keyword_found"]
                )

        # 1c. HEALTH CARD
        if has_health_card_keyword and not has_passport_keyword:
            logger.info(f"{log_prefix}   Health Card keyword found")

            if detected_province == "ontario" or "ohip" in full_text_lower:
                logger.info(f"{log_prefix}   Detected Ontario Health Card based on keyword")
                return DocumentTypeInfo(
                    document_type=DocumentType.ONTARIO_HEALTH_CARD.value,
                    document_type_enum=DocumentType.ONTARIO_HEALTH_CARD,
                    confidence=0.9,
                    country="Canada",
                    state_province="Ontario",
                    document_name="Ontario Health Card",
                    detected_features=["health_card_keyword_found", "province: ontario"]
                )

        # 1d. DRIVER'S LICENCE (Canada)
        if has_dl_keyword and not has_passport_keyword:
            logger.info(f"{log_prefix}   Driver's licence keyword found")

            # Check Canadian provinces first
            if detected_province and detected_province in cls.DL_TYPES:
                doc_type, state_province, doc_name = cls.DL_TYPES[detected_province]
                logger.info(f"{log_prefix}   Detected {doc_name} based on DL keyword + province '{detected_province}'")
                return DocumentTypeInfo(
                    document_type=doc_type.value,
                    document_type_enum=doc_type,
                    confidence=0.85,
                    country="Canada",
                    state_province=state_province,
                    document_name=doc_name,
                    detected_features=["dl_keyword_found", f"province: {detected_province}"]
                )

            # Check US states
            if detected_us_state and detected_us_state in cls.US_DL_TYPES:
                doc_type, state_name, doc_name = cls.US_DL_TYPES[detected_us_state]
                logger.info(f"{log_prefix}   Detected {doc_name} based on DL keyword + US state '{detected_us_state}'")
                return DocumentTypeInfo(
                    document_type=doc_type.value,
                    document_type_enum=doc_type,
                    confidence=0.85,
                    country="United States",
                    state_province=state_name,
                    document_name=doc_name,
                    detected_features=["dl_keyword_found", f"us_state: {detected_us_state}"]
                )

            # Check for generic US DL (US state detected but no specific validator)
            if detected_us_state and detected_us_state not in cls.US_DL_TYPES:
                state_name = cls.US_STATE_MAPPING.get(detected_us_state, detected_us_state.title())
                logger.info(f"{log_prefix}   Detected US DL for {state_name} (generic validator)")
                return DocumentTypeInfo(
                    document_type=DocumentType.US_DRIVERS_LICENSE.value,
                    document_type_enum=DocumentType.US_DRIVERS_LICENSE,
                    confidence=0.8,
                    country="United States",
                    state_province=state_name,
                    document_name=f"{state_name} Driver's License",
                    detected_features=["dl_keyword_found", f"us_state: {detected_us_state}"]
                )

        # 1e. PASSPORT
        if has_passport_keyword or is_passport_by_title:
            logger.info(f"{log_prefix}   Passport keyword found (country_code: {country_code or 'none'})")

            if country_code:
                # Check if this country code has a specific passport validator
                specific_passport_type = None
                for doc_type, patterns in DOCUMENT_PATTERNS.items():
                    pattern_country_code = patterns.get("country_code")
                    if pattern_country_code and pattern_country_code.upper() == country_code:
                        specific_passport_type = doc_type
                        break

                if specific_passport_type:
                    patterns = DOCUMENT_PATTERNS[specific_passport_type]
                    logger.info(f"{log_prefix}   Detected specific passport: {patterns['name']}")
                    return DocumentTypeInfo(
                        document_type=specific_passport_type.value,
                        document_type_enum=specific_passport_type,
                        confidence=0.9,
                        country=patterns.get("country"),
                        state_province=None,
                        document_name=patterns["name"],
                        detected_features=["passport_keyword_found", f"country_code: {country_code}"]
                    )
                elif country_code in COUNTRY_CODES:
                    country_name = COUNTRY_CODES[country_code]
                    dynamic_doc_type = f"{country_name.lower().replace(' ', '_')}_passport"
                    logger.info(f"{log_prefix}   Detected generic passport for {country_name}")
                    return DocumentTypeInfo(
                        document_type=dynamic_doc_type,
                        document_type_enum=DocumentType.GENERIC_PASSPORT,
                        confidence=0.85,
                        country=country_name,
                        state_province=None,
                        document_name=f"{country_name} Passport",
                        detected_features=["passport_keyword_found", f"country_code: {country_code}"]
                    )
            else:
                # Passport keyword found but no country_code - detect as generic passport
                logger.info(f"{log_prefix}   Detected Generic Passport (no country code)")
                return DocumentTypeInfo(
                    document_type=DocumentType.GENERIC_PASSPORT.value,
                    document_type_enum=DocumentType.GENERIC_PASSPORT,
                    confidence=0.75,
                    country=None,
                    state_province=None,
                    document_name="Passport",
                    detected_features=["passport_keyword_found", "no_country_code"]
                )

        # ============================================================
        # STEP 2: DOCUMENT NUMBER FORMAT DETECTION (fallback)
        # ============================================================
        logger.info(f"{log_prefix}   STEP 2: Checking document number format...")

        if clean_doc_number:
            for doc_type, format_info in cls.DOC_NUMBER_FORMATS.items():
                # Use original document number (with hyphens) for pattern matching
                doc_number_to_check = document_number.strip().upper()
                if re.match(format_info["pattern"], doc_number_to_check) or re.match(format_info["pattern"], clean_doc_number):
                    logger.info(f"{log_prefix}   Detected {format_info['name']} based on document number format")
                    return DocumentTypeInfo(
                        document_type=doc_type.value,
                        document_type_enum=doc_type,
                        confidence=0.7,
                        country=format_info["country"],
                        state_province=format_info["state_province"],
                        document_name=format_info["name"],
                        detected_features=["document_number_format_match", f"pattern: {format_info['pattern']}"]
                    )

        # ============================================================
        # STEP 3: PATTERN MATCHING (final fallback)
        # ============================================================
        logger.info(f"{log_prefix}   STEP 3: Pattern matching fallback...")

        best_match: Optional[DocumentTypeInfo] = None
        best_score = 0.0

        for doc_type, patterns in DOCUMENT_PATTERNS.items():
            score, features = cls._calculate_match_score(
                doc_type, patterns, document_number, address, full_text, country_code
            )

            logger.info(f"{log_prefix}   Checking {patterns['name']}: score={score:.2f}, features={features}")

            if score > best_score:
                best_score = score
                best_match = DocumentTypeInfo(
                    document_type=doc_type.value,
                    document_type_enum=doc_type,
                    confidence=score,
                    country=patterns.get("country"),
                    state_province=patterns.get("state_province"),
                    document_name=patterns["name"],
                    detected_features=features
                )

        # If no good match found
        if best_match is None or best_score < 0.3:
            # Last resort: check for passport keyword without country code
            if has_passport_keyword and country_code and country_code.upper() in COUNTRY_CODES:
                country_name = COUNTRY_CODES[country_code.upper()]
                dynamic_doc_type = f"{country_name.lower().replace(' ', '_')}_passport"
                logger.info(f"{log_prefix}   Result: {country_name} Passport (fallback)")
                return DocumentTypeInfo(
                    document_type=dynamic_doc_type,
                    document_type_enum=DocumentType.GENERIC_PASSPORT,
                    confidence=0.6,
                    country=country_name,
                    state_province=None,
                    document_name=f"{country_name} Passport",
                    detected_features=["passport_keyword_found", f"country_code: {country_code.upper()}"]
                )

            logger.info(f"{log_prefix}   Result: UNKNOWN (no confident match)")
            return DocumentTypeInfo(
                document_type=DocumentType.UNKNOWN.value,
                document_type_enum=DocumentType.UNKNOWN,
                confidence=0.0,
                country=None,
                state_province=None,
                document_name="Unknown Document",
                detected_features=[]
            )

        logger.info(f"{log_prefix}   Result: {best_match.document_name} (confidence: {best_match.confidence:.2f})")
        logger.info(f"{log_prefix} =============================================")

        return best_match

    @classmethod
    def _detect_province(cls, full_text_lower: str) -> Optional[str]:
        """Detect Canadian province from text."""
        # Check full province names
        for province_key in cls.PROVINCE_MAPPING.keys():
            if province_key in full_text_lower:
                # Normalize accented names to base name (e.g., "québec" -> "quebec")
                if province_key == "québec":
                    return "quebec"
                return province_key
        # Check abbreviations
        for abbrev, province in cls.PROVINCE_ABBREV.items():
            if abbrev in full_text_lower:
                return province
        return None

    @classmethod
    def _detect_us_state(cls, full_text_lower: str) -> Optional[str]:
        """Detect US state from text."""
        for state in cls.US_STATE_MAPPING.keys():
            if state in full_text_lower:
                return state
        for abbrev, state in cls.US_STATE_ABBREV.items():
            if abbrev in full_text_lower:
                return state
        return None

    @classmethod
    def _build_full_text(cls, data: Dict[str, Any]) -> str:
        """Combine all text fields for keyword searching."""
        parts = []
        for key, value in data.items():
            if value and isinstance(value, str):
                parts.append(value.lower())
        return " ".join(parts)

    @classmethod
    def _calculate_match_score(
        cls,
        doc_type: DocumentType,
        patterns: Dict[str, Any],
        document_number: str,
        address: str,
        full_text: str,
        country_code: str = ""
    ) -> tuple[float, list[str]]:
        """
        Calculate how well the document matches a specific type.

        Returns (score, detected_features)
        """
        score = 0.0
        features = []
        full_text_lower = full_text.lower()

        # Check country code match (for passport types)
        pattern_country_code = patterns.get("country_code")
        is_passport_type = "passport" in patterns.get("name", "").lower()

        if pattern_country_code and country_code and is_passport_type:
            if country_code.upper() == pattern_country_code.upper():
                score += 0.5
                features.append(f"country_code_match: {country_code}")

        # Check document number format
        license_format = patterns.get("license_format")
        if license_format and document_number:
            clean_number = document_number.strip().upper()
            if re.match(license_format, clean_number):
                score += 0.4
                features.append("document_number_format_match")

        # Check keywords in text
        keywords = patterns.get("keywords", [])
        matched_keywords = []
        for keyword in keywords:
            if keyword.lower() in full_text_lower:
                matched_keywords.append(keyword)

        if matched_keywords:
            keyword_score = min(len(matched_keywords) * 0.15, 0.45)
            score += keyword_score
            features.append(f"keywords_found: {', '.join(matched_keywords)}")

        # Ontario-specific: Check for Ontario address
        if doc_type == DocumentType.ONTARIO_DRIVERS_LICENSE:
            ontario_indicators = ["ontario", " on ", ", on", "on,", "toronto", "ottawa", "mississauga"]
            for indicator in ontario_indicators:
                if indicator.lower() in address.lower() or indicator.lower() in full_text_lower:
                    score += 0.15
                    features.append(f"ontario_address_indicator: {indicator}")
                    break

        return score, features

    @classmethod
    def is_ontario_drivers_license(cls, extracted_data: Dict[str, Any]) -> bool:
        """Quick check if document is likely an Ontario Driver's License."""
        doc_info = cls.detect(extracted_data)
        return doc_info.document_type_enum == DocumentType.ONTARIO_DRIVERS_LICENSE and doc_info.confidence >= 0.5
