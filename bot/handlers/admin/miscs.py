from aiogram import Dispatcher
from aiogram.types import CallbackQuery, Message
import contextlib
import random

from bot.database.methods import (
    check_role,
    get_users_with_tickets,
    reset_lottery_tickets,
    get_all_users,
    get_user_language,
    get_profile_settings,
    toggle_profile_feature,
    set_blackjack_max_bet,
    set_profile_text,
)
from bot.database.models import Permission
from bot.handlers.other import get_bot_user_ids
from bot.keyboards import (
    tools_menu,
    tools_games_menu,
    tools_profile_menu,
    tools_team_menu,
    tools_sales_menu,
    tools_broadcast_menu,
    lottery_menu,
    lottery_run_menu,
    lottery_broadcast_menu,
    back,
)
from bot.misc import TgConfig
from bot.localization import t
from bot.utils import safe_edit_message_text


_TOOLS_TEXTS = {
    'en': {
        'main': '🛠️ <b>Administrator tools</b>\nChoose a category to continue.',
        'games': '🎮 <b>Game utilities</b>\nManage entertainment modules for your users.',
        'profile': '👤 <b>Profile controls</b>\nToggle and fine-tune user profile features.',
        'team': '🤝 <b>Team management</b>\nAssign trusted owners and assistants.',
        'sales': '🏷️ <b>Sales toolkit</b>\nControl reseller access and promo codes.',
        'broadcast': '📣 <b>Communication</b>\nSend targeted announcements to your audience.',
    },
    'lt': {
        'main': '🛠️ <b>Įrankių meniu</b>\nPasirinkite dominančią kategoriją.',
        'games': '🎮 <b>Žaidimų valdymas</b>\nTvarkykite pramogų modulius savo vartotojams.',
        'profile': '👤 <b>Profilio valdymas</b>\nĮjunkite ar išjunkite profilio funkcijas bei jas derinkite.',
        'team': '🤝 <b>Komandos valdymas</b>\nPriskirkite savininkus ir asistentus.',
        'sales': '🏷️ <b>Pardavimo įrankiai</b>\nValdykite resellerius ir nuolaidų kodus.',
        'broadcast': '📣 <b>Komunikacija</b>\nSiųskite žinutes savo auditorijai.',
    },
    'ru': {
        'main': '🛠️ <b>Панель инструментов</b>\nВыберите нужную категорию.',
        'games': '🎮 <b>Игровые модули</b>\nУправляйте развлечениями для пользователей.',
        'profile': '👤 <b>Управление профилем</b>\nВключайте, отключайте и настраивайте функции профиля.',
        'team': '🤝 <b>Команда</b>\nНазначайте владельцев и ассистентов.',
        'sales': '🏷️ <b>Инструменты продаж</b>\nКонтролируйте реселлеров и промокоды.',
        'broadcast': '📣 <b>Коммуникации</b>\nРассылайте сообщения своей аудитории.',
    },
}

_PROFILE_STATUS = {
    'en': {True: 'Enabled', False: 'Disabled'},
    'lt': {True: 'Įjungta', False: 'Išjungta'},
    'ru': {True: 'Вкл.', False: 'Выкл.'},
}

_PROFILE_LINES = {
    'en': {
        'title': '👤 <b>Profile controls</b>',
        'profile': 'Profile menu: <b>{status}</b>',
        'blackjack': 'Blackjack: <b>{status}</b> (max {max_bet}€)',
        'quests': 'Quests: <b>{status}</b>',
        'missions': 'Missions: <b>{status}</b>',
        'quests_desc': '🧩 Quests text: {text}',
        'missions_desc': '🎯 Missions text: {text}',
    },
    'lt': {
        'title': '👤 <b>Profilio funkcijos</b>',
        'profile': 'Profilio meniu: <b>{status}</b>',
        'blackjack': 'Blackjack: <b>{status}</b> (maks. {max_bet}€)',
        'quests': 'Uždaviniai: <b>{status}</b>',
        'missions': 'Misijos: <b>{status}</b>',
        'quests_desc': '🧩 Uždavinių tekstas: {text}',
        'missions_desc': '🎯 Misijų tekstas: {text}',
    },
    'ru': {
        'title': '👤 <b>Настройки профиля</b>',
        'profile': 'Меню профиля: <b>{status}</b>',
        'blackjack': 'Blackjack: <b>{status}</b> (макс. {max_bet}€)',
        'quests': 'Задания: <b>{status}</b>',
        'missions': 'Миссии: <b>{status}</b>',
        'quests_desc': '🧩 Текст заданий: {text}',
        'missions_desc': '🎯 Текст миссий: {text}',
    },
}


def _tools_text(lang: str, key: str) -> str:
    translations = _TOOLS_TEXTS.get(lang, _TOOLS_TEXTS['en'])
    if key in translations:
        return translations[key]
    return _TOOLS_TEXTS['en'][key]


def _profile_overview_text(lang: str, settings: dict) -> str:
    status_words = _PROFILE_STATUS.get(lang, _PROFILE_STATUS['en'])
    lines_conf = _PROFILE_LINES.get(lang, _PROFILE_LINES['en'])
    lines = [lines_conf['title'], '']
    lines.append(lines_conf['profile'].format(status=status_words[settings.get('profile_enabled', True)]))
    lines.append(
        lines_conf['blackjack'].format(
            status=status_words[settings.get('blackjack_enabled', True)],
            max_bet=settings.get('blackjack_max_bet', 5),
        )
    )
    lines.append(lines_conf['quests'].format(status=status_words[settings.get('quests_enabled', True)]))
    lines.append(lines_conf['missions'].format(status=status_words[settings.get('missions_enabled', False)]))
    quests_desc = settings.get('quests_description')
    missions_desc = settings.get('missions_description')
    if quests_desc:
        lines.extend(['', lines_conf['quests_desc'].format(text=quests_desc)])
    if missions_desc:
        lines.extend(['', lines_conf['missions_desc'].format(text=missions_desc)])
    return '\n'.join(lines)


def _can_manage_profile(role: int) -> bool:
    return bool(role & (Permission.SETTINGS_MANAGE | Permission.OWN))


def _pick_winner():
    users = get_users_with_tickets()
    if not users:
        return None
    total = sum(u[2] for u in users)
    r = random.randint(1, total)
    cumulative = 0
    for u in users:
        cumulative += u[2]
        if r <= cumulative:
            return u
    return None


async def miscs_callback_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    TgConfig.STATE[user_id] = None
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if role != Permission.USE:
        await safe_edit_message_text(bot,
            _tools_text(lang, 'main'),
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=tools_menu(role),
            parse_mode='HTML',
        )
        return
    await call.answer(t(lang, 'insufficient_rights'))


async def tools_games_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    await safe_edit_message_text(bot,
        _tools_text(lang, 'games'),
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=tools_games_menu(role),
        parse_mode='HTML',
    )


async def _render_profile_menu(bot, chat_id: int, message_id: int, lang: str, settings: dict | None = None):
    profile_settings = settings or get_profile_settings()
    await safe_edit_message_text(
        bot,
        _profile_overview_text(lang, profile_settings),
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=tools_profile_menu(profile_settings),
        parse_mode='HTML',
    )


async def tools_profile_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not _can_manage_profile(role):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    settings = get_profile_settings()
    await _render_profile_menu(
        bot,
        call.message.chat.id,
        call.message.message_id,
        lang,
        settings,
    )


async def tools_team_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.OWN):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    await safe_edit_message_text(bot,
        _tools_text(lang, 'team'),
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=tools_team_menu(role),
        parse_mode='HTML',
    )


async def tools_sales_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.SHOP_MANAGE):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    await safe_edit_message_text(bot,
        _tools_text(lang, 'sales'),
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=tools_sales_menu(role),
        parse_mode='HTML',
    )


async def tools_broadcast_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.BROADCAST):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    await safe_edit_message_text(bot,
        _tools_text(lang, 'broadcast'),
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=tools_broadcast_menu(role),
        parse_mode='HTML',
    )


async def profile_toggle_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not _can_manage_profile(role):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    feature = call.data.split(':', 1)[1]
    current = get_profile_settings()
    try:
        updated = toggle_profile_feature(feature, not current.get(feature, False))
    except ValueError:
        await call.answer('Unsupported feature', show_alert=True)
        return
    await call.answer(t(lang, 'settings_saved'))
    await _render_profile_menu(
        bot,
        call.message.chat.id,
        call.message.message_id,
        lang,
        updated,
    )


async def profile_blackjack_max_bet_prompt(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not _can_manage_profile(role):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    settings = get_profile_settings()
    TgConfig.STATE[user_id] = 'profile_settings:blackjack_max_bet'
    TgConfig.STATE[f'{user_id}_profile_message'] = call.message.message_id
    TgConfig.STATE[f'{user_id}_profile_chat'] = call.message.chat.id
    prompt = await call.message.answer(t(lang, 'enter_blackjack_max_bet', current=settings.get('blackjack_max_bet', 5)))
    TgConfig.STATE[f'{user_id}_profile_prompt'] = prompt.message_id


async def profile_edit_quests_prompt(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not _can_manage_profile(role):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    settings = get_profile_settings()
    TgConfig.STATE[user_id] = 'profile_settings:quests_description'
    TgConfig.STATE[f'{user_id}_profile_message'] = call.message.message_id
    TgConfig.STATE[f'{user_id}_profile_chat'] = call.message.chat.id
    placeholder = settings.get('quests_description') or t(lang, 'no_text_configured')
    prompt = await call.message.answer(t(lang, 'enter_quests_description', current=placeholder))
    TgConfig.STATE[f'{user_id}_profile_prompt'] = prompt.message_id


async def profile_edit_missions_prompt(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not _can_manage_profile(role):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    settings = get_profile_settings()
    TgConfig.STATE[user_id] = 'profile_settings:missions_description'
    TgConfig.STATE[f'{user_id}_profile_message'] = call.message.message_id
    TgConfig.STATE[f'{user_id}_profile_chat'] = call.message.chat.id
    placeholder = settings.get('missions_description') or t(lang, 'no_text_configured')
    prompt = await call.message.answer(t(lang, 'enter_missions_description', current=placeholder))
    TgConfig.STATE[f'{user_id}_profile_prompt'] = prompt.message_id


async def profile_settings_receive_input(message: Message):
    bot, user_id = await get_bot_user_ids(message)
    state = TgConfig.STATE.get(user_id)
    if not state or not str(state).startswith('profile_settings:'):
        return
    _, key = str(state).split(':', 1)
    lang = get_user_language(user_id) or 'en'
    chat_id = TgConfig.STATE.pop(f'{user_id}_profile_chat', message.chat.id)
    msg_id = TgConfig.STATE.pop(f'{user_id}_profile_message', None)
    prompt_id = TgConfig.STATE.pop(f'{user_id}_profile_prompt', None)
    text = message.text.strip() if message.text else ''
    try:
        if key == 'blackjack_max_bet':
            value = int(text)
            settings = set_blackjack_max_bet(value)
        elif key == 'quests_description':
            settings = set_profile_text('quests_description', text)
        elif key == 'missions_description':
            settings = set_profile_text('missions_description', text)
        else:
            await message.answer('Unsupported setting')
            TgConfig.STATE[user_id] = None
            return
    except ValueError:
        if key == 'blackjack_max_bet':
            await message.answer(t(lang, 'invalid_number'))
        else:
            await message.answer(t(lang, 'invalid_text'))
        return
    TgConfig.STATE[user_id] = None
    with contextlib.suppress(Exception):
        await message.delete()
    if prompt_id:
        with contextlib.suppress(Exception):
            await bot.delete_message(chat_id, prompt_id)
    if msg_id is not None:
        await _render_profile_menu(bot, chat_id, msg_id, lang, settings)


async def lottery_callback_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    TgConfig.STATE[user_id] = None
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if role != Permission.USE:
        await safe_edit_message_text(bot, 
            t(lang, 'lottery'),
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=lottery_menu(),
        )
        return
    await call.answer(t(lang, 'insufficient_rights'))


async def view_tickets_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    lang = get_user_language(user_id) or 'en'
    users = get_users_with_tickets()
    lines = [t(lang, 'users_tickets')]
    if not users:
        lines.append(t(lang, 'no_tickets'))
    else:
        for uid, username, count in users:
            name = f'@{username}' if username else str(uid)
            lines.append(f'{name} — {count}')
    await safe_edit_message_text(bot, 
        '\n'.join(lines),
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=back('lottery'),
    )


async def run_lottery_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    lang = get_user_language(user_id) or 'en'
    winner = _pick_winner()
    if not winner:
        await safe_edit_message_text(bot, 
            t(lang, 'no_tickets'),
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=back('lottery'),
        )
        return
    TgConfig.STATE['lottery_winner'] = winner
    username = f'@{winner[1]}' if winner[1] else str(winner[0])
    text = t(lang, 'lottery_winner', username=username, tickets=winner[2])
    await safe_edit_message_text(bot, 
        text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=lottery_run_menu(lang),
    )


async def lottery_confirm_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    if not TgConfig.STATE.get('lottery_winner'):
        lang = get_user_language(user_id) or 'en'
        await call.answer(t(lang, 'no_winner'))
        return
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    await safe_edit_message_text(bot, 
        t(lang, 'lottery_broadcast_prompt'),
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=lottery_broadcast_menu(role, lang),
    )


async def lottery_rerun_handler(call: CallbackQuery):
    await run_lottery_handler(call)


async def lottery_cancel_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    TgConfig.STATE.pop('lottery_winner', None)
    await safe_edit_message_text(bot, 
        '🎟️ Loterija',
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=lottery_menu(),
    )


async def lottery_broadcast_yes(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    lang = get_user_language(user_id) or 'en'
    TgConfig.STATE[user_id] = 'lottery_broadcast_message'
    TgConfig.STATE[f'{user_id}_message_id'] = call.message.message_id
    await safe_edit_message_text(bot, 
        t(lang, 'lottery_enter_message'),
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
    )


async def lottery_broadcast_no(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    lang = get_user_language(user_id) or 'en'
    reset_lottery_tickets()
    TgConfig.STATE.pop('lottery_winner', None)
    await safe_edit_message_text(bot, 
        t(lang, 'lottery_finished'),
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=back('lottery'),
    )


async def lottery_broadcast_message(message: Message):
    bot = message.bot
    user_id = message.from_user.id
    if TgConfig.STATE.get(user_id) != 'lottery_broadcast_message':
        return
    text = message.text
    users = get_all_users()
    for uid, in users:
        try:
            await bot.send_message(uid, text)
        except Exception:
            continue
    reset_lottery_tickets()
    TgConfig.STATE.pop('lottery_winner', None)
    TgConfig.STATE[user_id] = None
    TgConfig.STATE.pop(f'{user_id}_message_id', None)
    await bot.send_message(user_id, '✅ Loterija baigta.', reply_markup=back('lottery'))


def register_miscs(dp: Dispatcher) -> None:
    dp.register_callback_query_handler(miscs_callback_handler, lambda c: c.data == 'miscs', state='*')
    dp.register_callback_query_handler(tools_games_handler, lambda c: c.data == 'tools_cat_games', state='*')
    dp.register_callback_query_handler(
        tools_profile_handler,
        lambda c: c.data in ('tools_cat_profile', 'profile_blackjack_settings'),
        state='*',
    )
    dp.register_callback_query_handler(tools_team_handler, lambda c: c.data == 'tools_cat_team', state='*')
    dp.register_callback_query_handler(tools_sales_handler, lambda c: c.data == 'tools_cat_sales', state='*')
    dp.register_callback_query_handler(tools_broadcast_handler, lambda c: c.data == 'tools_cat_broadcast', state='*')
    dp.register_callback_query_handler(profile_toggle_handler, lambda c: c.data.startswith('profile_toggle:'), state='*')
    dp.register_callback_query_handler(profile_blackjack_max_bet_prompt, lambda c: c.data == 'profile_blackjack_max_bet', state='*')
    dp.register_callback_query_handler(profile_edit_quests_prompt, lambda c: c.data == 'profile_edit_quests', state='*')
    dp.register_callback_query_handler(profile_edit_missions_prompt, lambda c: c.data == 'profile_edit_missions', state='*')
    dp.register_message_handler(
        profile_settings_receive_input,
        lambda m: str(TgConfig.STATE.get(m.from_user.id, '')).startswith('profile_settings:'),
        state='*',
    )
    dp.register_callback_query_handler(lottery_callback_handler, lambda c: c.data == 'lottery', state='*')
    dp.register_callback_query_handler(view_tickets_handler, lambda c: c.data == 'view_tickets', state='*')
    dp.register_callback_query_handler(run_lottery_handler, lambda c: c.data == 'run_lottery', state='*')
    dp.register_callback_query_handler(lottery_confirm_handler, lambda c: c.data == 'lottery_confirm', state='*')
    dp.register_callback_query_handler(lottery_rerun_handler, lambda c: c.data == 'lottery_rerun', state='*')
    dp.register_callback_query_handler(lottery_cancel_handler, lambda c: c.data == 'lottery_cancel', state='*')
    dp.register_callback_query_handler(lottery_broadcast_yes, lambda c: c.data == 'lottery_broadcast_yes', state='*')
    dp.register_callback_query_handler(lottery_broadcast_no, lambda c: c.data == 'lottery_broadcast_no', state='*')
    dp.register_message_handler(
        lottery_broadcast_message,
        lambda m: TgConfig.STATE.get(m.from_user.id) == 'lottery_broadcast_message',
    )
