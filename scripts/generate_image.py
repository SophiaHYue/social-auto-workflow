"""
scripts/generate_image.py
──────────────────────────
Generates a daily AI image using either DALL·E (OpenAI) or
Stable Diffusion (Stability AI).  Returns the local file path
of the saved image.
"""

import os
import sys
import logging
import requests
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import cfg

logger = logging.getLogger(__name__)


def generate_with_dalle(prompt: str, output_dir: str) -> str:
    """
    Call the OpenAI Images API (DALL·E 3) and save the result locally.

    Args:
        prompt: Text description for the image.
        output_dir: Directory where the PNG will be saved.

    Returns:
        Absolute path to the saved image file.
    """
    import openai

    openai.api_key = cfg["OPENAI_API_KEY"]
    response = openai.images.generate(
        model="dall-e-3",
        prompt=prompt,
        n=1,
        size="1024x1024",
    )
    image_url = response.data[0].url

    os.makedirs(output_dir, exist_ok=True)
    filename = datetime.utcnow().strftime("dalle_%Y%m%d_%H%M%S.png")
    filepath = os.path.join(output_dir, filename)

    img_data = requests.get(image_url, timeout=60).content
    with open(filepath, "wb") as f:
        f.write(img_data)

    logger.info("DALL·E image saved to %s", filepath)
    return filepath


def generate_with_stable_diffusion(prompt: str, output_dir: str) -> str:
    """
    Call the Stability AI REST API and save the result locally.

    Args:
        prompt: Text description for the image.
        output_dir: Directory where the PNG will be saved.

    Returns:
        Absolute path to the saved image file.
    """
    api_key = cfg["STABILITY_API_KEY"]
    url = "https://api.stability.ai/v1/generation/stable-diffusion-v1-6/text-to-image"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    payload = {
        "text_prompts": [{"text": prompt}],
        "cfg_scale": 7,
        "height": 1024,
        "width": 1024,
        "samples": 1,
        "steps": 30,
    }

    response = requests.post(url, headers=headers, json=payload, timeout=120)
    response.raise_for_status()

    import base64

    artifacts = response.json().get("artifacts", [])
    if not artifacts:
        raise RuntimeError("Stability AI returned no artifacts.")

    os.makedirs(output_dir, exist_ok=True)
    filename = datetime.utcnow().strftime("sd_%Y%m%d_%H%M%S.png")
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "wb") as f:
        f.write(base64.b64decode(artifacts[0]["base64"]))

    logger.info("Stable Diffusion image saved to %s", filepath)
    return filepath


def generate_image(prompt: str, output_dir: str | None = None) -> str:
    """
    High-level wrapper: tries DALL·E first, falls back to Stable Diffusion.

    Args:
        prompt: Text description for the image.
        output_dir: Where to save the file.  Defaults to cfg["OUTPUT_DIR"].

    Returns:
        Absolute path to the saved image file.
    """
    output_dir = output_dir or cfg["OUTPUT_DIR"]

    if cfg.get("OPENAI_API_KEY"):
        return generate_with_dalle(prompt, output_dir)
    elif cfg.get("STABILITY_API_KEY"):
        return generate_with_stable_diffusion(prompt, output_dir)
    else:
        raise EnvironmentError(
            "No image generation API key configured. "
            "Set OPENAI_API_KEY or STABILITY_API_KEY in your .env file."
        )
