from enum import Enum
from typing import Optional, List
from pydantic import BaseModel


class DocumentType(str, Enum):
    """Supported document types for validation."""
    # Canadian Provinces
    ONTARIO_DRIVERS_LICENSE = "ontario_drivers_license"
    ONTARIO_HEALTH_CARD = "ontario_health_card"
    BC_DRIVERS_LICENSE = "bc_drivers_license"
    ALBERTA_DRIVERS_LICENSE = "alberta_drivers_license"
    QUEBEC_DRIVERS_LICENSE = "quebec_drivers_license"
    MANITOBA_DRIVERS_LICENSE = "manitoba_drivers_license"
    SASKATCHEWAN_DRIVERS_LICENSE = "saskatchewan_drivers_license"
    NOVA_SCOTIA_DRIVERS_LICENSE = "nova_scotia_drivers_license"
    NEW_BRUNSWICK_DRIVERS_LICENSE = "new_brunswick_drivers_license"
    PEI_DRIVERS_LICENSE = "pei_drivers_license"
    NEWFOUNDLAND_DRIVERS_LICENSE = "newfoundland_drivers_license"
    # Canadian Territories
    NWT_DRIVERS_LICENSE = "nwt_drivers_license"
    NUNAVUT_DRIVERS_LICENSE = "nunavut_drivers_license"
    YUKON_DRIVERS_LICENSE = "yukon_drivers_license"
    # Passports
    CANADIAN_PASSPORT = "canadian_passport"
    US_PASSPORT = "us_passport"
    UK_PASSPORT = "uk_passport"
    INDIA_PASSPORT = "india_passport"
    AUSTRALIA_PASSPORT = "australia_passport"
    GERMANY_PASSPORT = "germany_passport"
    FRANCE_PASSPORT = "france_passport"
    NIGERIA_PASSPORT = "nigeria_passport"
    CHINA_PASSPORT = "china_passport"
    COLOMBIA_PASSPORT = "colombia_passport"
    UKRAINE_PASSPORT = "ukraine_passport"
    GENERIC_PASSPORT = "generic_passport"
    # Photo Cards / Photo IDs
    ONTARIO_PHOTO_CARD = "ontario_photo_card"
    BC_PHOTO_ID = "bc_photo_id"
    ALBERTA_PHOTO_ID = "alberta_photo_id"
    GENERIC_PHOTO_ID = "generic_photo_id"
    # Permanent Residence Cards
    CANADA_PR_CARD = "canada_pr_card"
    # US State Driver's Licenses
    CALIFORNIA_DRIVERS_LICENSE = "california_drivers_license"
    TEXAS_DRIVERS_LICENSE = "texas_drivers_license"
    # Other Documents
    US_DRIVERS_LICENSE = "us_drivers_license"
    GENERIC_ID = "generic_id"
    UNKNOWN = "unknown"


class DocumentTypeInfo(BaseModel):
    """Information about detected document type."""
    document_type: str  # Can be enum value or dynamic like "philippines_passport"
    document_type_enum: Optional[DocumentType] = None  # For internal validator lookup
    confidence: float  # 0-1 confidence score
    country: Optional[str] = None
    state_province: Optional[str] = None
    document_name: str
    detected_features: List[str] = []


# Document type detection patterns and rules
DOCUMENT_PATTERNS = {
    DocumentType.ONTARIO_DRIVERS_LICENSE: {
        "name": "Ontario Driver's License",
        "country": "Canada",
        "state_province": "Ontario",
        "license_format": r"^[A-Z]\d{4}-\d{5}-\d{5}$",
        "keywords": ["ontario", "driver's licence", "driver licence", "class g", "class g1", "class g2"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.ONTARIO_HEALTH_CARD: {
        "name": "Ontario Health Card",
        "country": "Canada",
        "state_province": "Ontario",
        "license_format": r"^\d{10}[A-Z]{2}$",
        "keywords": ["ontario", "health card", "ohip", "ministry of health", "carte santé"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.BC_DRIVERS_LICENSE: {
        "name": "BC Driver's Licence",
        "country": "Canada",
        "state_province": "British Columbia",
        "license_format": r"^(NDL:?|DL:?)?\d{6,7}$",
        "keywords": ["british columbia", "bc", "driver's licence", "driver licence", "class 5", "class 7", "ndl"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.ALBERTA_DRIVERS_LICENSE: {
        "name": "Alberta Driver's Licence",
        "country": "Canada",
        "state_province": "Alberta",
        "license_format": r"^\d{6}-?\d{3}$",
        "keywords": ["alberta", "ab", "driver's licence", "driver licence", "class 5", "class 7", "gdl"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.QUEBEC_DRIVERS_LICENSE: {
        "name": "Quebec Driver's Licence",
        "country": "Canada",
        "state_province": "Quebec",
        "license_format": r"^[A-Z]\d{4}-?\d{6}-?\d{2}$",
        "keywords": ["quebec", "qc", "permis de conduire", "driver's licence", "classe 5", "probatoire"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.MANITOBA_DRIVERS_LICENSE: {
        "name": "Manitoba Driver's Licence",
        "country": "Canada",
        "state_province": "Manitoba",
        "license_format": r"^\d{9}$",
        "keywords": ["manitoba", "mb", "driver's licence", "driver licence", "class 5", "dd/réf", "dd/ref"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.SASKATCHEWAN_DRIVERS_LICENSE: {
        "name": "Saskatchewan Driver's Licence",
        "country": "Canada",
        "state_province": "Saskatchewan",
        "license_format": r"^\d{8}$",
        "keywords": ["saskatchewan", "sk", "sgi", "driver's licence", "driver licence", "class 5", "class 7"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.NOVA_SCOTIA_DRIVERS_LICENSE: {
        "name": "Nova Scotia Driver's Licence",
        "country": "Canada",
        "state_province": "Nova Scotia",
        "license_format": r"^[A-Z]{5}\d{9}$",
        "keywords": ["nova scotia", "ns", "driver's licence", "driver licence", "class 5", "class 7"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.NEW_BRUNSWICK_DRIVERS_LICENSE: {
        "name": "New Brunswick Driver's Licence",
        "country": "Canada",
        "state_province": "New Brunswick",
        "license_format": r"^\d{7}$",
        "keywords": ["new brunswick", "nouveau-brunswick", "nb", "driver's licence", "permis de conduire", "class 5", "class 7"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.PEI_DRIVERS_LICENSE: {
        "name": "PEI Driver's Licence",
        "country": "Canada",
        "state_province": "Prince Edward Island",
        "license_format": r"^\d{1,6}$",
        "keywords": ["prince edward island", "pei", "pe", "driver's licence", "driver licence", "class 5", "class 7"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.NEWFOUNDLAND_DRIVERS_LICENSE: {
        "name": "Newfoundland Driver's Licence",
        "country": "Canada",
        "state_province": "Newfoundland and Labrador",
        "license_format": r"^[A-Z]\d{9}$",
        "keywords": ["newfoundland", "labrador", "nl", "driver's licence", "driver licence", "class 5", "class 7"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.NWT_DRIVERS_LICENSE: {
        "name": "NWT Driver's Licence",
        "country": "Canada",
        "state_province": "Northwest Territories",
        "license_format": r"^\d{6}$",
        "keywords": ["northwest territories", "nwt", "nt", "driver's licence", "driver licence", "class 5", "class 7"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.NUNAVUT_DRIVERS_LICENSE: {
        "name": "Nunavut Driver's Licence",
        "country": "Canada",
        "state_province": "Nunavut",
        "license_format": r"^\d{6}$",
        "keywords": ["nunavut", "nu", "driver's licence", "driver licence", "class 5", "class 7"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.YUKON_DRIVERS_LICENSE: {
        "name": "Yukon Driver's Licence",
        "country": "Canada",
        "state_province": "Yukon",
        "license_format": r"^\d{6}$",
        "keywords": ["yukon", "yt", "yk", "driver's licence", "driver licence", "class 5", "class 7"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.CANADIAN_PASSPORT: {
        "name": "Canadian Passport",
        "country": "Canada",
        "country_code": "CAN",
        "state_province": None,
        "license_format": r"^[A-Z]{2}\d{6}$",
        "keywords": ["canada", "canadian", "passport", "passeport", "CAN"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.US_PASSPORT: {
        "name": "US Passport",
        "country": "United States",
        "country_code": "USA",
        "state_province": None,
        "license_format": r"^\d{9}$",
        "keywords": ["united states", "usa", "american", "passport", "USA"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.UK_PASSPORT: {
        "name": "UK Passport",
        "country": "United Kingdom",
        "country_code": "GBR",
        "state_province": None,
        "license_format": r"^\d{9}$",
        "keywords": ["united kingdom", "british", "uk", "gbr", "passport", "GBR"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.INDIA_PASSPORT: {
        "name": "India Passport",
        "country": "India",
        "country_code": "IND",
        "state_province": None,
        "license_format": r"^[A-Z]\d{7}$",
        "keywords": ["india", "indian", "republic of india", "passport", "IND"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.AUSTRALIA_PASSPORT: {
        "name": "Australia Passport",
        "country": "Australia",
        "country_code": "AUS",
        "state_province": None,
        "license_format": r"^[A-Z]{1,2}\d{7}$",
        "keywords": ["australia", "australian", "passport", "AUS"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.GERMANY_PASSPORT: {
        "name": "Germany Passport",
        "country": "Germany",
        "country_code": "DEU",
        "state_province": None,
        "license_format": r"^[A-Z0-9]{9}$",
        "keywords": ["germany", "german", "bundesrepublik", "deutschland", "passport", "reisepass", "DEU"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.FRANCE_PASSPORT: {
        "name": "France Passport",
        "country": "France",
        "country_code": "FRA",
        "state_province": None,
        "license_format": r"^[A-Z0-9]{9}$",
        "keywords": ["france", "french", "république française", "passport", "passeport", "FRA"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.NIGERIA_PASSPORT: {
        "name": "Nigeria Passport",
        "country": "Nigeria",
        "country_code": "NGA",
        "state_province": None,
        "license_format": r"^[A-Z]\d{8}$",
        "keywords": ["nigeria", "nigerian", "federal republic of nigeria", "passport", "NGA"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.CHINA_PASSPORT: {
        "name": "China Passport",
        "country": "China",
        "country_code": "CHN",
        "state_province": None,
        "license_format": r"^[EGD]\d{8}$",
        "keywords": ["china", "chinese", "people's republic of china", "中华人民共和国", "passport", "CHN"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.COLOMBIA_PASSPORT: {
        "name": "Colombia Passport",
        "country": "Colombia",
        "country_code": "COL",
        "state_province": None,
        "license_format": r"^[A-Z]{2}\d{7}$",
        "keywords": ["colombia", "colombian", "república de colombia", "passport", "pasaporte", "COL"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.UKRAINE_PASSPORT: {
        "name": "Ukraine Passport",
        "country": "Ukraine",
        "country_code": "UKR",
        "state_province": None,
        "license_format": r"^[A-Z]{2}\d{6}$",
        "keywords": ["ukraine", "ukrainian", "україна", "passport", "паспорт", "UKR"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.GENERIC_PASSPORT: {
        "name": "International Passport",
        "country": None,
        "country_code": None,
        "state_province": None,
        "license_format": r"^[A-Z0-9]{6,12}$",
        "keywords": ["passport", "passeport", "pasaporte", "reisepass", "паспорт"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.CANADA_PR_CARD: {
        "name": "Canada Permanent Residence Card",
        "country": "Canada",
        "country_code": "CAN",
        "state_province": None,
        "license_format": r"^[A-Z]{2}\d{6}$",
        "keywords": ["permanent resident", "permanent residence", "résident permanent", "pr card", "immigration", "canada"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.CALIFORNIA_DRIVERS_LICENSE: {
        "name": "California Driver's License",
        "country": "United States",
        "state_province": "California",
        "license_format": r"^[A-Z]\d{7}$",
        "keywords": ["california", "ca", "driver license", "driver's license", "dmv", "state of california"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.TEXAS_DRIVERS_LICENSE: {
        "name": "Texas Driver's License",
        "country": "United States",
        "state_province": "Texas",
        "license_format": r"^\d{8}$",
        "keywords": ["texas", "tx", "driver license", "driver's license", "dps", "state of texas"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
    DocumentType.US_DRIVERS_LICENSE: {
        "name": "US Driver's License",
        "country": "United States",
        "state_province": None,
        "license_format": r"^[A-Z0-9]{6,15}$",
        "keywords": ["driver license", "driver's license", "dmv"],
        "required_fields": ["first_name", "last_name", "date_of_birth", "expiry_date", "document_number"],
    },
}


# Comprehensive ISO 3166-1 alpha-3 country codes for passport detection
COUNTRY_CODES = {
    # Africa
    "DZA": "Algeria", "AGO": "Angola", "BEN": "Benin", "BWA": "Botswana", "BFA": "Burkina Faso",
    "BDI": "Burundi", "CMR": "Cameroon", "CPV": "Cape Verde", "CAF": "Central African Republic",
    "TCD": "Chad", "COM": "Comoros", "COG": "Congo", "COD": "DR Congo", "CIV": "Ivory Coast",
    "DJI": "Djibouti", "EGY": "Egypt", "GNQ": "Equatorial Guinea", "ERI": "Eritrea", "SWZ": "Eswatini",
    "ETH": "Ethiopia", "GAB": "Gabon", "GMB": "Gambia", "GHA": "Ghana", "GIN": "Guinea",
    "GNB": "Guinea-Bissau", "KEN": "Kenya", "LSO": "Lesotho", "LBR": "Liberia", "LBY": "Libya",
    "MDG": "Madagascar", "MWI": "Malawi", "MLI": "Mali", "MRT": "Mauritania", "MUS": "Mauritius",
    "MAR": "Morocco", "MOZ": "Mozambique", "NAM": "Namibia", "NER": "Niger", "NGA": "Nigeria",
    "RWA": "Rwanda", "STP": "Sao Tome and Principe", "SEN": "Senegal", "SYC": "Seychelles",
    "SLE": "Sierra Leone", "SOM": "Somalia", "ZAF": "South Africa", "SSD": "South Sudan",
    "SDN": "Sudan", "TZA": "Tanzania", "TGO": "Togo", "TUN": "Tunisia", "UGA": "Uganda",
    "ZMB": "Zambia", "ZWE": "Zimbabwe",

    # Americas
    "ARG": "Argentina", "BHS": "Bahamas", "BRB": "Barbados", "BLZ": "Belize", "BOL": "Bolivia",
    "BRA": "Brazil", "CAN": "Canada", "CHL": "Chile", "COL": "Colombia", "CRI": "Costa Rica",
    "CUB": "Cuba", "DMA": "Dominica", "DOM": "Dominican Republic", "ECU": "Ecuador",
    "SLV": "El Salvador", "GRD": "Grenada", "GTM": "Guatemala", "GUY": "Guyana", "HTI": "Haiti",
    "HND": "Honduras", "JAM": "Jamaica", "MEX": "Mexico", "NIC": "Nicaragua", "PAN": "Panama",
    "PRY": "Paraguay", "PER": "Peru", "KNA": "Saint Kitts and Nevis", "LCA": "Saint Lucia",
    "VCT": "Saint Vincent and the Grenadines", "SUR": "Suriname", "TTO": "Trinidad and Tobago",
    "USA": "United States", "URY": "Uruguay", "VEN": "Venezuela",

    # Asia
    "AFG": "Afghanistan", "ARM": "Armenia", "AZE": "Azerbaijan", "BHR": "Bahrain", "BGD": "Bangladesh",
    "BTN": "Bhutan", "BRN": "Brunei", "KHM": "Cambodia", "CHN": "China", "CYP": "Cyprus",
    "GEO": "Georgia", "IND": "India", "IDN": "Indonesia", "IRN": "Iran", "IRQ": "Iraq",
    "ISR": "Israel", "JPN": "Japan", "JOR": "Jordan", "KAZ": "Kazakhstan", "KWT": "Kuwait",
    "KGZ": "Kyrgyzstan", "LAO": "Laos", "LBN": "Lebanon", "MYS": "Malaysia", "MDV": "Maldives",
    "MNG": "Mongolia", "MMR": "Myanmar", "NPL": "Nepal", "PRK": "North Korea", "OMN": "Oman",
    "PAK": "Pakistan", "PSE": "Palestine", "PHL": "Philippines", "QAT": "Qatar", "SAU": "Saudi Arabia",
    "SGP": "Singapore", "KOR": "South Korea", "LKA": "Sri Lanka", "SYR": "Syria", "TWN": "Taiwan",
    "TJK": "Tajikistan", "THA": "Thailand", "TLS": "Timor-Leste", "TUR": "Turkey", "TKM": "Turkmenistan",
    "ARE": "United Arab Emirates", "UZB": "Uzbekistan", "VNM": "Vietnam", "YEM": "Yemen",

    # Europe
    "ALB": "Albania", "AND": "Andorra", "AUT": "Austria", "BLR": "Belarus", "BEL": "Belgium",
    "BIH": "Bosnia and Herzegovina", "BGR": "Bulgaria", "HRV": "Croatia", "CZE": "Czech Republic",
    "DNK": "Denmark", "EST": "Estonia", "FIN": "Finland", "FRA": "France", "DEU": "Germany",
    "GRC": "Greece", "HUN": "Hungary", "ISL": "Iceland", "IRL": "Ireland", "ITA": "Italy",
    "XKX": "Kosovo", "LVA": "Latvia", "LIE": "Liechtenstein", "LTU": "Lithuania", "LUX": "Luxembourg",
    "MLT": "Malta", "MDA": "Moldova", "MCO": "Monaco", "MNE": "Montenegro", "NLD": "Netherlands",
    "MKD": "North Macedonia", "NOR": "Norway", "POL": "Poland", "PRT": "Portugal", "ROU": "Romania",
    "RUS": "Russia", "SMR": "San Marino", "SRB": "Serbia", "SVK": "Slovakia", "SVN": "Slovenia",
    "ESP": "Spain", "SWE": "Sweden", "CHE": "Switzerland", "UKR": "Ukraine", "GBR": "United Kingdom",
    "VAT": "Vatican City",

    # Oceania
    "AUS": "Australia", "FJI": "Fiji", "KIR": "Kiribati", "MHL": "Marshall Islands",
    "FSM": "Micronesia", "NRU": "Nauru", "NZL": "New Zealand", "PLW": "Palau",
    "PNG": "Papua New Guinea", "WSM": "Samoa", "SLB": "Solomon Islands", "TON": "Tonga",
    "TUV": "Tuvalu", "VUT": "Vanuatu",
}
