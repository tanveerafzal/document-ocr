"""
Test script to process all documents in a folder using the OCR Extract API.

Usage:
    python test_documents.py <folder_path> [--api-url URL] [--api-key KEY] [--concurrency N]

Example:
    python test_documents.py ./test_images --api-url http://localhost:8080 --api-key mykey --concurrency 5
"""

import os
import sys
import json
import argparse
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time


SUPPORTED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp'}

# Thread-safe counter and failure tracker
class Counter:
    def __init__(self):
        self.success = 0
        self.fail = 0
        self.failures = []  # List of (filename, document_type) tuples
        self.lock = threading.Lock()

    def add_success(self):
        with self.lock:
            self.success += 1

    def add_fail(self, filename: str = None, document_type: str = None):
        with self.lock:
            self.fail += 1
            if filename:
                self.failures.append((filename, document_type or "unknown"))


def process_document(file_path: Path, api_url: str, api_key: str) -> dict:
    """
    Send a document image to the OCR extract API and return the result.
    """
    url = f"{api_url.rstrip('/')}/ocr/extract/image?validate=true"

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


def process_single_file(image_file: Path, api_url: str, api_key: str, counter: Counter, total: int, print_lock: threading.Lock):
    """
    Process a single file (used by thread pool).
    """
    try:
        result = process_document(image_file, api_url, api_key)
        output_path = save_result(image_file, result)

        with print_lock:
            # Check if fake document detected
            fake_detection = result.get("fake_detection", {})
            is_fake = fake_detection.get("is_fake", False)

            if is_fake:
                print(f"\n{'*' * 50}")
                print(f"*** FAKE DOCUMENT *** {image_file.name}")
                print(f"{'*' * 50}")
                print(f"Reasons: {fake_detection.get('reasons', [])}")
                print()
                counter.add_fail(image_file.name, "FAKE_DOCUMENT")
            elif result.get("success"):
                counter.add_success()
                print(f"[OK] {image_file.name}")
            else:
                document_type = result.get("document_type", "unknown")
                counter.add_fail(image_file.name, document_type)
                print(f"[FAIL] {image_file.name}")

            # Print full response
            print("-" * 40)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print("-" * 40)
            print(f"Saved: {output_path.name}")
            print()

        return result

    except requests.exceptions.ConnectionError:
        with print_lock:
            counter.add_fail(image_file.name, "connection_error")
            print(f"[ERROR] {image_file.name} - Cannot connect to API")
        return None
    except Exception as e:
        with print_lock:
            counter.add_fail(image_file.name, "exception")
            print(f"[ERROR] {image_file.name} - {str(e)}")
        return None


def process_folder(folder_path: str, api_url: str, api_key: str, concurrency: int = 3):
    """
    Process all documents in a folder with optional concurrency.
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

    print(f"Found {len(image_files)} image(s) to process")
    print(f"Concurrency: {concurrency} parallel request(s)")
    print("-" * 60 + "\n")

    counter = Counter()
    print_lock = threading.Lock()
    total = len(image_files)
    start_time = time.time()

    if concurrency == 1:
        # Sequential processing
        for image_file in image_files:
            process_single_file(image_file, api_url, api_key, counter, total, print_lock)
    else:
        # Parallel processing
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = {
                executor.submit(
                    process_single_file,
                    image_file,
                    api_url,
                    api_key,
                    counter,
                    total,
                    print_lock
                ): image_file
                for image_file in image_files
            }

            # Wait for all to complete
            for future in as_completed(futures):
                pass  # Results already handled in process_single_file

    elapsed = time.time() - start_time
    print("-" * 60)
    print(f"\nCompleted: {counter.success} succeeded, {counter.fail} failed")
    print(f"Total time: {elapsed:.2f}s ({elapsed/total:.2f}s per document)")

    # Write failures to text file
    if counter.failures:
        failures_file = folder / "failures.txt"
        with open(failures_file, "w", encoding="utf-8") as f:
            for filename, doc_type in counter.failures:
                f.write(f"{filename} failed, document type is {doc_type}\n")
        print(f"\nFailures saved to: {failures_file}")


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
        default=os.environ.get("API_URL", "https://document-ocr-960587958424.northamerica-northeast2.run.app"),
        help="API base URL (default: http://localhost:8080 or API_URL env var)"
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("API_KEY", ""),
        help="API key for authentication (or set API_KEY env var)"
    )
    parser.add_argument(
        "--concurrency", "-c",
        type=int,
        default=1,
        help="Number of parallel requests (default: 1)"
    )

    args = parser.parse_args()

    if not args.api_key:
        print("Error: API key required. Use --api-key or set API_KEY environment variable")
        sys.exit(1)

    print(f"API URL: {args.api_url}")
    print(f"Folder: {args.folder}")
    print("-" * 60)

    process_folder(args.folder, args.api_url, args.api_key, args.concurrency)


if __name__ == "__main__":
    main()
