"""
scripts/pinterest.py
─────────────────────
Creates Pins on a Pinterest board via the Pinterest API v5.
"""

import sys
import logging
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import cfg

logger = logging.getLogger(__name__)

API_BASE = "https://api.pinterest.com/v5"


def _token() -> str:
    token = cfg.get("PINTEREST_ACCESS_TOKEN")
    if not token:
        raise EnvironmentError("PINTEREST_ACCESS_TOKEN is not configured.")
    return token


def _board_id() -> str:
    board_id = cfg.get("PINTEREST_BOARD_ID")
    if not board_id:
        raise EnvironmentError("PINTEREST_BOARD_ID is not configured.")
    return board_id


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_token()}",
        "Content-Type": "application/json",
    }


def create_pin(
    image_url: str,
    title: str,
    description: str,
    link: str | None = None,
) -> dict:
    """
    Create a new Pin on the configured board.

    The image must be accessible via a *public* URL.

    Args:
        image_url: Publicly accessible URL of the image.
        title: Pin title (≤ 100 characters).
        description: Pin description (may include hashtags).
        link: Optional destination URL for the Pin.

    Returns:
        API response dict (contains 'id').
    """
    media_source: dict = {"source_type": "image_url", "url": image_url}
    pin_data: dict = {
        "board_id": _board_id(),
        "media_source": media_source,
        "title": title,
        "description": description,
    }
    if link:
        pin_data["link"] = link

    resp = requests.post(
        f"{API_BASE}/pins",
        headers=_headers(),
        json=pin_data,
        timeout=60,
    )
    resp.raise_for_status()
    result = resp.json()
    logger.info("Pinterest pin created: %s", result.get("id"))
    return result


def get_board_pins(bookmark: str | None = None, page_size: int = 25) -> dict:
    """
    List Pins on the configured board (for analytics / audit).

    Args:
        bookmark: Pagination cursor from the previous call.
        page_size: Number of Pins to return per page.

    Returns:
        API response dict with 'items' list and optional 'bookmark'.
    """
    params: dict = {"page_size": page_size}
    if bookmark:
        params["bookmark"] = bookmark

    resp = requests.get(
        f"{API_BASE}/boards/{_board_id()}/pins",
        headers=_headers(),
        params=params,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def get_pin_analytics(pin_id: str, start_date: str, end_date: str) -> dict:
    """
    Retrieve analytics for a single Pin.

    Args:
        pin_id: The Pin ID.
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.

    Returns:
        API response dict with impression / save / click metrics.
    """
    resp = requests.get(
        f"{API_BASE}/pins/{pin_id}/analytics",
        headers=_headers(),
        params={
            "start_date": start_date,
            "end_date": end_date,
            "metric_types": "IMPRESSION,SAVE,PIN_CLICK,OUTBOUND_CLICK",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()
