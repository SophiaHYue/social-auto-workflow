"""
scripts/generate_video.py
──────────────────────────
Generates short and long AI videos.

Short videos – Runway ML REST API (image-to-video or text-to-video).
Long  videos – Pictory REST API (script-to-video / article-to-video).

Falls back to a local MoviePy slide-show if neither cloud API is configured.
"""

import os
import sys
import time
import logging
import requests
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import cfg

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Short video helpers
# ─────────────────────────────────────────────────────────────


def generate_short_video_runway(
    prompt: str, image_path: str | None, output_dir: str
) -> str:
    """
    Use Runway ML to create a short video (~4 s) from a text prompt
    or a seed image.

    Args:
        prompt: Text description / motion prompt.
        image_path: Optional local image to use as the first frame.
        output_dir: Directory where the MP4 will be saved.

    Returns:
        Absolute path to the saved video file.
    """
    api_key = cfg["RUNWAY_API_KEY"]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Submit generation task
    payload: dict = {"prompt": prompt, "model": "gen3a_turbo", "duration": 5}
    if image_path:
        import base64

        with open(image_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        payload["image"] = f"data:image/png;base64,{encoded}"

    submit_url = "https://api.runwayml.com/v1/image_to_video"
    resp = requests.post(submit_url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    task_id = resp.json()["id"]

    # Poll until done
    poll_url = f"https://api.runwayml.com/v1/tasks/{task_id}"
    for _ in range(60):  # max ~5 min
        time.sleep(10)
        poll = requests.get(poll_url, headers=headers, timeout=30)
        poll.raise_for_status()
        data = poll.json()
        status = data.get("status")
        if status == "SUCCEEDED":
            video_url = data["output"][0]
            break
        if status in ("FAILED", "CANCELLED"):
            raise RuntimeError(f"Runway task {task_id} failed with status {status}")
    else:
        raise TimeoutError(f"Runway task {task_id} timed out.")

    os.makedirs(output_dir, exist_ok=True)
    filename = datetime.utcnow().strftime("short_%Y%m%d_%H%M%S.mp4")
    filepath = os.path.join(output_dir, filename)
    video_data = requests.get(video_url, timeout=120).content
    with open(filepath, "wb") as f:
        f.write(video_data)

    logger.info("Runway short video saved to %s", filepath)
    return filepath


def generate_short_video_moviepy(
    image_path: str, caption: str, output_dir: str
) -> str:
    """
    Create a simple slide-show MP4 using MoviePy (offline fallback).

    Args:
        image_path: Path to the source image.
        caption: Text overlay for the clip.
        output_dir: Directory where the MP4 will be saved.

    Returns:
        Absolute path to the saved video file.
    """
    from moviepy.editor import ImageClip, TextClip, CompositeVideoClip  # type: ignore

    clip = ImageClip(image_path, duration=5)
    txt = (
        TextClip(caption, fontsize=40, color="white", bg_color="black")
        .set_position("bottom")
        .set_duration(5)
    )
    video = CompositeVideoClip([clip, txt])

    os.makedirs(output_dir, exist_ok=True)
    filename = datetime.utcnow().strftime("short_local_%Y%m%d_%H%M%S.mp4")
    filepath = os.path.join(output_dir, filename)
    video.write_videofile(filepath, fps=24, logger=None)

    logger.info("MoviePy short video saved to %s", filepath)
    return filepath


# ─────────────────────────────────────────────────────────────
# Long video helpers
# ─────────────────────────────────────────────────────────────


def _pictory_get_token() -> str:
    """Obtain a short-lived Pictory access token."""
    resp = requests.post(
        "https://api.pictory.ai/pictoryapis/v1/oauth2/token",
        json={
            "client_id": cfg["PICTORY_CLIENT_ID"],
            "client_secret": cfg["PICTORY_CLIENT_SECRET"],
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def generate_long_video_pictory(script: str, output_dir: str) -> str:
    """
    Use Pictory to render a long-form video from a script.

    Args:
        script: The full article / script text.
        output_dir: Directory where the MP4 will be saved.

    Returns:
        Absolute path to the saved video file.
    """
    token = _pictory_get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # Step 1 – create story
    story_resp = requests.post(
        "https://api.pictory.ai/pictoryapis/v1/video/storyboard",
        headers=headers,
        json={
            "videoName": f"daily_{datetime.utcnow().strftime('%Y%m%d')}",
            "videoDescription": "Daily AI content",
            "language": "en",
            "autoHighlightKeyword": "Yes",
            "noOfWords": 30,
            "brandLogo": {},
            "scenes": [{"text": script, "voiceOver": True, "splitTextByEOS": True}],
        },
        timeout=60,
    )
    story_resp.raise_for_status()
    job_id = story_resp.json()["jobId"]

    # Step 2 – poll for render completion
    for _ in range(120):
        time.sleep(15)
        status_resp = requests.get(
            f"https://api.pictory.ai/pictoryapis/v1/jobs/{job_id}",
            headers=headers,
            timeout=30,
        )
        status_resp.raise_for_status()
        data = status_resp.json()
        if data.get("status") == "completed":
            video_url = data["videoURL"]
            break
        if data.get("status") == "failed":
            raise RuntimeError(f"Pictory job {job_id} failed.")
    else:
        raise TimeoutError(f"Pictory job {job_id} timed out.")

    os.makedirs(output_dir, exist_ok=True)
    filename = datetime.utcnow().strftime("long_%Y%m%d_%H%M%S.mp4")
    filepath = os.path.join(output_dir, filename)
    video_data = requests.get(video_url, timeout=300).content
    with open(filepath, "wb") as f:
        f.write(video_data)

    logger.info("Pictory long video saved to %s", filepath)
    return filepath


# ─────────────────────────────────────────────────────────────
# Public helpers
# ─────────────────────────────────────────────────────────────


def generate_short_video(
    prompt: str, image_path: str | None = None, output_dir: str | None = None
) -> str:
    """
    High-level helper: tries Runway, falls back to MoviePy.

    Args:
        prompt: Text / motion description.
        image_path: Optional seed image.
        output_dir: Where to save the file.

    Returns:
        Absolute path to the saved video file.
    """
    output_dir = output_dir or cfg["OUTPUT_DIR"]
    if cfg.get("RUNWAY_API_KEY"):
        return generate_short_video_runway(prompt, image_path, output_dir)
    else:
        if not image_path:
            raise ValueError(
                "MoviePy fallback requires an image_path when RUNWAY_API_KEY is not set."
            )
        return generate_short_video_moviepy(image_path, prompt, output_dir)


def generate_long_video(script: str, output_dir: str | None = None) -> str:
    """
    High-level helper: uses Pictory.

    Args:
        script: Full article / script text.
        output_dir: Where to save the file.

    Returns:
        Absolute path to the saved video file.
    """
    output_dir = output_dir or cfg["OUTPUT_DIR"]
    if cfg.get("PICTORY_CLIENT_ID"):
        return generate_long_video_pictory(script, output_dir)
    else:
        raise EnvironmentError(
            "No long-video API configured. Set PICTORY_CLIENT_ID and "
            "PICTORY_CLIENT_SECRET in your .env file."
        )
