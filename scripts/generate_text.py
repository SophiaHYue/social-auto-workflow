"""
scripts/generate_text.py
──────────────────────────
Generates captions, titles, and hashtags using the OpenAI Chat API.
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import cfg

logger = logging.getLogger(__name__)

# Default content prompt template
_DEFAULT_TOPIC = "today's AI technology trends and innovations"

_CAPTION_SYSTEM = (
    "You are a social media content expert. "
    "Write engaging, platform-appropriate captions."
)

_TITLE_SYSTEM = (
    "You are a YouTube content strategist. "
    "Write compelling, SEO-optimized video titles."
)

_HASHTAG_SYSTEM = (
    "You are a social media growth expert. "
    "Generate relevant, trending hashtags separated by spaces."
)


def _chat(system: str, user: str, max_tokens: int = 300) -> str:
    """Send a single chat completion request and return the assistant reply."""
    import openai

    openai.api_key = cfg["OPENAI_API_KEY"]
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=max_tokens,
        temperature=0.8,
    )
    return response.choices[0].message.content.strip()


def generate_caption(topic: str = _DEFAULT_TOPIC, platform: str = "general") -> str:
    """
    Generate a social media caption for the given topic.

    Args:
        topic: Subject or theme for today's content.
        platform: Target platform (general, instagram, tiktok, facebook, …).

    Returns:
        Caption string including relevant emojis and a call-to-action.
    """
    user_msg = (
        f"Write a compelling {platform} caption about: {topic}. "
        "Include emojis and a call-to-action. Keep it under 200 words."
    )
    caption = _chat(_CAPTION_SYSTEM, user_msg)
    logger.info("Caption generated (%d chars)", len(caption))
    return caption


def generate_title(topic: str = _DEFAULT_TOPIC) -> str:
    """
    Generate a YouTube / blog title for the given topic.

    Args:
        topic: Subject or theme for today's content.

    Returns:
        Title string (≤ 80 characters).
    """
    user_msg = (
        f"Write a YouTube video title about: {topic}. "
        "Make it click-worthy, under 80 characters."
    )
    title = _chat(_TITLE_SYSTEM, user_msg, max_tokens=80)
    logger.info("Title generated: %s", title)
    return title


def generate_hashtags(
    topic: str = _DEFAULT_TOPIC, count: int = 20, platform: str = "general"
) -> list[str]:
    """
    Generate a list of hashtags for the given topic.

    Args:
        topic: Subject or theme for today's content.
        count: Desired number of hashtags.
        platform: Target platform.

    Returns:
        List of hashtag strings (each starting with #).
    """
    user_msg = (
        f"Generate exactly {count} relevant {platform} hashtags for: {topic}. "
        "Return only the hashtags separated by spaces, no other text."
    )
    raw = _chat(_HASHTAG_SYSTEM, user_msg, max_tokens=200)
    # Ensure every tag starts with #
    tags = [
        tag if tag.startswith("#") else f"#{tag}"
        for tag in raw.split()
        if tag.strip()
    ]
    logger.info("Hashtags generated: %s", " ".join(tags))
    return tags


def generate_all_text(topic: str = _DEFAULT_TOPIC) -> dict:
    """
    Convenience wrapper – generate caption, title, and hashtags in one call.

    Args:
        topic: Subject or theme for today's content.

    Returns:
        Dict with keys 'caption', 'title', 'hashtags'.
    """
    return {
        "caption": generate_caption(topic),
        "title": generate_title(topic),
        "hashtags": generate_hashtags(topic),
    }
