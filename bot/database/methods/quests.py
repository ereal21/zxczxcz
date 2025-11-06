"""Database helpers for weekly quest configuration."""

from __future__ import annotations

import json
import uuid

from bot.constants.quests import (
    DEFAULT_QUEST_TITLES,
    DEFAULT_QUEST_REWARD,
)
from bot.database import Database
from bot.database.models import QuestSettings
from bot.database.methods.terms import normalise_term_code

__all__ = [
    'get_weekly_quest',
    'set_weekly_quest_titles',
    'set_weekly_quest_reset',
    'add_weekly_quest_task',
    'update_weekly_quest_task',
    'delete_weekly_quest_task',
    'set_weekly_quest_reward',
]


def _ensure_entry() -> QuestSettings:
    session = Database().session
    entry = session.query(QuestSettings).first()
    if entry is None:
        entry = QuestSettings()
        session.add(entry)
        session.commit()
        session.refresh(entry)
    return entry


def _serialise_titles(titles: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    merged: dict[str, dict[str, str]] = {}
    base_languages = DEFAULT_QUEST_TITLES.keys()
    for language in set(base_languages) | set(titles.keys()):
        defaults = DEFAULT_QUEST_TITLES.get(language, DEFAULT_QUEST_TITLES['en'])
        existing = titles.get(language, {})
        if not isinstance(existing, dict):
            existing = {}
        merged[language] = {
            'title': str(existing.get('title') or defaults['title']).strip(),
            'description': str(existing.get('description') or defaults['description']).strip(),
        }
    return merged


def _serialise_reward(data: dict) -> dict:
    reward_type = data.get('type') or DEFAULT_QUEST_REWARD['type']
    if reward_type not in {'discount', 'stock'}:
        reward_type = 'discount'
    result: dict = {'type': reward_type}
    if reward_type == 'discount':
        try:
            value = int(data.get('value', DEFAULT_QUEST_REWARD['value']))
        except (TypeError, ValueError):
            value = DEFAULT_QUEST_REWARD['value']
        value = max(0, min(100, value))
        result['value'] = value
    else:
        result['value'] = str(data.get('value') or '').strip()
    titles = data.get('title')
    if not isinstance(titles, dict):
        titles = {}
    reward_titles: dict[str, str] = {}
    for language in set(DEFAULT_QUEST_REWARD['title'].keys()) | set(titles.keys()):
        fallback = DEFAULT_QUEST_REWARD['title'].get(language, DEFAULT_QUEST_REWARD['title']['en'])
        reward_titles[language] = str(titles.get(language) or fallback).strip()
    result['title'] = reward_titles
    return result


def _serialise_task(term: str, count: int, titles: dict[str, str], task_id: str | None = None) -> dict:
    normalised_term = normalise_term_code(term)
    if not normalised_term:
        raise ValueError('Invalid term')
    if count <= 0:
        raise ValueError('Count must be greater than zero')
    task_titles: dict[str, str] = {}
    for language in titles.keys() | DEFAULT_QUEST_TITLES.keys():
        fallback = DEFAULT_QUEST_TITLES.get(language, DEFAULT_QUEST_TITLES['en'])['title']
        task_titles[language] = str(titles.get(language) or fallback).strip()
    return {
        'id': task_id or uuid.uuid4().hex,
        'term': normalised_term,
        'count': int(count),
        'titles': task_titles,
    }


def get_weekly_quest() -> dict:
    entry = _ensure_entry()
    return {
        'titles': entry.titles_dict(),
        'tasks': entry.tasks_list(),
        'reward': entry.reward_dict(),
        'reset_weekday': entry.reset_weekday,
        'reset_hour': entry.reset_hour,
    }


def set_weekly_quest_titles(language: str, title: str, description: str) -> dict:
    entry = _ensure_entry()
    titles = entry.titles_dict()
    titles[str(language)] = {
        'title': str(title or '').strip() or DEFAULT_QUEST_TITLES.get(language, DEFAULT_QUEST_TITLES['en'])['title'],
        'description': str(description or '').strip() or DEFAULT_QUEST_TITLES.get(language, DEFAULT_QUEST_TITLES['en'])['description'],
    }
    entry.titles = json.dumps(_serialise_titles(titles), ensure_ascii=False)
    Database().session.commit()
    return get_weekly_quest()


def set_weekly_quest_reset(weekday: int, hour: int) -> dict:
    entry = _ensure_entry()
    weekday = max(0, min(6, int(weekday)))
    hour = max(0, min(23, int(hour)))
    entry.reset_weekday = weekday
    entry.reset_hour = hour
    Database().session.commit()
    return get_weekly_quest()


def add_weekly_quest_task(term: str, count: int, titles: dict[str, str]) -> dict:
    entry = _ensure_entry()
    tasks = entry.tasks_list()
    task = _serialise_task(term, int(count), titles)
    tasks.append(task)
    entry.tasks = json.dumps(tasks, ensure_ascii=False)
    Database().session.commit()
    return task


def update_weekly_quest_task(task_id: str, term: str | None = None, count: int | None = None,
                             titles: dict[str, str] | None = None) -> dict:
    entry = _ensure_entry()
    tasks = entry.tasks_list()
    updated = None
    for task in tasks:
        if task.get('id') == task_id:
            if term is not None:
                task['term'] = normalise_term_code(term)
            if count is not None:
                new_count = int(count)
                if new_count <= 0:
                    raise ValueError('Count must be greater than zero')
                task['count'] = new_count
            if titles:
                for language, value in titles.items():
                    task_titles = task.setdefault('titles', {})
                    task_titles[language] = str(value or '').strip()
            updated = task
            break
    if updated is None:
        raise ValueError('Task not found')
    entry.tasks = json.dumps(tasks, ensure_ascii=False)
    Database().session.commit()
    return updated


def delete_weekly_quest_task(task_id: str) -> bool:
    entry = _ensure_entry()
    tasks = entry.tasks_list()
    filtered = [task for task in tasks if task.get('id') != task_id]
    if len(filtered) == len(tasks):
        return False
    entry.tasks = json.dumps(filtered, ensure_ascii=False)
    Database().session.commit()
    return True


def set_weekly_quest_reward(reward: dict) -> dict:
    entry = _ensure_entry()
    entry.reward = json.dumps(_serialise_reward(reward), ensure_ascii=False)
    Database().session.commit()
    return get_weekly_quest()['reward']
