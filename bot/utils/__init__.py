from .names import generate_internal_name, display_name
from .messages import safe_edit_message_text, restore_previous_message, clear_message_history
from .emoji import apply_ui_emojis, invalidate_ui_emoji_cache, get_ui_emoji_overrides_cached

__all__ = [
    'generate_internal_name',
    'display_name',
    'safe_edit_message_text',
    'restore_previous_message',
    'clear_message_history',
    'apply_ui_emojis',
    'invalidate_ui_emoji_cache',
    'get_ui_emoji_overrides_cached',
    'notify_restock',
]


async def notify_restock(*args, **kwargs):
    """Lazy wrapper around ``stock_notify.notify_restock`` to avoid circular imports."""

    from .stock_notify import notify_restock as _notify_restock

    return await _notify_restock(*args, **kwargs)
