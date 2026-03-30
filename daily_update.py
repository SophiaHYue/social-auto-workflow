"""
daily_update.py
────────────────
Orchestrates the full daily AI content generation and multi-platform
publishing workflow.

Usage:
    python daily_update.py [--topic "your topic here"] [--dry-run]

Options:
    --topic TEXT    Override the default AI-generated topic.
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
from scripts.generate_image import generate_image
from scripts.generate_video import generate_short_video
from scripts.generate_text import generate_all_text

# Platforms
from scripts.facebook import post_photo as fb_post_photo
from scripts.instagram import post_image as ig_post_image
from scripts.tiktok import post_video as tt_post_video
from scripts.youtube import upload_video as yt_upload_video
from scripts.pinterest import create_pin as pt_create_pin


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
    Execute the full daily workflow.

    Args:
        topic: Today's content topic / theme.
        dry_run: If True, generates content but skips all API publishing.

    Returns:
        Manifest dict with all published content IDs.
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

    # ── 1. Generate content ─────────────────────────────────
    logger.info("=== Generating content for topic: %s ===", topic)

    logger.info("Generating text …")
    text = generate_all_text(topic)
    caption = text["caption"]
    title = text["title"]
    hashtags_str = " ".join(text["hashtags"])
    full_caption = f"{caption}\n\n{hashtags_str}"
    manifest["content"]["text"] = text

    logger.info("Generating image …")
    image_path = generate_image(topic, output_str)
    manifest["content"]["image_path"] = image_path

    logger.info("Generating short video …")
    video_path = generate_short_video(caption, image_path=image_path, output_dir=output_str)
    manifest["content"]["video_path"] = video_path

    # ── 2. Publish ──────────────────────────────────────────
    if dry_run:
        logger.info("Dry-run mode – skipping all publishing.")
        _save_manifest(manifest, reports_dir)
        return manifest

    logger.info("=== Publishing content ===")

    # Facebook
    fb_result = _try(fb_post_photo, image_path, full_caption, platform="Facebook")
    manifest["published"]["facebook"] = fb_result

    # Instagram and Pinterest require a *publicly accessible* HTTPS URL for the
    # image.  In a production setup, upload the file to a CDN (e.g. S3, Cloudinary)
    # and pass the resulting URL here.  We log a clear warning and skip rather than
    # passing an invalid file:// URL that the APIs would reject.
    public_image_url = os.environ.get("PUBLIC_IMAGE_URL")

    if public_image_url:
        # Instagram
        ig_result = _try(
            ig_post_image,
            public_image_url,
            full_caption,
            platform="Instagram",
        )
        manifest["published"]["instagram"] = ig_result

        # Pinterest
        pt_result = _try(
            pt_create_pin,
            public_image_url,
            title,
            full_caption,
            platform="Pinterest",
        )
        manifest["published"]["pinterest"] = pt_result
    else:
        logger.warning(
            "PUBLIC_IMAGE_URL is not set – skipping Instagram and Pinterest. "
            "Upload the generated image to a public CDN and set this env var."
        )
        manifest["published"]["instagram"] = None
        manifest["published"]["pinterest"] = None

    # TikTok
    tt_result = _try(tt_post_video, video_path, full_caption, platform="TikTok")
    manifest["published"]["tiktok"] = tt_result

    # YouTube
    yt_result = _try(
        yt_upload_video,
        video_path,
        title,
        full_caption,
        text["hashtags"],
        platform="YouTube",
    )
    manifest["published"]["youtube"] = yt_result

    logger.info("=== Publishing complete ===")
    _save_manifest(manifest, reports_dir)
    return manifest


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Daily AI content generation & publishing")
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
