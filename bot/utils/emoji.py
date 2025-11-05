"""Helpers for configurable UI emojis."""

from __future__ import annotations

from functools import lru_cache
from typing import Dict

from bot.database.methods import get_ui_emoji_overrides


@lru_cache(maxsize=1)
def _load_overrides() -> Dict[str, str]:
    return get_ui_emoji_overrides()


def invalidate_ui_emoji_cache() -> None:
    """Reset cached overrides so subsequent calls fetch fresh data."""

    _load_overrides.cache_clear()


def get_ui_emoji_overrides_cached() -> Dict[str, str]:
    return _load_overrides().copy()


def apply_ui_emojis(text: str) -> str:
    """Replace default emojis in text with configured overrides."""

    overrides = _load_overrides()
    result = text
    for original, replacement in overrides.items():
        result = result.replace(original, replacement)
    return result
