"""
scripts/youtube.py
───────────────────
Uploads videos to YouTube using the YouTube Data API v3
(OAuth 2.0 with a stored refresh token).
"""

import sys
import os
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import cfg

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_URI = "https://oauth2.googleapis.com/token"


def _build_service():
    """Build and return an authenticated YouTube API service client."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build  # type: ignore

    creds = Credentials(
        token=None,
        refresh_token=cfg["YOUTUBE_REFRESH_TOKEN"],
        token_uri=TOKEN_URI,
        client_id=cfg["YOUTUBE_CLIENT_ID"],
        client_secret=cfg["YOUTUBE_CLIENT_SECRET"],
        scopes=SCOPES,
    )
    return build("youtube", "v3", credentials=creds)


def upload_video(
    video_path: str,
    title: str,
    description: str,
    tags: list[str] | None = None,
    category_id: str = "28",  # 28 = Science & Technology
    privacy_status: str = "public",
) -> dict:
    """
    Upload a video to YouTube.

    Args:
        video_path: Local path to the MP4 file.
        title: Video title (≤ 100 characters).
        description: Video description.
        tags: List of keyword tags.
        category_id: YouTube category numeric ID string.
        privacy_status: 'public', 'private', or 'unlisted'.

    Returns:
        Insert API response dict (contains 'id' = the new video ID).
    """
    from googleapiclient.http import MediaFileUpload  # type: ignore

    youtube = _build_service()

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags or [],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy_status,
        },
    }

    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        _, response = request.next_chunk()

    logger.info("YouTube video uploaded: id=%s", response.get("id"))
    return response


def get_video_analytics(video_id: str) -> dict:
    """
    Retrieve basic analytics for a YouTube video via the YouTube Analytics API.

    Args:
        video_id: The YouTube video ID.

    Returns:
        Dict with view / like / comment counts from the Data API.
    """
    youtube = _build_service()
    response = (
        youtube.videos()
        .list(
            part="statistics",
            id=video_id,
        )
        .execute()
    )
    items = response.get("items", [])
    if not items:
        return {}
    return items[0].get("statistics", {})
