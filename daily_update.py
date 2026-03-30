"""
daily_update.py
────────────────
Daily AI content generation and publishing workflow.

Steps:
  1. Generate a caption and hashtags using OpenAI API
  2. Generate an image using OpenAI DALL·E
  3. Generate a short video from the image using MoviePy
  4. Post to Facebook (photo post) and Instagram (image post)

Usage:
    python daily_update.py [--topic "your topic here"] [--dry-run]

Options:
    --topic TEXT    Content topic / theme (default: AI technology trends).
    --dry-run       Generate content but skip publishing.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# ── Logging setup ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("daily_update")

# ── Project root on sys.path ───────────────────────────────────
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from config.settings import cfg
from scripts.generate_image import generate_with_dalle
from scripts.generate_video import generate_short_video_moviepy
from scripts.generate_text import generate_caption, generate_hashtags
from scripts.facebook import post_photo as fb_post_photo
from scripts.instagram import post_image as ig_post_image


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────


def _ensure_dirs() -> tuple[Path, Path]:
    output_dir = Path(cfg["OUTPUT_DIR"])
    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir = Path(cfg["REPORTS_DIR"])
    reports_dir.mkdir(parents=True, exist_ok=True)
    return output_dir, reports_dir


def _save_manifest(manifest: dict, reports_dir: Path) -> None:
    """Persist a JSON manifest of today's published content IDs."""
    date_str = datetime.utcnow().strftime("%Y%m%d")
    manifest_path = reports_dir / f"manifest_{date_str}.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    logger.info("Manifest saved to %s", manifest_path)


def _try(func, *args, platform: str = "", **kwargs):
    """Call *func* and return its result; log + return None on any error."""
    try:
        return func(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        logger.error("Error publishing to %s: %s", platform or func.__name__, exc)
        return None


# ─────────────────────────────────────────────────────────────
# Main workflow
# ─────────────────────────────────────────────────────────────


def run(topic: str, dry_run: bool = False) -> dict:
    """
    Execute the daily workflow.

    Steps:
      1. Generate caption + hashtags via OpenAI
      2. Generate image via OpenAI DALL·E
      3. Generate short video via MoviePy
      4. Post to Facebook and Instagram

    Args:
        topic: Today's content topic / theme.
        dry_run: If True, generates content but skips all API publishing.

    Returns:
        Manifest dict with generated file paths and published content IDs.
    """
    output_dir, reports_dir = _ensure_dirs()
    output_str = str(output_dir)
    manifest: dict = {
        "date": datetime.utcnow().isoformat(),
        "topic": topic,
        "dry_run": dry_run,
        "content": {},
        "published": {},
    }

    # ── Step 1: Generate caption + hashtags using OpenAI ────────
    logger.info("=== Step 1: Generating text content via OpenAI ===")
    caption = generate_caption(topic)
    hashtags = generate_hashtags(topic)
    hashtags_str = " ".join(hashtags)
    full_caption = f"{caption}\n\n{hashtags_str}"
    manifest["content"]["caption"] = caption
    manifest["content"]["hashtags"] = hashtags

    # ── Step 2: Generate image using OpenAI DALL·E ──────────────
    logger.info("=== Step 2: Generating image via OpenAI DALL·E ===")
    image_path = generate_with_dalle(topic, output_str)
    manifest["content"]["image_path"] = image_path

    # ── Step 3: Generate short video using MoviePy ───────────────
    logger.info("=== Step 3: Generating short video via MoviePy ===")
    video_path = generate_short_video_moviepy(image_path, caption, output_str)
    manifest["content"]["video_path"] = video_path

    # ── Step 4: Publish ──────────────────────────────────────────
    if dry_run:
        logger.info("Dry-run mode – skipping publishing.")
        _save_manifest(manifest, reports_dir)
        return manifest

    logger.info("=== Step 4: Publishing to Facebook and Instagram ===")

    # Facebook – accepts a local file path directly
    fb_result = _try(fb_post_photo, image_path, full_caption, platform="Facebook")
    manifest["published"]["facebook"] = fb_result

    # Instagram requires a publicly accessible HTTPS URL.
    # Set PUBLIC_IMAGE_URL after uploading the generated image to a CDN
    # (e.g. S3, Cloudinary) to enable Instagram publishing.
    public_image_url = os.environ.get("PUBLIC_IMAGE_URL")
    if public_image_url:
        ig_result = _try(
            ig_post_image,
            public_image_url,
            full_caption,
            platform="Instagram",
        )
        manifest["published"]["instagram"] = ig_result
    else:
        logger.warning(
            "PUBLIC_IMAGE_URL is not set – skipping Instagram. "
            "Upload the generated image to a public CDN and set this env var."
        )
        manifest["published"]["instagram"] = None

    logger.info("=== Publishing complete ===")
    _save_manifest(manifest, reports_dir)
    return manifest


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Daily AI content generation & publishing to Facebook and Instagram"
    )
    parser.add_argument(
        "--topic",
        default="today's AI technology trends and innovations",
        help="Content topic / theme for today's post.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate content but skip all API publishing calls.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    result = run(args.topic, dry_run=args.dry_run)
    print(json.dumps(result, indent=2, ensure_ascii=False))

