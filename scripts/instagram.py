"""
scripts/instagram.py
─────────────────────
Publishes content to an Instagram Business/Creator account via
the Meta Graph API (two-step container → publish flow).

Supports:
  - Single image posts
  - Reels (short video)
"""

import sys
import time
import logging
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import cfg

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.facebook.com/v19.0"


def _ig_user_id() -> str:
    uid = cfg.get("INSTAGRAM_USER_ID")
    if not uid:
        raise EnvironmentError("INSTAGRAM_USER_ID is not configured.")
    return uid


def _token() -> str:
    token = cfg.get("FACEBOOK_ACCESS_TOKEN")
    if not token:
        raise EnvironmentError("FACEBOOK_ACCESS_TOKEN is not configured.")
    return token


def _create_container(params: dict) -> str:
    """Create a media container and return its container_id."""
    url = f"{GRAPH_BASE}/{_ig_user_id()}/media"
    params["access_token"] = _token()
    resp = requests.post(url, data=params, timeout=60)
    resp.raise_for_status()
    container_id = resp.json()["id"]
    logger.debug("IG container created: %s", container_id)
    return container_id


def _publish_container(container_id: str) -> dict:
    """Publish a previously created container."""
    url = f"{GRAPH_BASE}/{_ig_user_id()}/media_publish"
    resp = requests.post(
        url,
        data={"creation_id": container_id, "access_token": _token()},
        timeout=60,
    )
    resp.raise_for_status()
    result = resp.json()
    logger.info("Instagram post published: %s", result)
    return result


def _wait_for_container(container_id: str, max_wait: int = 300) -> None:
    """Poll until the container status is FINISHED."""
    url = f"{GRAPH_BASE}/{container_id}"
    deadline = time.time() + max_wait
    while time.time() < deadline:
        resp = requests.get(
            url,
            params={"fields": "status_code", "access_token": _token()},
            timeout=30,
        )
        resp.raise_for_status()
        status = resp.json().get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"Instagram container {container_id} errored.")
        time.sleep(10)
    raise TimeoutError(f"Container {container_id} did not finish in time.")


def post_image(image_url: str, caption: str) -> dict:
    """
    Publish a single image post to Instagram.

    The image must be accessible via a *public* URL.

    Args:
        image_url: Publicly accessible URL of the image.
        caption: Post caption (may include hashtags).

    Returns:
        API response dict (contains 'id').
    """
    container_id = _create_container(
        {"image_url": image_url, "caption": caption}
    )
    _wait_for_container(container_id)
    return _publish_container(container_id)


def post_reel(video_url: str, caption: str, cover_url: str | None = None) -> dict:
    """
    Publish a Reel to Instagram.

    The video must be accessible via a *public* URL.

    Args:
        video_url: Publicly accessible URL of the video (.mp4).
        caption: Reel caption (may include hashtags).
        cover_url: Optional URL for the cover image.

    Returns:
        API response dict (contains 'id').
    """
    container_params: dict = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
    }
    if cover_url:
        container_params["cover_url"] = cover_url

    container_id = _create_container(container_params)
    _wait_for_container(container_id, max_wait=600)
    return _publish_container(container_id)


def get_media_insights(media_id: str) -> dict:
    """
    Retrieve insights for a published Instagram media object.

    Args:
        media_id: The IG media object ID.

    Returns:
        API response dict with insight metrics.
    """
    url = f"{GRAPH_BASE}/{media_id}/insights"
    resp = requests.get(
        url,
        params={
            "metric": "impressions,reach,likes,comments,shares,saved",
            "access_token": _token(),
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()
