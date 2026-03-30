"""
config/settings.py
──────────────────
Loads environment variables (from a .env file or the OS environment)
and exposes a single `cfg` dict used throughout the project.
"""

import os
from pathlib import Path

# Load .env file when present (python-dotenv is optional but recommended)
try:
    from dotenv import load_dotenv

    _env_path = Path(__file__).parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    pass  # proceed with OS-level environment variables only


def _require(key: str) -> str:
    """Return the value of *key* or raise if it is not set."""
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{key}' is not set. "
            "Copy config/api_keys.example.env to .env and fill in your credentials."
        )
    return value


def _optional(key: str, default: str = "") -> str:
    return os.getenv(key, default)


cfg = {
    # ── OpenAI ──────────────────────────────────────────────
    "OPENAI_API_KEY": _optional("OPENAI_API_KEY"),
    # ── Stable Diffusion ────────────────────────────────────
    "STABILITY_API_KEY": _optional("STABILITY_API_KEY"),
    # ── Runway ML ───────────────────────────────────────────
    "RUNWAY_API_KEY": _optional("RUNWAY_API_KEY"),
    # ── Pictory ─────────────────────────────────────────────
    "PICTORY_CLIENT_ID": _optional("PICTORY_CLIENT_ID"),
    "PICTORY_CLIENT_SECRET": _optional("PICTORY_CLIENT_SECRET"),
    # ── Facebook / Instagram ─────────────────────────────────
    "FACEBOOK_ACCESS_TOKEN": _optional("FACEBOOK_ACCESS_TOKEN"),
    "FACEBOOK_PAGE_ID": _optional("FACEBOOK_PAGE_ID"),
    "INSTAGRAM_USER_ID": _optional("INSTAGRAM_USER_ID"),
    # ── TikTok ───────────────────────────────────────────────
    "TIKTOK_ACCESS_TOKEN": _optional("TIKTOK_ACCESS_TOKEN"),
    "TIKTOK_OPEN_ID": _optional("TIKTOK_OPEN_ID"),
    # ── YouTube ──────────────────────────────────────────────
    "YOUTUBE_CLIENT_ID": _optional("YOUTUBE_CLIENT_ID"),
    "YOUTUBE_CLIENT_SECRET": _optional("YOUTUBE_CLIENT_SECRET"),
    "YOUTUBE_REFRESH_TOKEN": _optional("YOUTUBE_REFRESH_TOKEN"),
    # ── Pinterest ────────────────────────────────────────────
    "PINTEREST_ACCESS_TOKEN": _optional("PINTEREST_ACCESS_TOKEN"),
    "PINTEREST_BOARD_ID": _optional("PINTEREST_BOARD_ID"),
    # ── General ──────────────────────────────────────────────
    "OUTPUT_DIR": _optional("OUTPUT_DIR", "output"),
    "REPORTS_DIR": _optional("REPORTS_DIR", "reports"),
    # Optional: public CDN URL for the generated image (required by Instagram
    # and Pinterest APIs which do not accept local file paths).
    "PUBLIC_IMAGE_URL": _optional("PUBLIC_IMAGE_URL"),
}
