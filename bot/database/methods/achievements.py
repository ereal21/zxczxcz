"""Persistence helpers for editable achievements."""

from __future__ import annotations

import json

from bot.constants.achievements import DEFAULT_ACHIEVEMENTS, ACHIEVEMENT_TYPES
from bot.database import Database
from bot.database.models import Achievement
from bot.database.methods.terms import normalise_term_code

__all__ = [
    'list_achievements',
    'get_achievement',
    'set_achievement_titles',
    'configure_term_achievement',
    'create_custom_achievement',
    'delete_custom_achievement',
]


def _ensure_entry(code: str) -> Achievement:
    session = Database().session
    entry = session.query(Achievement).filter(Achievement.code == code).first()
    if entry is None:
        defaults = DEFAULT_ACHIEVEMENTS.get(code, {'type': 'term_purchase'})
        entry = Achievement(code=code, config=defaults)
        session.add(entry)
        session.commit()
        session.refresh(entry)
    return entry


def _merge_defaults(code: str, config: dict) -> dict:
    defaults = DEFAULT_ACHIEVEMENTS.get(code, {})
    merged = defaults.copy()
    merged.update(config)
    ach_type = merged.get('type') or defaults.get('type') or 'term_purchase'
    if ach_type not in ACHIEVEMENT_TYPES:
        ach_type = 'term_purchase'
    merged['type'] = ach_type
    return merged


def list_achievements() -> list[dict]:
    session = Database().session
    entries = session.query(Achievement).order_by(Achievement.code.asc()).all()
    result: list[dict] = []
    for entry in entries:
        config = _merge_defaults(entry.code, entry.config_dict())
        result.append({'code': entry.code, 'config': config})
    return result


def get_achievement(code: str) -> dict | None:
    session = Database().session
    entry = session.query(Achievement).filter(Achievement.code == code).first()
    if entry is None:
        return None
    return {'code': code, 'config': _merge_defaults(code, entry.config_dict())}


def _update_entry(entry: Achievement, config: dict) -> dict:
    entry.config = json.dumps(config, ensure_ascii=False)
    Database().session.commit()
    return {'code': entry.code, 'config': config}


def set_achievement_titles(code: str, titles: dict[str, str]) -> dict:
    entry = _ensure_entry(code)
    config = _merge_defaults(code, entry.config_dict())
    cleaned: dict[str, str] = {}
    for language, value in titles.items():
        cleaned[language] = str(value or '').strip()
    config['titles'] = cleaned
    return _update_entry(entry, config)


def configure_term_achievement(code: str, term_code: str, target: int) -> dict:
    entry = _ensure_entry(code)
    config = _merge_defaults(code, entry.config_dict())
    if config.get('type') != 'term_purchase':
        raise ValueError('Only term purchase achievements are configurable')
    normalised_term = normalise_term_code(term_code)
    if not normalised_term:
        raise ValueError('Invalid term code')
    target = int(target)
    if target <= 0:
        raise ValueError('Target must be greater than zero')
    config['term'] = normalised_term
    config['target'] = target
    return _update_entry(entry, config)


def create_custom_achievement(code: str, titles: dict[str, str], term_code: str, target: int) -> dict:
    normalised_code = str(code or '').strip().lower()
    if not normalised_code:
        raise ValueError('Achievement code is required')
    if normalised_code in DEFAULT_ACHIEVEMENTS:
        raise ValueError('Cannot overwrite built-in achievement')
    session = Database().session
    existing = session.query(Achievement).filter(Achievement.code == normalised_code).first()
    if existing is not None:
        raise ValueError('Achievement already exists')
    entry = Achievement(code=normalised_code, config={'type': 'term_purchase'})
    session.add(entry)
    session.commit()
    session.refresh(entry)
    configure_term_achievement(normalised_code, term_code, target)
    return set_achievement_titles(normalised_code, titles)


def delete_custom_achievement(code: str) -> bool:
    if code in DEFAULT_ACHIEVEMENTS:
        raise ValueError('Cannot delete built-in achievement')
    session = Database().session
    entry = session.query(Achievement).filter(Achievement.code == code).first()
    if entry is None:
        return False
    session.delete(entry)
    session.commit()
    return True
