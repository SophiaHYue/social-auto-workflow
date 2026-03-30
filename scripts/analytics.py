"""
scripts/analytics.py
─────────────────────
Collects engagement analytics from all configured platforms and
returns a unified list of metric dicts.

Each platform function is fault-tolerant: if credentials are missing
or the API call fails, it logs a warning and returns an empty list so
the other platforms can still be collected.
"""

import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import cfg

logger = logging.getLogger(__name__)


def _today() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


def _yesterday() -> str:
    return (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")


def _week_ago() -> str:
    return (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")


# ─────────────────────────────────────────────────────────────
# Per-platform collectors
# ─────────────────────────────────────────────────────────────


def collect_facebook() -> list[dict]:
    """Collect Facebook Page insights."""
    if not cfg.get("FACEBOOK_ACCESS_TOKEN"):
        logger.warning("Facebook analytics skipped – no access token.")
        return []
    try:
        from scripts.facebook import get_page_insights

        data = get_page_insights(
            "page_impressions,page_engaged_users,page_fan_adds_unique"
        )
        records = []
        for item in data.get("data", []):
            for val in item.get("values", []):
                records.append(
                    {
                        "platform": "facebook",
                        "metric": item["name"],
                        "value": val["value"],
                        "end_time": val.get("end_time", _today()),
                    }
                )
        return records
    except Exception as exc:  # noqa: BLE001
        logger.warning("Facebook analytics error: %s", exc)
        return []


def collect_instagram(recent_media_ids: list[str] | None = None) -> list[dict]:
    """Collect Instagram post insights for a list of media IDs."""
    if not cfg.get("FACEBOOK_ACCESS_TOKEN"):
        logger.warning("Instagram analytics skipped – no access token.")
        return []
    if not recent_media_ids:
        logger.info("No Instagram media IDs provided – skipping insights.")
        return []
    try:
        from scripts.instagram import get_media_insights

        records = []
        for media_id in recent_media_ids:
            data = get_media_insights(media_id)
            for item in data.get("data", []):
                records.append(
                    {
                        "platform": "instagram",
                        "media_id": media_id,
                        "metric": item["name"],
                        "value": item.get("values", [{}])[0].get("value", 0),
                        "end_time": _today(),
                    }
                )
        return records
    except Exception as exc:  # noqa: BLE001
        logger.warning("Instagram analytics error: %s", exc)
        return []


def collect_tiktok() -> list[dict]:
    """Collect TikTok video analytics."""
    if not cfg.get("TIKTOK_ACCESS_TOKEN"):
        logger.warning("TikTok analytics skipped – no access token.")
        return []
    try:
        from scripts.tiktok import get_video_list

        data = get_video_list(max_count=20)
        records = []
        for video in data.get("data", {}).get("videos", []):
            for metric in ("view_count", "like_count", "comment_count", "share_count"):
                records.append(
                    {
                        "platform": "tiktok",
                        "media_id": video.get("id"),
                        "metric": metric,
                        "value": video.get(metric, 0),
                        "end_time": _today(),
                    }
                )
        return records
    except Exception as exc:  # noqa: BLE001
        logger.warning("TikTok analytics error: %s", exc)
        return []


def collect_youtube(video_ids: list[str] | None = None) -> list[dict]:
    """Collect YouTube video statistics."""
    if not cfg.get("YOUTUBE_REFRESH_TOKEN"):
        logger.warning("YouTube analytics skipped – no refresh token.")
        return []
    if not video_ids:
        logger.info("No YouTube video IDs provided – skipping analytics.")
        return []
    try:
        from scripts.youtube import get_video_analytics

        records = []
        for vid in video_ids:
            stats = get_video_analytics(vid)
            for metric, value in stats.items():
                records.append(
                    {
                        "platform": "youtube",
                        "media_id": vid,
                        "metric": metric,
                        "value": value,
                        "end_time": _today(),
                    }
                )
        return records
    except Exception as exc:  # noqa: BLE001
        logger.warning("YouTube analytics error: %s", exc)
        return []


def collect_pinterest(pin_ids: list[str] | None = None) -> list[dict]:
    """Collect Pinterest Pin analytics."""
    if not cfg.get("PINTEREST_ACCESS_TOKEN"):
        logger.warning("Pinterest analytics skipped – no access token.")
        return []
    if not pin_ids:
        logger.info("No Pinterest pin IDs provided – skipping analytics.")
        return []
    try:
        from scripts.pinterest import get_pin_analytics

        records = []
        start = _week_ago()
        end = _today()
        for pin_id in pin_ids:
            data = get_pin_analytics(pin_id, start, end)
            for metric, values in data.get("all", {}).get("daily_metrics", {}).items():
                for day in values:
                    records.append(
                        {
                            "platform": "pinterest",
                            "media_id": pin_id,
                            "metric": metric,
                            "value": day.get("value", 0),
                            "end_time": day.get("date", end),
                        }
                    )
        return records
    except Exception as exc:  # noqa: BLE001
        logger.warning("Pinterest analytics error: %s", exc)
        return []


# ─────────────────────────────────────────────────────────────
# Aggregated collection
# ─────────────────────────────────────────────────────────────


def collect_all(media_ids: dict | None = None) -> list[dict]:
    """
    Collect analytics from all configured platforms.

    Args:
        media_ids: Optional dict mapping platform names to lists of
                   recently published media IDs, e.g.::

                       {
                           "instagram": ["17854360229135492"],
                           "youtube":   ["dQw4w9WgXcQ"],
                           "pinterest": ["123456789"],
                       }

    Returns:
        Flat list of metric record dicts.
    """
    media_ids = media_ids or {}
    records: list[dict] = []
    records += collect_facebook()
    records += collect_instagram(media_ids.get("instagram"))
    records += collect_tiktok()
    records += collect_youtube(media_ids.get("youtube"))
    records += collect_pinterest(media_ids.get("pinterest"))
    logger.info("Collected %d analytics records across all platforms.", len(records))
    return records
