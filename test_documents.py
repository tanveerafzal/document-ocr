"""
Test script to process all documents in a folder using the OCR Extract API.

Usage:
    python test_documents.py <folder_path> [--api-url URL] [--api-key KEY]

Example:
    python test_documents.py ./test_images --api-url http://localhost:8080 --api-key mykey
"""

import os
import sys
import json
import argparse
import requests
from pathlib import Path


SUPPORTED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp'}


def process_document(file_path: Path, api_url: str, api_key: str) -> dict:
    """
    Send a document image to the OCR extract API and return the result.
    """
    url = f"{api_url.rstrip('/')}/ocr/extract/image"

    headers = {
        "X-API-Key": api_key
    }

    with open(file_path, "rb") as f:
        files = {
            "file": (file_path.name, f, f"image/{file_path.suffix[1:]}")
        }
        response = requests.post(url, headers=headers, files=files)

    if response.status_code == 200:
        return response.json()
    else:
        return {
            "success": False,
            "error": f"API error: {response.status_code} - {response.text}"
        }


def save_result(file_path: Path, result: dict):
    """
    Save the extraction result as JSON with the same name as the image.
    """
    output_path = file_path.with_suffix(".json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    return output_path


def process_folder(folder_path: str, api_url: str, api_key: str):
    """
    Process all documents in a folder.
    """
    folder = Path(folder_path)

    if not folder.exists():
        print(f"Error: Folder '{folder_path}' does not exist")
        sys.exit(1)

    if not folder.is_dir():
        print(f"Error: '{folder_path}' is not a directory")
        sys.exit(1)

    # Find all supported image files
    image_files = [
        f for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    if not image_files:
        print(f"No supported images found in '{folder_path}'")
        print(f"Supported formats: {', '.join(SUPPORTED_EXTENSIONS)}")
        sys.exit(0)

    print(f"Found {len(image_files)} image(s) to process\n")
    print("-" * 60)

    success_count = 0
    fail_count = 0

    for i, image_file in enumerate(image_files, 1):
        print(f"\n[{i}/{len(image_files)}] Processing: {image_file.name}")

        try:
            result = process_document(image_file, api_url, api_key)
            output_path = save_result(image_file, result)

            if result.get("success"):
                success_count += 1
                print(f"  ✓ Success")
                print(f"    Name: {result.get('first_name')} {result.get('last_name')}")
                print(f"    Doc#: {result.get('document_number')}")
                print(f"    DOB: {result.get('date_of_birth')}")
            else:
                fail_count += 1
                print(f"  ✗ Failed: {result.get('error', 'Unknown error')}")
                if result.get("missing_fields"):
                    print(f"    Missing: {', '.join(result['missing_fields'])}")

            print(f"  → Saved: {output_path.name}")

        except requests.exceptions.ConnectionError:
            fail_count += 1
            print(f"  ✗ Error: Cannot connect to API at {api_url}")
            print("    Make sure the server is running")
        except Exception as e:
            fail_count += 1
            print(f"  ✗ Error: {str(e)}")

    print("\n" + "-" * 60)
    print(f"\nCompleted: {success_count} succeeded, {fail_count} failed")


def main():
    parser = argparse.ArgumentParser(
        description="Process documents in a folder using OCR Extract API"
    )
    parser.add_argument(
        "folder",
        help="Path to folder containing document images"
    )
    parser.add_argument(
        "--api-url",
        default=os.environ.get("API_URL", "http://localhost:8080"),
        help="API base URL (default: http://localhost:8080 or API_URL env var)"
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("API_KEY", ""),
        help="API key for authentication (or set API_KEY env var)"
    )

    args = parser.parse_args()

    if not args.api_key:
        print("Error: API key required. Use --api-key or set API_KEY environment variable")
        sys.exit(1)

    print(f"API URL: {args.api_url}")
    print(f"Folder: {args.folder}")
    print("-" * 60)

    process_folder(args.folder, args.api_url, args.api_key)


if __name__ == "__main__":
    main()
