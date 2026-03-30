"""
analytics_report.py
────────────────────
Collects cross-platform engagement analytics and saves reports as
both CSV and JSON in the /reports directory.

Usage:
    python analytics_report.py [--output-dir reports]

Optionally reads a manifest file produced by daily_update.py to
supply recently published media IDs to each platform's analytics API.
"""

import argparse
import csv
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
logger = logging.getLogger("analytics_report")

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from config.settings import cfg
from scripts.analytics import collect_all


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────


def _load_latest_manifest(reports_dir: Path) -> dict:
    """
    Try to load the most recent daily manifest so we know which
    media IDs to query for per-post analytics.

    Returns an empty dict if no manifest is found.
    """
    manifests = sorted(reports_dir.glob("manifest_*.json"), reverse=True)
    if not manifests:
        logger.info("No manifest found – will collect platform-level metrics only.")
        return {}
    logger.info("Loading manifest: %s", manifests[0])
    with open(manifests[0], "r", encoding="utf-8") as f:
        return json.load(f)


def _extract_media_ids(manifest: dict) -> dict:
    """
    Build the media_ids dict expected by analytics.collect_all().
    """
    published = manifest.get("published", {})
    media_ids: dict = {}

    # Instagram
    ig = published.get("instagram")
    if isinstance(ig, dict) and ig.get("id"):
        media_ids["instagram"] = [ig["id"]]

    # YouTube
    yt = published.get("youtube")
    if isinstance(yt, dict) and yt.get("id"):
        media_ids["youtube"] = [yt["id"]]

    # Pinterest
    pt = published.get("pinterest")
    if isinstance(pt, dict) and pt.get("id"):
        media_ids["pinterest"] = [pt["id"]]

    return media_ids


def _save_csv(records: list[dict], filepath: Path) -> None:
    if not records:
        logger.warning("No analytics records to save.")
        return
    fieldnames = list(records[0].keys())
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    logger.info("CSV report saved to %s (%d rows)", filepath, len(records))


def _save_json(records: list[dict], filepath: Path) -> None:
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    logger.info("JSON report saved to %s (%d records)", filepath, len(records))


def _print_summary(records: list[dict]) -> None:
    """Print a simple per-platform summary to stdout."""
    from collections import defaultdict

    totals: dict = defaultdict(lambda: defaultdict(float))
    for rec in records:
        totals[rec["platform"]][rec["metric"]] += float(rec.get("value") or 0)

    print("\n──── Analytics Summary ────")
    for platform, metrics in sorted(totals.items()):
        print(f"\n  {platform.upper()}")
        for metric, value in sorted(metrics.items()):
            print(f"    {metric}: {value:,.0f}")
    print()


# ─────────────────────────────────────────────────────────────
# Main report function
# ─────────────────────────────────────────────────────────────


def run(output_dir: str | None = None) -> list[dict]:
    """
    Collect analytics and write CSV + JSON reports.

    Args:
        output_dir: Directory for report files.  Defaults to cfg["REPORTS_DIR"].

    Returns:
        List of analytics record dicts.
    """
    reports_dir = Path(output_dir or cfg["REPORTS_DIR"])
    reports_dir.mkdir(parents=True, exist_ok=True)

    manifest = _load_latest_manifest(reports_dir)
    media_ids = _extract_media_ids(manifest)

    logger.info("Collecting analytics from all platforms …")
    records = collect_all(media_ids)

    date_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    _save_csv(records, reports_dir / f"analytics_{date_str}.csv")
    _save_json(records, reports_dir / f"analytics_{date_str}.json")

    _print_summary(records)
    return records


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect cross-platform analytics and save reports")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory where reports will be saved (default: REPORTS_DIR env var or 'reports').",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run(output_dir=args.output_dir)
