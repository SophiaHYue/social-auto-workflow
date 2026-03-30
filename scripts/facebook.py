"""
scripts/facebook.py
─────────────────────
Publishes content to a Facebook Page using the Meta Graph API.

Supports:
  - Photo posts (with caption)
  - Video posts (with title + description)
  - Text-only posts
"""

import sys
import logging
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import cfg

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.facebook.com/v19.0"


def _page_id() -> str:
    page_id = cfg.get("FACEBOOK_PAGE_ID")
    if not page_id:
        raise EnvironmentError("FACEBOOK_PAGE_ID is not configured.")
    return page_id


def _token() -> str:
    token = cfg.get("FACEBOOK_ACCESS_TOKEN")
    if not token:
        raise EnvironmentError("FACEBOOK_ACCESS_TOKEN is not configured.")
    return token


def post_photo(image_path: str, caption: str) -> dict:
    """
    Upload a photo to the Facebook Page feed.

    Args:
        image_path: Local path to the image file.
        caption: Post caption / message.

    Returns:
        API response dict (contains 'post_id').
    """
    url = f"{GRAPH_BASE}/{_page_id()}/photos"
    with open(image_path, "rb") as f:
        resp = requests.post(
            url,
            data={"caption": caption, "access_token": _token()},
            files={"source": f},
            timeout=60,
        )
    resp.raise_for_status()
    result = resp.json()
    logger.info("Facebook photo posted: %s", result)
    return result


def post_video(video_path: str, title: str, description: str) -> dict:
    """
    Upload a video to the Facebook Page feed.

    Args:
        video_path: Local path to the MP4 file.
        title: Video title.
        description: Video description / caption.

    Returns:
        API response dict (contains 'id').
    """
    url = f"{GRAPH_BASE}/{_page_id()}/videos"
    with open(video_path, "rb") as f:
        resp = requests.post(
            url,
            data={
                "title": title,
                "description": description,
                "access_token": _token(),
            },
            files={"source": f},
            timeout=300,
        )
    resp.raise_for_status()
    result = resp.json()
    logger.info("Facebook video posted: %s", result)
    return result


def post_text(message: str) -> dict:
    """
    Publish a text-only post to the Facebook Page feed.

    Args:
        message: Post body text.

    Returns:
        API response dict (contains 'id').
    """
    url = f"{GRAPH_BASE}/{_page_id()}/feed"
    resp = requests.post(
        url,
        data={"message": message, "access_token": _token()},
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()
    logger.info("Facebook text post published: %s", result)
    return result


def get_page_insights(metric: str = "page_impressions,page_engaged_users") -> dict:
    """
    Retrieve basic Page Insights for analytics.

    Args:
        metric: Comma-separated list of Page Insights metric names.

    Returns:
        API response dict with insight data.
    """
    url = f"{GRAPH_BASE}/{_page_id()}/insights"
    resp = requests.get(
        url,
        params={"metric": metric, "access_token": _token()},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()
