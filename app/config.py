import os
import subprocess
from datetime import datetime


# Verifik API Configuration
VERIFIK_API_ENABLED = os.environ.get("VERIFIK_API_ENABLED", "false").lower() == "true"
VERIFIK_API_TOKEN = os.environ.get("VERIFIK_API_TOKEN", "")
VERIFIK_API_BASE_URL = os.environ.get("VERIFIK_API_BASE_URL", "https://api.verifik.co/v2")


def get_build_number() -> str:
    """Get build number from environment or generate from git/timestamp."""
    # First check environment variable
    env_build = os.environ.get("BUILD_NUMBER")
    if env_build:
        return env_build

    # Try to get git commit hash
    try:
        git_hash = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()

        # Try to get branch name
        try:
            branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                stderr=subprocess.DEVNULL
            ).decode("utf-8").strip()
        except Exception:
            branch = "unknown"

        return f"{branch}-{git_hash}"
    except Exception:
        pass

    # Fallback to timestamp
    return f"build-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


BUILD_NUMBER = get_build_number()
