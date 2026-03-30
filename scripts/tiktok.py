"""
scripts/tiktok.py
──────────────────
Publishes videos to TikTok via the TikTok Business API (Content Posting API).

Flow: init upload → upload chunk → publish
"""

import sys
import os
import logging
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import cfg

logger = logging.getLogger(__name__)

API_BASE = "https://open.tiktokapis.com/v2"


def _token() -> str:
    token = cfg.get("TIKTOK_ACCESS_TOKEN")
    if not token:
        raise EnvironmentError("TIKTOK_ACCESS_TOKEN is not configured.")
    return token


def _open_id() -> str:
    open_id = cfg.get("TIKTOK_OPEN_ID")
    if not open_id:
        raise EnvironmentError("TIKTOK_OPEN_ID is not configured.")
    return open_id


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_token()}",
        "Content-Type": "application/json; charset=UTF-8",
    }


def post_video(
    video_path: str,
    caption: str,
    privacy_level: str = "PUBLIC_TO_EVERYONE",
) -> dict:
    """
    Upload and publish a video to TikTok.

    Args:
        video_path: Local path to the MP4 file.
        caption: Post caption (≤ 2200 characters, may include hashtags).
        privacy_level: One of PUBLIC_TO_EVERYONE, MUTUAL_FOLLOW_FRIENDS,
                       SELF_ONLY.

    Returns:
        API response dict from the publish step.
    """
    file_size = os.path.getsize(video_path)

    # Step 1 – Init upload
    init_resp = requests.post(
        f"{API_BASE}/post/publish/video/init/",
        headers=_headers(),
        json={
            "post_info": {
                "title": caption[:150],
                "privacy_level": privacy_level,
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": file_size,
                "chunk_size": file_size,
                "total_chunk_count": 1,
            },
        },
        timeout=30,
    )
    init_resp.raise_for_status()
    init_data = init_resp.json()["data"]
    publish_id = init_data["publish_id"]
    upload_url = init_data["upload_url"]

    # Step 2 – Upload video in a single chunk
    with open(video_path, "rb") as f:
        upload_resp = requests.put(
            upload_url,
            data=f,
            headers={
                "Content-Type": "video/mp4",
                "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
                "Content-Length": str(file_size),
            },
            timeout=300,
        )
    upload_resp.raise_for_status()

    logger.info("TikTok video uploaded, publish_id=%s", publish_id)

    # Step 3 – Check publish status
    status_resp = requests.post(
        f"{API_BASE}/post/publish/status/fetch/",
        headers=_headers(),
        json={"publish_id": publish_id},
        timeout=30,
    )
    status_resp.raise_for_status()
    result = status_resp.json()
    logger.info("TikTok publish status: %s", result)
    return result


def get_video_list(max_count: int = 20) -> dict:
    """
    Retrieve the user's recent video list for analytics purposes.

    Args:
        max_count: Number of videos to retrieve (max 20).

    Returns:
        API response dict with a list of video objects.
    """
    resp = requests.post(
        f"{API_BASE}/video/list/",
        headers=_headers(),
        params={"fields": "id,title,view_count,like_count,comment_count,share_count"},
        json={"max_count": max_count},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()
