"""Database helpers for loyalty level configuration."""

from __future__ import annotations

import json
from typing import Iterable, Sequence

from sqlalchemy import func

from bot.constants.levels import DEFAULT_LEVEL_NAMES, DEFAULT_LEVEL_THRESHOLDS
from bot.database import Database
from bot.database.models import BoughtGoods, LevelSettings, User

__all__ = [
    'get_level_settings',
    'set_level_thresholds',
    'set_level_names',
    'set_level_rewards',
    'reset_level_settings',
    'get_user_level_stats',
]

_LEVEL_LANGUAGE_FALLBACK = 'en'


def _ensure_entry() -> LevelSettings:
    session = Database().session
    entry = session.query(LevelSettings).first()
    if entry is None:
        entry = LevelSettings()
        session.add(entry)
        session.commit()
        session.refresh(entry)
    return entry


def _load_thresholds(raw: str | None) -> list[int]:
    if not raw:
        return list(DEFAULT_LEVEL_THRESHOLDS)
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return list(DEFAULT_LEVEL_THRESHOLDS)
    if not isinstance(data, list):
        return list(DEFAULT_LEVEL_THRESHOLDS)
    values: list[int] = []
    for value in data:
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        if number < 0 or number in values:
            continue
        values.append(number)
    if not values:
        values = list(DEFAULT_LEVEL_THRESHOLDS)
    if 0 not in values:
        values.append(0)
    values.sort()
    return values


def _sanitize_thresholds(values: Sequence[int]) -> list[int]:
    cleaned: list[int] = []
    for value in values:
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        if number < 0 or number in cleaned:
            continue
        cleaned.append(number)
    if not cleaned:
        cleaned = list(DEFAULT_LEVEL_THRESHOLDS)
    if 0 not in cleaned:
        cleaned.append(0)
    cleaned.sort()
    return cleaned


def _sanitize_names(data: dict[str, Iterable[str]] | None, length: int) -> dict[str, list[str]]:
    if length <= 0:
        length = len(DEFAULT_LEVEL_THRESHOLDS)
    fallback_defaults = DEFAULT_LEVEL_NAMES.get(_LEVEL_LANGUAGE_FALLBACK, [])
    if not isinstance(data, dict):
        data = {}
    languages = set(DEFAULT_LEVEL_NAMES.keys()) | set(data.keys())
    result: dict[str, list[str]] = {}
    for language in sorted(languages):
        defaults = DEFAULT_LEVEL_NAMES.get(language, fallback_defaults)
        existing = list(data.get(language, []))
        cleaned: list[str] = []
        for index in range(length):
            value = ''
            if index < len(existing):
                raw_value = existing[index]
                if raw_value is None:
                    raw_value = ''
                value = str(raw_value).strip()
            if value:
                cleaned.append(value)
            elif index < len(defaults):
                cleaned.append(defaults[index])
            elif index < len(fallback_defaults):
                cleaned.append(fallback_defaults[index])
            else:
                cleaned.append(f'Level {index + 1}')
        result[language] = cleaned
    return result


def _load_names(raw: str | None, length: int) -> dict[str, list[str]]:
    if not raw:
        return _sanitize_names(DEFAULT_LEVEL_NAMES, length)
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        data = DEFAULT_LEVEL_NAMES
    if not isinstance(data, dict):
        data = DEFAULT_LEVEL_NAMES
    names_map: dict[str, list[str]] = {}
    for language, values in data.items():
        if isinstance(values, list):
            names_map[language] = [str(value).strip() if value is not None else '' for value in values]
    return _sanitize_names(names_map, length)


def _load_rewards(raw: str | None, length: int) -> list[int]:
    if not raw:
        return [0 for _ in range(length)]
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        data = []
    if not isinstance(data, list):
        data = []
    rewards: list[int] = []
    for index in range(length):
        value = 0
        if index < len(data):
            try:
                number = int(data[index])
            except (TypeError, ValueError):
                number = 0
            if number < 0:
                number = 0
            if number > 100:
                number = 100
            value = number
        rewards.append(value)
    return rewards


def get_level_settings() -> tuple[list[int], dict[str, list[str]], list[int]]:
    """Return current level thresholds, localized names, and rewards."""
    entry = _ensure_entry()
    session = Database().session
    try:
        raw_thresholds = json.loads(entry.thresholds or '[]')
    except (TypeError, json.JSONDecodeError):
        raw_thresholds = []
    if not isinstance(raw_thresholds, list):
        raw_thresholds = []
    thresholds = _sanitize_thresholds(raw_thresholds)
    try:
        raw_names = json.loads(entry.names or '{}')
    except (TypeError, json.JSONDecodeError):
        raw_names = DEFAULT_LEVEL_NAMES
    if not isinstance(raw_names, dict):
        raw_names = {}
    names = _sanitize_names(raw_names, len(thresholds))
    rewards = _load_rewards(entry.rewards, len(thresholds))
    changed = raw_thresholds != thresholds or raw_names != names
    if changed or _load_rewards(entry.rewards, len(raw_thresholds)) != rewards:
        entry.thresholds = json.dumps(thresholds)
        entry.names = json.dumps(names, ensure_ascii=False)
        entry.rewards = json.dumps(rewards)
        session.commit()
    if changed:
        session.expire(entry)
    return thresholds, names, rewards


def set_level_thresholds(thresholds: Sequence[int]) -> list[int]:
    """Update level thresholds and keep names aligned."""
    cleaned = _sanitize_thresholds(thresholds)
    entry = _ensure_entry()
    session = Database().session
    names = _load_names(entry.names, len(cleaned))
    rewards = _load_rewards(entry.rewards, len(cleaned))
    entry.thresholds = json.dumps(cleaned)
    entry.names = json.dumps(names, ensure_ascii=False)
    entry.rewards = json.dumps(rewards)
    session.commit()
    return cleaned


def set_level_names(language: str, names: Sequence[str]) -> list[str]:
    """Update level names for a specific language."""
    entry = _ensure_entry()
    session = Database().session
    thresholds = _load_thresholds(entry.thresholds)
    target = []
    for value in names:
        text = (value or '').strip()
        if text:
            target.append(text)
    sanitized = _sanitize_names({language: target}, len(thresholds))[language]
    current = _load_names(entry.names, len(thresholds))
    current[language] = sanitized
    entry.names = json.dumps(current, ensure_ascii=False)
    session.commit()
    return sanitized


def set_level_rewards(rewards: Sequence[int]) -> list[int]:
    """Update the reward percentages per level."""
    entry = _ensure_entry()
    session = Database().session
    thresholds = _load_thresholds(entry.thresholds)
    cleaned: list[int] = []
    for index in range(len(thresholds)):
        value = 0
        if index < len(rewards):
            try:
                number = int(rewards[index])
            except (TypeError, ValueError):
                number = 0
            if number < 0:
                number = 0
            if number > 100:
                number = 100
            value = number
        cleaned.append(value)
    entry.rewards = json.dumps(cleaned)
    session.commit()
    return cleaned


def reset_level_settings() -> tuple[list[int], dict[str, list[str]], list[int]]:
    """Restore level settings to the defaults."""
    entry = _ensure_entry()
    session = Database().session
    thresholds = list(DEFAULT_LEVEL_THRESHOLDS)
    names = _sanitize_names(DEFAULT_LEVEL_NAMES, len(thresholds))
    rewards = [0 for _ in thresholds]
    entry.thresholds = json.dumps(thresholds)
    entry.names = json.dumps(names, ensure_ascii=False)
    entry.rewards = json.dumps(rewards)
    session.commit()
    return thresholds, names, rewards


def get_user_level_stats(offset: int = 0, limit: int = 10) -> list[dict]:
    """Return aggregated user purchases for level overview."""
    session = Database().session
    query = (
        session.query(
            User.telegram_id,
            User.username,
            User.language,
            func.count(BoughtGoods.id).label('purchases'),
        )
        .outerjoin(BoughtGoods, BoughtGoods.buyer_id == User.telegram_id)
        .group_by(User.telegram_id)
        .order_by(func.count(BoughtGoods.id).desc(), User.telegram_id.asc())
    )
    if offset:
        query = query.offset(int(offset))
    if limit:
        query = query.limit(int(limit))
    rows = query.all()
    results: list[dict] = []
    for user_id, username, language, purchases in rows:
        results.append(
            {
                'user_id': int(user_id),
                'username': username,
                'language': (language or _LEVEL_LANGUAGE_FALLBACK),
                'purchases': int(purchases or 0),
            }
        )
    return results
