from __future__ import annotations

"""Default configuration for the weekly quest feature."""

DEFAULT_QUEST_TITLES = {
    'en': {
        'title': 'Weekly Highlight',
        'description': 'Complete curated tasks before the reset to earn a reward.',
    },
    'lt': {
        'title': 'Savaitės užduotis',
        'description': 'Atlikite paruoštas užduotis prieš atnaujinimą ir gaukite prizą.',
    },
    'ru': {
        'title': 'Еженедельный квест',
        'description': 'Выполните подобранные задания до обновления и получите награду.',
    },
}

DEFAULT_QUEST_RESET = {
    'weekday': 0,  # Monday
    'hour': 12,
}

DEFAULT_QUEST_TASKS: list[dict] = []

DEFAULT_QUEST_REWARD = {
    'type': 'discount',
    'value': 5,
    'title': {
        'en': '5% store-wide discount',
        'lt': '5% nuolaida visame kataloge',
        'ru': 'Скидка 5% на весь каталог',
    },
}

__all__ = [
    'DEFAULT_QUEST_TITLES',
    'DEFAULT_QUEST_RESET',
    'DEFAULT_QUEST_TASKS',
    'DEFAULT_QUEST_REWARD',
]
