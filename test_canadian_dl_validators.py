"""
Test script for Canadian Driver's Licence validators.
Run with: python test_canadian_dl_validators.py
"""

import asyncio
from datetime import datetime, timedelta

# Import all validators
from app.services.validators.ontario_dl import OntarioDriversLicenseValidator
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


def get_test_dates():
    """Generate realistic test dates."""
    today = datetime.now()
    dob = today - timedelta(days=365 * 30)  # 30 years old
    issue = today - timedelta(days=365 * 2)  # Issued 2 years ago
    expiry = today + timedelta(days=365 * 3)  # Expires in 3 years

    return {
        "dob": dob.strftime("%Y-%m-%d"),
        "issue": issue.strftime("%Y-%m-%d"),
        "expiry_birthday": dob.replace(year=today.year + 3).strftime("%Y-%m-%d"),
        "expiry": expiry.strftime("%Y-%m-%d"),
    }


# Test cases for each province/territory
TEST_CASES = []
dates = get_test_dates()

# Calculate DOB-encoded number for Ontario (YYMMDD)
dob_date = datetime.strptime(dates["dob"], "%Y-%m-%d")
dob_encoded = dob_date.strftime("%y%m%d")
# Ontario format: A1234-12345-12345 (Letter + 4 digits - 5 digits - 5 digits)
# Last 6 digits of the number (without hyphens) encode DOB as YYMMDD
# Example: S1234-56789-60122 -> without hyphens = S12345678960122 -> last 6 = 960122 = DOB
ontario_dl_number = f"S1234-5678{dob_encoded[0]}-{dob_encoded[1:]}"

TEST_CASES = [
    # Ontario - Letter + 4 digits + hyphen + 5 digits + hyphen + 5 digits (last 6 = DOB YYMMDD)
    {
        "name": "Ontario DL (Valid)",
        "validator": OntarioDriversLicenseValidator(),
        "data": {
            "document_number": ontario_dl_number,
            "full_name": "SMITH, JOHN MICHAEL",
            "date_of_birth": dates["dob"],
            "issue_date": dates["issue"],
            "expiry_date": dates["expiry_birthday"],
        },
        "expect_pass": True,
    },
    {
        "name": "Ontario DL (Invalid - Wrong first letter)",
        "validator": OntarioDriversLicenseValidator(),
        "data": {
            "document_number": "A1234-12345-12345",
            "full_name": "SMITH, JOHN",
            "date_of_birth": dates["dob"],
            "expiry_date": dates["expiry_birthday"],
        },
        "expect_pass": False,
    },

    # British Columbia - 6-7 digits
    {
        "name": "BC DL (Valid)",
        "validator": BCDriversLicenseValidator(),
        "data": {
            "document_number": "1234567",
            "full_name": "JONES, SARAH",
            "date_of_birth": dates["dob"],
            "issue_date": dates["issue"],
            "expiry_date": dates["expiry_birthday"],
        },
        "expect_pass": True,
    },

    # Alberta - 9 digits
    {
        "name": "Alberta DL (Valid)",
        "validator": AlbertaDriversLicenseValidator(),
        "data": {
            "document_number": "123456-789",
            "full_name": "WILLIAMS, ROBERT",
            "date_of_birth": dates["dob"],
            "issue_date": dates["issue"],
            "expiry_date": dates["expiry_birthday"],
        },
        "expect_pass": True,
    },

    # Quebec - Letter + 12 digits
    {
        "name": "Quebec DL (Valid)",
        "validator": QuebecDriversLicenseValidator(),
        "data": {
            "document_number": "T1234-567890-12",
            "full_name": "TREMBLAY, MARIE",
            "date_of_birth": dates["dob"],
            "issue_date": dates["issue"],
            "expiry_date": dates["expiry_birthday"],
        },
        "expect_pass": True,
    },
    {
        "name": "Quebec DL (Invalid - Wrong letter)",
        "validator": QuebecDriversLicenseValidator(),
        "data": {
            "document_number": "A1234-567890-12",
            "full_name": "TREMBLAY, MARIE",
            "date_of_birth": dates["dob"],
            "expiry_date": dates["expiry_birthday"],
        },
        "expect_pass": False,
    },

    # Manitoba - 4 letters + 6 digits
    {
        "name": "Manitoba DL (Valid)",
        "validator": ManitobaDriversLicenseValidator(),
        "data": {
            "document_number": "ABCD-123-456",
            "full_name": "ANDERSON, DAVID",
            "date_of_birth": dates["dob"],
            "issue_date": dates["issue"],
            "expiry_date": dates["expiry_birthday"],
        },
        "expect_pass": True,
    },

    # Saskatchewan - 8 digits
    {
        "name": "Saskatchewan DL (Valid)",
        "validator": SaskatchewanDriversLicenseValidator(),
        "data": {
            "document_number": "12345678",
            "full_name": "JOHNSON, EMILY",
            "date_of_birth": dates["dob"],
            "issue_date": dates["issue"],
            "expiry_date": dates["expiry_birthday"],
        },
        "expect_pass": True,
    },
    {
        "name": "Saskatchewan DL (Invalid - Too few digits)",
        "validator": SaskatchewanDriversLicenseValidator(),
        "data": {
            "document_number": "12345",
            "full_name": "JOHNSON, EMILY",
            "date_of_birth": dates["dob"],
            "expiry_date": dates["expiry"],
        },
        "expect_pass": False,
    },

    # Nova Scotia - 5 letters + 9 digits
    {
        "name": "Nova Scotia DL (Valid)",
        "validator": NovaScotiaDriversLicenseValidator(),
        "data": {
            "document_number": "MACDO123456789",
            "full_name": "MACDONALD, JAMES",
            "date_of_birth": dates["dob"],
            "issue_date": dates["issue"],
            "expiry_date": dates["expiry_birthday"],
        },
        "expect_pass": True,
    },

    # New Brunswick - 7 digits
    {
        "name": "New Brunswick DL (Valid)",
        "validator": NewBrunswickDriversLicenseValidator(),
        "data": {
            "document_number": "1234567",
            "full_name": "LEBLANC, NICOLE",
            "date_of_birth": dates["dob"],
            "issue_date": dates["issue"],
            "expiry_date": dates["expiry_birthday"],
        },
        "expect_pass": True,
    },

    # PEI - 1-6 digits
    {
        "name": "PEI DL (Valid)",
        "validator": PEIDriversLicenseValidator(),
        "data": {
            "document_number": "123456",
            "full_name": "CAMPBELL, ANNE",
            "date_of_birth": dates["dob"],
            "issue_date": dates["issue"],
            "expiry_date": dates["expiry_birthday"],
        },
        "expect_pass": True,
    },
    {
        "name": "PEI DL (Valid - Short number)",
        "validator": PEIDriversLicenseValidator(),
        "data": {
            "document_number": "123",
            "full_name": "CAMPBELL, ANNE",
            "date_of_birth": dates["dob"],
            "expiry_date": dates["expiry_birthday"],
        },
        "expect_pass": True,
    },

    # Newfoundland - Letter + 9 digits
    {
        "name": "Newfoundland DL (Valid)",
        "validator": NewfoundlandDriversLicenseValidator(),
        "data": {
            "document_number": "O123456789",
            "full_name": "O'BRIEN, PATRICK",
            "date_of_birth": dates["dob"],
            "issue_date": dates["issue"],
            "expiry_date": dates["expiry_birthday"],
        },
        "expect_pass": True,
    },
    {
        "name": "Newfoundland DL (Invalid - Wrong letter)",
        "validator": NewfoundlandDriversLicenseValidator(),
        "data": {
            "document_number": "A123456789",
            "full_name": "O'BRIEN, PATRICK",
            "date_of_birth": dates["dob"],
            "expiry_date": dates["expiry"],
        },
        "expect_pass": False,
    },

    # NWT - 6 digits
    {
        "name": "NWT DL (Valid)",
        "validator": NWTDriversLicenseValidator(),
        "data": {
            "document_number": "123456",
            "full_name": "TOOTOO, MARY",
            "date_of_birth": dates["dob"],
            "issue_date": dates["issue"],
            "expiry_date": dates["expiry_birthday"],
        },
        "expect_pass": True,
    },

    # Nunavut - 6 digits
    {
        "name": "Nunavut DL (Valid)",
        "validator": NunavutDriversLicenseValidator(),
        "data": {
            "document_number": "123456",
            "full_name": "IQALUK, PETER",
            "date_of_birth": dates["dob"],
            "issue_date": dates["issue"],
            "expiry_date": dates["expiry_birthday"],
        },
        "expect_pass": True,
    },

    # Yukon - 6 digits
    {
        "name": "Yukon DL (Valid)",
        "validator": YukonDriversLicenseValidator(),
        "data": {
            "document_number": "123456",
            "full_name": "GOLD, SARAH",
            "date_of_birth": dates["dob"],
            "issue_date": dates["issue"],
            "expiry_date": dates["expiry_birthday"],
        },
        "expect_pass": True,
    },

    # Test underage scenarios
    {
        "name": "Ontario DL (Invalid - Underage)",
        "validator": OntarioDriversLicenseValidator(),
        "data": {
            "document_number": "S1234-12345-112345",
            "full_name": "SMITH, TOMMY",
            "date_of_birth": (datetime.now() - timedelta(days=365 * 14)).strftime("%Y-%m-%d"),
            "expiry_date": dates["expiry"],
        },
        "expect_pass": False,
    },

    # Test expired document
    {
        "name": "BC DL (Invalid - Expired)",
        "validator": BCDriversLicenseValidator(),
        "data": {
            "document_number": "1234567",
            "full_name": "EXPIRED, TEST",
            "date_of_birth": dates["dob"],
            "expiry_date": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
        },
        "expect_pass": False,
    },
]


async def run_tests():
    """Run all test cases."""
    print("=" * 70)
    print("CANADIAN DRIVER'S LICENCE VALIDATOR TESTS")
    print("=" * 70)
    print()

    passed = 0
    failed = 0

    for test in TEST_CASES:
        result = await test["validator"].validate(test["data"])

        # Check if result matches expectation
        is_pass = result.status.value in ["passed", "warning"]
        expected = test["expect_pass"]
        test_passed = is_pass == expected

        if test_passed:
            passed += 1
            status_icon = "[PASS]"
        else:
            failed += 1
            status_icon = "[FAIL]"

        print(f"{status_icon} {test['name']}")
        print(f"  Document#: {test['data'].get('document_number', 'N/A')}")
        print(f"  Result: {result.status.value.upper()} - {result.message}")
        if not test_passed:
            print(f"  EXPECTED: {'PASS' if expected else 'FAIL'}, GOT: {'PASS' if is_pass else 'FAIL'}")
        if result.details.get("issues"):
            print(f"  Issues: {result.details['issues']}")
        if result.details.get("warnings"):
            print(f"  Warnings: {result.details['warnings']}")
        print()

    print("=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(TEST_CASES)} tests")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_tests())
    exit(0 if success else 1)
