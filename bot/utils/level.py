from bot.constants.levels import DEFAULT_LEVEL_NAMES, DEFAULT_LEVEL_THRESHOLDS
from bot.database.methods import get_level_settings


def get_level_info(purchases: int, lang: str = 'lt'):
    """Return level name and progress battery for purchase count.

    Discount levels have been disabled, so this function always returns 0 as the
    discount value to maintain compatibility with callers expecting three
    return values.
    """
    if purchases < 0:
        purchases = 0
    try:
        thresholds, names_map, rewards = get_level_settings()
    except Exception:  # pragma: no cover - fallback in case database is unavailable
        thresholds, names_map = DEFAULT_LEVEL_THRESHOLDS, DEFAULT_LEVEL_NAMES
        rewards = [0 for _ in thresholds]
    if not thresholds:
        thresholds = list(DEFAULT_LEVEL_THRESHOLDS)
    if not names_map:
        names_map = DEFAULT_LEVEL_NAMES
    if not rewards or len(rewards) < len(thresholds):
        rewards = [0 for _ in thresholds]
    level_index = 0
    for idx, threshold in enumerate(thresholds):
        if purchases >= threshold:
            level_index = idx
        else:
            break
    names = names_map.get(lang) or names_map.get('en') or next(iter(names_map.values()))
    if level_index >= len(names):
        level_index = len(names) - 1
    level_name = names[level_index]
    discount = rewards[level_index] if level_index < len(rewards) else 0

    if level_index < len(thresholds) - 1:
        next_threshold = thresholds[level_index + 1]
        current_threshold = thresholds[level_index]
        progress = purchases - current_threshold
        needed = next_threshold - current_threshold
        battery = '🪫' if progress * 2 < needed else '🔋'
    else:
        battery = '🔋'
    return level_name, discount, battery
