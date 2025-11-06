"""Database helpers for profile configuration."""

from __future__ import annotations

import json
from typing import Any

from bot.constants.profile import (
    PROFILE_BOOLEAN_FIELDS,
    PROFILE_NUMERIC_FIELDS,
    PROFILE_TEXT_FIELDS,
)
from bot.database.main import Database
from bot.database.models.main import ProfileSettings


def _get_or_create_profile_settings(session) -> ProfileSettings:
    settings = session.query(ProfileSettings).first()
    if settings is None:
        settings = ProfileSettings()
        session.add(settings)
        session.commit()
    return settings


def get_profile_settings() -> dict[str, Any]:
    """Return merged profile settings."""
    session = Database().session
    settings = _get_or_create_profile_settings(session)
    return settings.as_dict()


def update_profile_settings(updates: dict[str, Any]) -> dict[str, Any]:
    """Persist provided settings and return the merged configuration."""
    session = Database().session
    settings = _get_or_create_profile_settings(session)
    current = settings.as_dict()
    for key, value in updates.items():
        if key in PROFILE_BOOLEAN_FIELDS:
            current[key] = bool(value)
        elif key in PROFILE_NUMERIC_FIELDS:
            current[key] = int(value)
        elif key in PROFILE_TEXT_FIELDS:
            current[key] = str(value)
    settings.options = json.dumps(current, ensure_ascii=False)
    session.add(settings)
    session.commit()
    return current


def toggle_profile_feature(feature: str, enabled: bool) -> dict[str, Any]:
    """Convenience wrapper to enable or disable a boolean feature."""
    if feature not in PROFILE_BOOLEAN_FIELDS:
        raise ValueError(f'Unsupported profile feature: {feature}')
    return update_profile_settings({feature: enabled})


def set_blackjack_max_bet(value: int) -> dict[str, Any]:
    if value <= 0:
        raise ValueError('blackjack_max_bet must be positive')
    return update_profile_settings({'blackjack_max_bet': value})


def set_profile_text(key: str, value: str) -> dict[str, Any]:
    if key not in PROFILE_TEXT_FIELDS:
        raise ValueError(f'Unsupported profile text field: {key}')
    return update_profile_settings({key: value})
