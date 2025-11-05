"""Utilities for editing Telegram messages with history tracking."""

from __future__ import annotations

import contextlib
from copy import deepcopy
from typing import Any, Dict, List, Tuple

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.exceptions import MessageNotModified

from bot.misc import TgConfig

HistoryEntry = Tuple[str, Dict[str, Any]]

_HISTORY_PREFIX = 'message_history'
_MAX_HISTORY_LENGTH = 25


def _history_key(chat_id: int, message_id: int) -> str:
    return f'{_HISTORY_PREFIX}:{chat_id}:{message_id}'


def _serialise_reply_markup(markup: InlineKeyboardMarkup | None) -> Dict[str, Any] | None:
    if markup is None:
        return None
    if hasattr(markup, 'to_python'):
        return markup.to_python()
    return deepcopy(markup)


def _deserialise_reply_markup(data: Dict[str, Any] | None) -> InlineKeyboardMarkup | None:
    if data is None:
        return None
    if isinstance(data, dict):
        return InlineKeyboardMarkup(**data)
    return data  # pragma: no cover - fallback for unexpected types


def _normalise_kwargs(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    data = deepcopy(kwargs)
    for key in ('chat_id', 'message_id', 'inline_message_id'):
        data.pop(key, None)
    if 'reply_markup' in data:
        data['reply_markup'] = _serialise_reply_markup(data['reply_markup'])
    return data


def _remember_history(chat_id: int, message_id: int, text: str, kwargs: Dict[str, Any]) -> None:
    if chat_id is None or message_id is None:
        return
    history_key = _history_key(chat_id, message_id)
    entry: HistoryEntry = (text, _normalise_kwargs(kwargs))
    history: List[HistoryEntry] = TgConfig.STATE.setdefault(history_key, [])
    if history and history[-1] == entry:
        return
    history.append(entry)
    if len(history) > _MAX_HISTORY_LENGTH:
        del history[0]


def _pop_previous(chat_id: int, message_id: int) -> HistoryEntry | None:
    history_key = _history_key(chat_id, message_id)
    history: List[HistoryEntry] | None = TgConfig.STATE.get(history_key)
    if not history or len(history) < 2:
        return None
    history.pop()
    previous = history[-1]
    if not history:
        TgConfig.STATE.pop(history_key, None)
    return previous


async def safe_edit_message_text(
    bot,
    *args: Any,
    store_history: bool = True,
    **kwargs: Any,
) -> None:
    """Edit a message suppressing "MessageNotModified" errors and tracking history."""

    chat_id = kwargs.get('chat_id')
    message_id = kwargs.get('message_id')
    text: str | None = None
    if args:
        text = args[0]
    else:
        text = kwargs.get('text')

    if store_history and text is not None:
        _remember_history(chat_id, message_id, text, kwargs)

    with contextlib.suppress(MessageNotModified):
        await bot.edit_message_text(*args, **kwargs)


async def restore_previous_message(bot, chat_id: int, message_id: int) -> bool:
    """Restore the previous message state if available."""

    previous = _pop_previous(chat_id, message_id)
    if not previous:
        return False
    text, kwargs = previous
    kwargs = kwargs.copy()
    if 'reply_markup' in kwargs:
        kwargs['reply_markup'] = _deserialise_reply_markup(kwargs['reply_markup'])
    await safe_edit_message_text(
        bot,
        text,
        chat_id=chat_id,
        message_id=message_id,
        store_history=False,
        **kwargs,
    )
    return True


def clear_message_history(chat_id: int, message_id: int) -> None:
    """Remove cached history for a message."""

    TgConfig.STATE.pop(_history_key(chat_id, message_id), None)
