"""Shared navigation handlers (e.g. back button support)."""

from aiogram import Dispatcher
from aiogram.types import CallbackQuery

from bot.misc import TgConfig
from bot.utils import restore_previous_message


async def navigation_back_handler(call: CallbackQuery) -> None:
    fallback = call.data[len('navback:'):] if call.data else ''
    if fallback:
        TgConfig.STATE[call.from_user.id] = None
        TgConfig.STATE.pop(f'{call.from_user.id}_emoji_source', None)
        await call.answer()
        dispatcher = Dispatcher.get_current()
        call.data = fallback
        await dispatcher.callback_query_handlers.notify(call)
        return
    if call.message:
        restored = await restore_previous_message(
            call.bot,
            call.message.chat.id,
            call.message.message_id,
        )
        if restored:
            TgConfig.STATE[call.from_user.id] = None
            TgConfig.STATE.pop(f'{call.from_user.id}_emoji_source', None)
            await call.answer()
            return
    await call.answer()


def register_navigation(dp: Dispatcher) -> None:
    dp.register_callback_query_handler(
        navigation_back_handler,
        lambda c: c.data is not None and c.data.startswith('navback:'),
        state='*',
    )
