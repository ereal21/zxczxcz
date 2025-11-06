"""Shared navigation handlers (e.g. back button support)."""

from __future__ import annotations

from aiogram import Dispatcher
from aiogram.types import CallbackQuery
from aiogram.dispatcher.middlewares import BaseMiddleware

from bot.misc import TgConfig
from bot.utils import restore_previous_message


class NavigationMiddleware(BaseMiddleware):
    async def on_pre_process_callback_query(self, call: CallbackQuery, data: dict) -> None:
        if not call.data or call.data.startswith('navback:'):
            return
        user_id = call.from_user.id
        key = f'{user_id}_nav_stack'
        stack: list[str] = TgConfig.STATE.setdefault(key, [])
        if stack and stack[-1] == call.data:
            return
        stack.append(call.data)
        if len(stack) > 50:
            del stack[:-50]


async def navigation_back_handler(call: CallbackQuery) -> None:
    user_id = call.from_user.id
    stack_key = f'{user_id}_nav_stack'
    fallback = call.data[len('navback:'):] if call.data else ''
    stack: list[str] = TgConfig.STATE.get(stack_key, [])
    if stack and stack[-1] == call.data:
        stack.pop()
    if fallback:
        if stack:
            stack.pop()
        if fallback and not fallback.startswith('navback:'):
            stack.append(fallback)
        TgConfig.STATE[stack_key] = stack
        TgConfig.STATE[user_id] = None
        TgConfig.STATE.pop(f'{user_id}_emoji_source', None)
        await call.answer()
        dispatcher = Dispatcher.get_current()
        call.data = fallback
        await dispatcher.callback_query_handlers.notify(call)
        return
    target = None
    if stack:
        if stack:
            stack.pop()
        while stack:
            candidate = stack.pop()
            if candidate and not candidate.startswith('navback:'):
                target = candidate
                stack.append(candidate)
                break
        TgConfig.STATE[stack_key] = stack
    if target:
        TgConfig.STATE[user_id] = None
        TgConfig.STATE.pop(f'{user_id}_emoji_source', None)
        await call.answer()
        dispatcher = Dispatcher.get_current()
        call.data = target
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
    dp.middleware.setup(NavigationMiddleware())
    dp.register_callback_query_handler(
        navigation_back_handler,
        lambda c: c.data is not None and c.data.startswith('navback:'),
        state='*',
    )
