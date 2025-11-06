from aiogram import Dispatcher
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
import contextlib
import html
import random
import re

from bot.constants.achievements import DEFAULT_ACHIEVEMENTS
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
    list_terms,
    get_term,
    create_or_update_term,
    delete_term,
    term_usage_stats,
    get_weekly_quest,
    set_weekly_quest_titles,
    set_weekly_quest_reset,
    add_weekly_quest_task,
    update_weekly_quest_task,
    delete_weekly_quest_task,
    set_weekly_quest_reward,
    list_achievements,
    get_achievement,
    set_achievement_titles,
    configure_term_achievement,
    create_custom_achievement,
    delete_custom_achievement,
    normalise_term_code,
)
from bot.database.models import Permission
from bot.handlers.other import get_bot_user_ids
from bot.keyboards import (
    tools_menu,
    tools_games_menu,
    tools_profile_menu,
    tools_progress_menu,
    tools_team_menu,
    tools_sales_menu,
    tools_broadcast_menu,
    lottery_menu,
    lottery_run_menu,
    lottery_broadcast_menu,
    back,
)
from bot.keyboards.inline import _navback
from bot.misc import TgConfig
from bot.localization import t
from bot.utils import safe_edit_message_text


_TOOLS_TEXTS = {
    'en': {
        'main': '🛠️ <b>Administrator tools</b>\nChoose a category to continue.',
        'games': '🎮 <b>Game utilities</b>\nManage entertainment modules for your users.',
        'profile': '👤 <b>Profile controls</b>\nToggle and fine-tune user profile features.',
        'progress': '🚀 <b>Progress tools</b>\nConfigure levels, quests, achievements and terms.',
        'team': '🤝 <b>Team management</b>\nAssign trusted owners and assistants.',
        'sales': '🏷️ <b>Sales toolkit</b>\nControl reseller access and promo codes.',
        'broadcast': '📣 <b>Communication</b>\nSend targeted announcements to your audience.',
    },
    'lt': {
        'main': '🛠️ <b>Įrankių meniu</b>\nPasirinkite dominančią kategoriją.',
        'games': '🎮 <b>Žaidimų valdymas</b>\nTvarkykite pramogų modulius savo vartotojams.',
        'profile': '👤 <b>Profilio valdymas</b>\nĮjunkite ar išjunkite profilio funkcijas bei jas derinkite.',
        'progress': '🚀 <b>Progreso įrankiai</b>\nTvarkykite lygius, užduotis, pasiekimus ir terminus.',
        'team': '🤝 <b>Komandos valdymas</b>\nPriskirkite savininkus ir asistentus.',
        'sales': '🏷️ <b>Pardavimo įrankiai</b>\nValdykite resellerius ir nuolaidų kodus.',
        'broadcast': '📣 <b>Komunikacija</b>\nSiųskite žinutes savo auditorijai.',
    },
    'ru': {
        'main': '🛠️ <b>Панель инструментов</b>\nВыберите нужную категорию.',
        'games': '🎮 <b>Игровые модули</b>\nУправляйте развлечениями для пользователей.',
        'profile': '👤 <b>Управление профилем</b>\nВключайте, отключайте и настраивайте функции профиля.',
        'progress': '🚀 <b>Инструменты прогресса</b>\nНастраивайте уровни, квесты, достижения и термины.',
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


_TERM_LANGUAGES = ('lt', 'en', 'ru')


_WEEKDAY_LABELS = {
    'en': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
    'lt': ['Pirmadienis', 'Antradienis', 'Trečiadienis', 'Ketvirtadienis', 'Penktadienis', 'Šeštadienis', 'Sekmadienis'],
    'ru': ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'],
}


def _weekday_label(lang: str, index: int) -> str:
    names = _WEEKDAY_LABELS.get(lang) or _WEEKDAY_LABELS['en']
    if 0 <= index < len(names):
        return names[index]
    return names[0]


def _progress_message_id(user_id: int, fallback: int) -> int:
    message_id = TgConfig.STATE.get(f'{user_id}_progress_message', fallback)
    TgConfig.STATE[f'{user_id}_progress_message'] = message_id
    return message_id


def _detect_weekday_from_text(text: str) -> int | None:
    token = text.strip().lower()
    if not token:
        return None
    mapping = {
        'mon': 0,
        'monday': 0,
        'tue': 1,
        'tues': 1,
        'tuesday': 1,
        'wed': 2,
        'weds': 2,
        'wednesday': 2,
        'thu': 3,
        'thur': 3,
        'thurs': 3,
        'thursday': 3,
        'fri': 4,
        'friday': 4,
        'sat': 5,
        'saturday': 5,
        'sun': 6,
        'sunday': 6,
    }
    if token in mapping:
        return mapping[token]
    for names in _WEEKDAY_LABELS.values():
        for idx, name in enumerate(names):
            lower_name = name.lower()
            if token == lower_name or token == lower_name[:3]:
                return idx
    return None


def _language_label(lang: str, code: str) -> str:
    labels = {
        'lt': {'lt': 'Lietuvių', 'en': 'Anglų', 'ru': 'Rusų'},
        'en': {'lt': 'Lithuanian', 'en': 'English', 'ru': 'Russian'},
        'ru': {'lt': 'Литовский', 'en': 'Английский', 'ru': 'Русский'},
    }
    return labels.get(lang, labels['en']).get(code, code.upper())


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


async def _render_terms_menu(
    bot,
    chat_id: int,
    message_id: int,
    lang: str,
    user_id: int,
    notice: str | None = None,
) -> None:
    terms = list_terms()
    back_target = TgConfig.STATE.get(f'{user_id}_terms_back', 'tools_cat_progress')
    lines = [t(lang, 'tools_terms_title')]
    if notice:
        lines.extend(['', notice])
    if not terms:
        lines.extend(['', t(lang, 'tools_terms_empty')])
    else:
        lines.append('')
        for term in terms:
            labels = term.get('labels', {})
            display = labels.get(lang) or labels.get('en') or term['code']
            lines.append(f"<code>{term['code']}</code> — {html.escape(display)}")
    markup = InlineKeyboardMarkup(row_width=1)
    for term in terms:
        markup.add(InlineKeyboardButton(term['code'], callback_data=f'term_view_{term["code"]}'))
    markup.add(InlineKeyboardButton(t(lang, 'tools_terms_add_button'), callback_data='term_add'))
    markup.add(InlineKeyboardButton(t(lang, 'back'), callback_data=_navback(back_target)))
    await safe_edit_message_text(
        bot,
        '\n'.join(lines),
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


async def _render_term_detail(
    bot,
    chat_id: int,
    message_id: int,
    lang: str,
    user_id: int,
    code: str,
    notice: str | None = None,
) -> None:
    term = get_term(code)
    if term is None:
        await _render_terms_menu(
            bot,
            chat_id,
            message_id,
            lang,
            user_id,
            t(lang, 'tools_terms_code_invalid'),
        )
        return
    stats = term_usage_stats(code)
    lines = [t(lang, 'tools_terms_detail_header', code=code)]
    if notice:
        lines.extend(['', notice])
    lines.extend([
        '',
        t(lang, 'tools_terms_stats', products=stats['products'], sales=stats['sales']),
        '',
        t(lang, 'tools_terms_labels'),
    ])
    labels = term.get('labels', {})
    for language in _TERM_LANGUAGES:
        value = labels.get(language) or '—'
        lines.append(f"{_language_label(lang, language)}: {html.escape(value)}")
    markup = InlineKeyboardMarkup(row_width=2)
    for language in _TERM_LANGUAGES:
        markup.insert(
            InlineKeyboardButton(
                f'✏️ {_language_label(lang, language)}',
                callback_data=f'term_edit_{code}_{language}',
            )
        )
    if stats['products'] == 0:
        markup.add(InlineKeyboardButton(t(lang, 'tools_terms_delete_button'), callback_data=f'term_delete_{code}'))
    markup.add(InlineKeyboardButton(t(lang, 'back'), callback_data=_navback('tools_progress_terms')))
    await safe_edit_message_text(
        bot,
        '\n'.join(lines),
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


async def _prompt_next_term_label(bot, user_id: int, chat_id: int, message_id: int, lang: str) -> None:
    index = TgConfig.STATE.get(f'{user_id}_term_lang_index', 0)
    code = TgConfig.STATE.get(f'{user_id}_term_code')
    if code is None:
        await _render_terms_menu(bot, chat_id, message_id, lang, user_id)
        return
    if index >= len(_TERM_LANGUAGES):
        labels: dict = TgConfig.STATE.pop(f'{user_id}_term_labels', {})
        create_or_update_term(code, labels)
        TgConfig.STATE.pop(f'{user_id}_term_lang_index', None)
        TgConfig.STATE.pop(f'{user_id}_term_code', None)
        TgConfig.STATE[user_id] = None
        await _render_term_detail(
            bot,
            chat_id,
            message_id,
            lang,
            user_id,
            code,
            t(lang, 'tools_terms_saved', code=code),
        )
        return
    language = _TERM_LANGUAGES[index]
    prompt = t(lang, 'tools_terms_label_prompt', code=code, language=_language_label(lang, language))
    markup = InlineKeyboardMarkup().add(
        InlineKeyboardButton(t(lang, 'back'), callback_data=_navback('tools_progress_terms'))
    )
    await safe_edit_message_text(
        bot,
        prompt,
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


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


async def tools_progress_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.SHOP_MANAGE):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    message_id = call.message.message_id
    TgConfig.STATE[user_id] = None
    TgConfig.STATE[f'{user_id}_progress_message'] = message_id
    await call.answer()
    await safe_edit_message_text(
        bot,
        t(lang, 'tools_progress_title'),
        chat_id=call.message.chat.id,
        message_id=message_id,
        reply_markup=tools_progress_menu(),
        parse_mode='HTML',
    )


async def tools_terms_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.SHOP_MANAGE):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    message_id = _progress_message_id(user_id, call.message.message_id)
    state = str(TgConfig.STATE.get(user_id) or '')
    if state == 'create_item_term':
        TgConfig.STATE.setdefault(f'{user_id}_terms_back', 'item_term_prompt')
    elif state in {'quest_task_new_term'} or state.startswith('quest_task_edit_term:'):
        TgConfig.STATE[f'{user_id}_terms_back'] = 'quest_task_term_prompt'
    else:
        TgConfig.STATE[f'{user_id}_terms_back'] = 'tools_cat_progress'
    TgConfig.STATE[user_id] = None
    await call.answer()
    await _render_terms_menu(bot, call.message.chat.id, message_id, lang, user_id)


async def tools_term_detail_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.SHOP_MANAGE):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    code = call.data[len('term_view_'):]
    message_id = _progress_message_id(user_id, call.message.message_id)
    await call.answer()
    await _render_term_detail(bot, call.message.chat.id, message_id, lang, user_id, code)


async def tools_term_add_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.SHOP_MANAGE):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    message_id = _progress_message_id(user_id, call.message.message_id)
    TgConfig.STATE[user_id] = 'terms:create_code'
    await call.answer()
    markup = InlineKeyboardMarkup().add(
        InlineKeyboardButton(t(lang, 'back'), callback_data=_navback('tools_progress_terms'))
    )
    await safe_edit_message_text(
        bot,
        t(lang, 'tools_terms_code_prompt'),
        chat_id=call.message.chat.id,
        message_id=message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


async def terms_receive_code(message: Message):
    bot, user_id = await get_bot_user_ids(message)
    if TgConfig.STATE.get(user_id) != 'terms:create_code':
        return
    lang = get_user_language(user_id) or 'en'
    chat_id = message.chat.id
    message_id = _progress_message_id(user_id, message.message_id)
    code = normalise_term_code((message.text or '').strip())
    with contextlib.suppress(Exception):
        await bot.delete_message(chat_id=chat_id, message_id=message.message_id)
    if not code:
        await bot.send_message(chat_id, t(lang, 'tools_terms_code_invalid'))
        await _render_terms_menu(bot, chat_id, message_id, lang, user_id)
        return
    if get_term(code):
        await bot.send_message(chat_id, t(lang, 'tools_terms_code_exists'))
        await _render_terms_menu(bot, chat_id, message_id, lang, user_id)
        return
    TgConfig.STATE[f'{user_id}_term_code'] = code
    TgConfig.STATE[f'{user_id}_term_labels'] = {}
    TgConfig.STATE[f'{user_id}_term_lang_index'] = 0
    TgConfig.STATE[user_id] = 'terms:create_label'
    await _prompt_next_term_label(bot, user_id, chat_id, message_id, lang)


async def terms_receive_label(message: Message):
    bot, user_id = await get_bot_user_ids(message)
    if TgConfig.STATE.get(user_id) != 'terms:create_label':
        return
    lang = get_user_language(user_id) or 'en'
    chat_id = message.chat.id
    message_id = _progress_message_id(user_id, message.message_id)
    index = TgConfig.STATE.get(f'{user_id}_term_lang_index', 0)
    if index >= len(_TERM_LANGUAGES):
        TgConfig.STATE[user_id] = None
        await _render_terms_menu(bot, chat_id, message_id, lang, user_id)
        return
    labels: dict = TgConfig.STATE.get(f'{user_id}_term_labels', {})
    language = _TERM_LANGUAGES[index]
    labels[language] = (message.text or '').strip()
    TgConfig.STATE[f'{user_id}_term_labels'] = labels
    TgConfig.STATE[f'{user_id}_term_lang_index'] = index + 1
    with contextlib.suppress(Exception):
        await bot.delete_message(chat_id=chat_id, message_id=message.message_id)
    await _prompt_next_term_label(bot, user_id, chat_id, message_id, lang)


async def tools_term_edit_label_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.SHOP_MANAGE):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    _, _, code, language = call.data.split('_', 3)
    message_id = _progress_message_id(user_id, call.message.message_id)
    TgConfig.STATE[user_id] = 'terms:edit_label'
    TgConfig.STATE[f'{user_id}_term_code'] = code
    TgConfig.STATE[f'{user_id}_term_language'] = language
    await call.answer()
    markup = InlineKeyboardMarkup().add(
        InlineKeyboardButton(t(lang, 'back'), callback_data=_navback(f'term_view_{code}'))
    )
    await safe_edit_message_text(
        bot,
        t(lang, 'tools_terms_label_prompt', code=code, language=_language_label(lang, language)),
        chat_id=call.message.chat.id,
        message_id=message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


async def terms_receive_edit_label(message: Message):
    bot, user_id = await get_bot_user_ids(message)
    if TgConfig.STATE.get(user_id) != 'terms:edit_label':
        return
    lang = get_user_language(user_id) or 'en'
    code = TgConfig.STATE.get(f'{user_id}_term_code')
    language = TgConfig.STATE.get(f'{user_id}_term_language')
    chat_id = message.chat.id
    message_id = _progress_message_id(user_id, message.message_id)
    if not code or not language:
        TgConfig.STATE[user_id] = None
        await _render_terms_menu(bot, chat_id, message_id, lang, user_id)
        return
    term = get_term(code) or {'labels': {}}
    labels = term.get('labels', {})
    labels[language] = (message.text or '').strip()
    create_or_update_term(code, labels)
    TgConfig.STATE[user_id] = None
    TgConfig.STATE.pop(f'{user_id}_term_code', None)
    TgConfig.STATE.pop(f'{user_id}_term_language', None)
    with contextlib.suppress(Exception):
        await bot.delete_message(chat_id=chat_id, message_id=message.message_id)
    await _render_term_detail(bot, chat_id, message_id, lang, user_id, code, t(lang, 'tools_terms_saved', code=code))


async def tools_term_delete_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.SHOP_MANAGE):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    code = call.data[len('term_delete_'):]
    message_id = _progress_message_id(user_id, call.message.message_id)
    await call.answer()
    try:
        delete_term(code)
    except ValueError:
        await _render_term_detail(
            bot,
            call.message.chat.id,
            message_id,
            lang,
            user_id,
            code,
            t(lang, 'tools_terms_in_use'),
        )
        return
    await _render_terms_menu(
        bot,
        call.message.chat.id,
        message_id,
        lang,
        user_id,
        t(lang, 'tools_terms_deleted', code=code),
    )


async def _render_quest_overview(bot, chat_id: int, message_id: int, lang: str, notice: str | None = None) -> None:
    quest = get_weekly_quest()
    titles = quest.get('titles', {}) or {}
    current_title = titles.get(lang) or titles.get('en') or next(iter(titles.values()), {})
    if isinstance(current_title, dict):
        display_title = str(current_title.get('title') or '').strip()
        description = str(current_title.get('description') or '').strip()
    else:
        display_title = str(current_title or '').strip()
        description = ''
    reward = quest.get('reward', {}) or {}
    reward_type = reward.get('type', 'discount')
    reward_value = reward.get('value')
    reward_titles = reward.get('title', {}) or {}
    reward_title = str(
        reward_titles.get(lang)
        or reward_titles.get('en')
        or next(iter(reward_titles.values()), ''),
    ).strip()
    tasks = quest.get('tasks', []) or []
    reset_weekday = int(quest.get('reset_weekday', 0))
    reset_hour = int(quest.get('reset_hour', 12))

    lines = [t(lang, 'tools_quest_heading')]
    if notice:
        lines.extend(['', notice])
    if display_title:
        lines.append(t(lang, 'tools_quest_current_title', title=html.escape(display_title)))
    if description:
        lines.append(t(lang, 'tools_quest_current_description', description=html.escape(description)))
    schedule = t(
        lang,
        'tools_quest_schedule',
        weekday=_weekday_label(lang, reset_weekday),
        hour=f'{reset_hour:02d}:00',
    )
    lines.extend(['', schedule])
    if reward_type == 'discount':
        reward_line = t(lang, 'tools_quest_reward_discount', percent=reward_value or 0)
    else:
        reward_line = t(lang, 'tools_quest_reward_stock', value=html.escape(str(reward_value or '')))
    lines.extend(['', reward_line])
    if reward_title:
        lines.append(t(lang, 'tools_quest_reward_title_line', text=html.escape(reward_title)))
    lines.append('')
    if tasks:
        lines.append(t(lang, 'tools_quest_tasks_header'))
        for idx, task in enumerate(tasks, start=1):
            task_title_map = task.get('titles', {}) or {}
            task_title = str(
                task_title_map.get(lang)
                or task_title_map.get('en')
                or next(iter(task_title_map.values()), ''),
            ).strip()
            lines.append(
                t(
                    lang,
                    'tools_quest_task_line',
                    index=idx,
                    term=task.get('term', '—'),
                    count=task.get('count', 0),
                    title=html.escape(task_title),
                )
            )
    else:
        lines.append(t(lang, 'tools_quest_tasks_empty'))

    markup = InlineKeyboardMarkup(row_width=2)
    markup.row(
        InlineKeyboardButton(t(lang, 'tools_quest_btn_titles'), callback_data='quest_titles'),
        InlineKeyboardButton(t(lang, 'tools_quest_btn_tasks'), callback_data='quest_tasks'),
    )
    markup.row(
        InlineKeyboardButton(t(lang, 'tools_quest_btn_reward'), callback_data='quest_reward'),
        InlineKeyboardButton(t(lang, 'tools_quest_btn_reset'), callback_data='quest_reset'),
    )
    markup.add(InlineKeyboardButton(t(lang, 'back'), callback_data=_navback('tools_cat_progress')))

    await safe_edit_message_text(
        bot,
        '\n'.join(lines),
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


async def tools_progress_quest_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.SHOP_MANAGE):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    message_id = _progress_message_id(user_id, call.message.message_id)
    TgConfig.STATE[user_id] = None
    await call.answer()
    await _render_quest_overview(bot, call.message.chat.id, message_id, lang)


async def _render_quest_titles_menu(bot, chat_id: int, message_id: int, lang: str) -> None:
    quest = get_weekly_quest()
    titles = quest.get('titles', {}) or {}
    lines = [t(lang, 'tools_quest_titles_heading')]
    for language in _TERM_LANGUAGES:
        entry = titles.get(language, {})
        if isinstance(entry, dict):
            preview = entry.get('title') or ''
        else:
            preview = entry or ''
        lines.append(
            t(
                lang,
                'tools_quest_title_line',
                language=_language_label(lang, language),
                title=html.escape(str(preview).strip()),
            )
        )
    markup = InlineKeyboardMarkup(row_width=2)
    for language in _TERM_LANGUAGES:
        markup.insert(
            InlineKeyboardButton(
                _language_label(lang, language),
                callback_data=f'quest_titles_lang_{language}',
            )
        )
    markup.add(InlineKeyboardButton(t(lang, 'back'), callback_data='tools_progress_quest'))
    await safe_edit_message_text(
        bot,
        '\n'.join(lines),
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


async def quest_titles_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.SHOP_MANAGE):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    message_id = _progress_message_id(user_id, call.message.message_id)
    TgConfig.STATE[user_id] = None
    await call.answer()
    await _render_quest_titles_menu(bot, call.message.chat.id, message_id, lang)


async def quest_titles_language_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.SHOP_MANAGE):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    language = call.data.rsplit('_', 1)[-1]
    message_id = _progress_message_id(user_id, call.message.message_id)
    quest = get_weekly_quest()
    entry = quest.get('titles', {}).get(language, {})
    if isinstance(entry, dict):
        current_title = str(entry.get('title') or '').strip()
        current_description = str(entry.get('description') or '').strip()
    else:
        current_title = str(entry or '').strip()
        current_description = ''
    prompt = t(
        lang,
        'tools_quest_titles_edit_prompt',
        language=_language_label(lang, language),
        title=current_title,
        description=current_description,
    )
    TgConfig.STATE[user_id] = f'quest_titles:{language}'
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton(t(lang, 'back'), callback_data='quest_titles'))
    await call.answer()
    await safe_edit_message_text(
        bot,
        prompt,
        chat_id=call.message.chat.id,
        message_id=message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


async def quest_titles_receive(message: Message):
    bot, user_id = await get_bot_user_ids(message)
    state = TgConfig.STATE.get(user_id)
    if not state or not str(state).startswith('quest_titles:'):
        return
    language = str(state).split(':', 1)[1]
    lang = get_user_language(user_id) or 'en'
    text = (message.text or '').strip()
    title = ''
    description = ''
    if text:
        parts = text.split('\n', 1)
        title = parts[0].strip()
        if len(parts) > 1:
            description = parts[1].strip()
    set_weekly_quest_titles(language, title, description)
    TgConfig.STATE[user_id] = None
    with contextlib.suppress(Exception):
        await message.delete()
    notice = t(lang, 'tools_quest_titles_saved', language=_language_label(lang, language))
    message_id = _progress_message_id(user_id, message.message_id)
    await _render_quest_overview(bot, message.chat.id, message_id, lang, notice)


async def quest_reset_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.SHOP_MANAGE):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    message_id = _progress_message_id(user_id, call.message.message_id)
    TgConfig.STATE[user_id] = 'quest_reset'
    quest = get_weekly_quest()
    prompt = t(
        lang,
        'tools_quest_reset_prompt',
        weekday=_weekday_label(lang, int(quest.get('reset_weekday', 0))),
        hour=f"{int(quest.get('reset_hour', 12)):02d}:00",
    )
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton(t(lang, 'back'), callback_data='tools_progress_quest'))
    await call.answer()
    await safe_edit_message_text(
        bot,
        prompt,
        chat_id=call.message.chat.id,
        message_id=message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


async def quest_reset_receive(message: Message):
    bot, user_id = await get_bot_user_ids(message)
    if TgConfig.STATE.get(user_id) != 'quest_reset':
        return
    lang = get_user_language(user_id) or 'en'
    quest = get_weekly_quest()
    existing_weekday = int(quest.get('reset_weekday', 0))
    existing_hour = int(quest.get('reset_hour', 12))
    text = message.text or ''
    numbers = re.findall(r'\d+', text)
    explicit = bool(numbers)
    weekday = None
    hour = None
    if numbers:
        try:
            weekday = int(numbers[0])
        except ValueError:
            weekday = existing_weekday
        if len(numbers) >= 2:
            try:
                hour = int(numbers[1])
            except ValueError:
                hour = existing_hour
    for token in re.split(r'\s+', text):
        candidate = _detect_weekday_from_text(token)
        if candidate is not None:
            weekday = candidate
            explicit = True
            break
    if not explicit:
        await message.answer(t(lang, 'tools_quest_reset_invalid'))
        return
    if weekday is None:
        weekday = existing_weekday
    weekday = max(0, min(6, weekday))
    if hour is None:
        hour = existing_hour
    hour = max(0, min(23, hour))
    set_weekly_quest_reset(weekday, hour)
    TgConfig.STATE[user_id] = None
    with contextlib.suppress(Exception):
        await message.delete()
    notice = t(
        lang,
        'tools_quest_reset_saved',
        weekday=_weekday_label(lang, weekday),
        hour=f'{hour:02d}:00',
    )
    message_id = _progress_message_id(user_id, message.message_id)
    await _render_quest_overview(bot, message.chat.id, message_id, lang, notice)


async def _render_quest_reward_menu(bot, chat_id: int, message_id: int, lang: str, notice: str | None = None) -> None:
    quest = get_weekly_quest()
    reward = quest.get('reward', {}) or {}
    reward_type = reward.get('type', 'discount')
    reward_value = reward.get('value')
    reward_titles = reward.get('title', {}) or {}
    reward_title = str(
        reward_titles.get(lang)
        or reward_titles.get('en')
        or next(iter(reward_titles.values()), ''),
    ).strip()
    lines = [t(lang, 'tools_quest_reward_heading')]
    if notice:
        lines.extend(['', notice])
    if reward_type == 'discount':
        lines.append(t(lang, 'tools_quest_reward_discount', percent=reward_value or 0))
    else:
        lines.append(t(lang, 'tools_quest_reward_stock', value=html.escape(str(reward_value or ''))))
    if reward_title:
        lines.append(t(lang, 'tools_quest_reward_title_line', text=html.escape(reward_title)))
    markup = InlineKeyboardMarkup(row_width=2)
    markup.row(
        InlineKeyboardButton(t(lang, 'tools_quest_reward_discount_btn'), callback_data='quest_reward_type_discount'),
        InlineKeyboardButton(t(lang, 'tools_quest_reward_stock_btn'), callback_data='quest_reward_type_stock'),
    )
    markup.add(InlineKeyboardButton(t(lang, 'tools_quest_reward_titles_btn'), callback_data='quest_reward_titles'))
    markup.add(InlineKeyboardButton(t(lang, 'back'), callback_data='tools_progress_quest'))
    await safe_edit_message_text(
        bot,
        '\n'.join(lines),
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


async def quest_reward_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.SHOP_MANAGE):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    message_id = _progress_message_id(user_id, call.message.message_id)
    TgConfig.STATE[user_id] = None
    await call.answer()
    await _render_quest_reward_menu(bot, call.message.chat.id, message_id, lang)


async def quest_reward_set_discount_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.SHOP_MANAGE):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    message_id = _progress_message_id(user_id, call.message.message_id)
    TgConfig.STATE[user_id] = 'quest_reward:discount'
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton(t(lang, 'back'), callback_data='quest_reward'))
    await call.answer()
    await safe_edit_message_text(
        bot,
        t(lang, 'tools_quest_reward_discount_prompt'),
        chat_id=call.message.chat.id,
        message_id=message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


async def quest_reward_set_stock_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.SHOP_MANAGE):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    message_id = _progress_message_id(user_id, call.message.message_id)
    TgConfig.STATE[user_id] = 'quest_reward:stock'
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton(t(lang, 'back'), callback_data='quest_reward'))
    await call.answer()
    await safe_edit_message_text(
        bot,
        t(lang, 'tools_quest_reward_stock_prompt'),
        chat_id=call.message.chat.id,
        message_id=message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


async def quest_reward_titles_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.SHOP_MANAGE):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    message_id = _progress_message_id(user_id, call.message.message_id)
    lines = [t(lang, 'tools_quest_reward_titles_prompt')]
    markup = InlineKeyboardMarkup(row_width=2)
    for language in _TERM_LANGUAGES:
        markup.insert(
            InlineKeyboardButton(
                _language_label(lang, language),
                callback_data=f'quest_reward_title_{language}',
            )
        )
    markup.add(InlineKeyboardButton(t(lang, 'back'), callback_data='quest_reward'))
    await call.answer()
    await safe_edit_message_text(
        bot,
        '\n'.join(lines),
        chat_id=call.message.chat.id,
        message_id=message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


async def quest_reward_title_language_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.SHOP_MANAGE):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    language = call.data.split('_', 2)[-1]
    quest = get_weekly_quest()
    reward = quest.get('reward', {}) or {}
    reward_titles = reward.get('title', {}) or {}
    existing = str(reward_titles.get(language, '')).strip()
    message_id = _progress_message_id(user_id, call.message.message_id)
    TgConfig.STATE[user_id] = f'quest_reward_title:{language}'
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton(t(lang, 'back'), callback_data='quest_reward_titles'))
    prompt = t(lang, 'tools_quest_reward_title_prompt', language=_language_label(lang, language), current=existing)
    await call.answer()
    await safe_edit_message_text(
        bot,
        prompt,
        chat_id=call.message.chat.id,
        message_id=message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


async def quest_reward_receive_input(message: Message):
    bot, user_id = await get_bot_user_ids(message)
    state = str(TgConfig.STATE.get(user_id))
    if state not in ('quest_reward:discount', 'quest_reward:stock'):
        return
    lang = get_user_language(user_id) or 'en'
    quest = get_weekly_quest()
    reward = quest.get('reward', {}) or {}
    reward_titles = reward.get('title', {}) or {}
    message_id = _progress_message_id(user_id, message.message_id)
    if state.endswith('discount'):
        try:
            value = int((message.text or '').strip())
        except (TypeError, ValueError):
            await message.answer(t(lang, 'invalid_number'))
            return
        value = max(0, min(100, value))
        set_weekly_quest_reward({'type': 'discount', 'value': value, 'title': reward_titles})
        notice = t(lang, 'tools_quest_reward_discount_saved', percent=value)
    else:
        text = (message.text or '').strip()
        if not text:
            await message.answer(t(lang, 'invalid_text'))
            return
        set_weekly_quest_reward({'type': 'stock', 'value': text, 'title': reward_titles})
        notice = t(lang, 'tools_quest_reward_stock_saved', value=html.escape(text))
    TgConfig.STATE[user_id] = None
    with contextlib.suppress(Exception):
        await message.delete()
    await _render_quest_reward_menu(bot, message.chat.id, message_id, lang, notice)


async def quest_reward_receive_title(message: Message):
    bot, user_id = await get_bot_user_ids(message)
    state = str(TgConfig.STATE.get(user_id))
    if not state.startswith('quest_reward_title:'):
        return
    _, language = state.split(':', 1)
    lang = get_user_language(user_id) or 'en'
    quest = get_weekly_quest()
    reward = quest.get('reward', {}) or {}
    reward_titles = reward.get('title', {}) or {}
    reward_titles[language] = (message.text or '').strip()
    payload = {
        'type': reward.get('type', 'discount'),
        'value': reward.get('value'),
        'title': reward_titles,
    }
    set_weekly_quest_reward(payload)
    TgConfig.STATE[user_id] = None
    with contextlib.suppress(Exception):
        await message.delete()
    notice = t(lang, 'tools_quest_reward_title_saved', language=_language_label(lang, language))
    message_id = _progress_message_id(user_id, message.message_id)
    await _render_quest_reward_menu(bot, message.chat.id, message_id, lang, notice)


async def _render_quest_tasks_menu(bot, chat_id: int, message_id: int, lang: str, notice: str | None = None) -> None:
    quest = get_weekly_quest()
    tasks = quest.get('tasks', []) or []
    lines = [t(lang, 'tools_quest_tasks_overview')]
    if notice:
        lines.extend(['', notice])
    if tasks:
        for idx, task in enumerate(tasks, start=1):
            lines.append(
                t(
                    lang,
                    'tools_quest_task_summary',
                    index=idx,
                    term=task.get('term', '—'),
                    count=task.get('count', 0),
                )
            )
    else:
        lines.append(t(lang, 'tools_quest_tasks_empty'))
    markup = InlineKeyboardMarkup(row_width=1)
    for task in tasks:
        code = task.get('id')
        label = t(
            lang,
            'tools_quest_task_button',
            term=task.get('term', '—'),
            count=task.get('count', 0),
        )
        markup.add(InlineKeyboardButton(label, callback_data=f'quest_task_view_{code}'))
    markup.add(InlineKeyboardButton(t(lang, 'tools_quest_task_add'), callback_data='quest_task_add'))
    markup.add(InlineKeyboardButton(t(lang, 'back'), callback_data='tools_progress_quest'))
    await safe_edit_message_text(
        bot,
        '\n'.join(lines),
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


async def tools_quest_tasks_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.SHOP_MANAGE):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    message_id = _progress_message_id(user_id, call.message.message_id)
    TgConfig.STATE[user_id] = None
    await call.answer()
    await _render_quest_tasks_menu(bot, call.message.chat.id, message_id, lang)


async def _render_quest_task_detail(bot, chat_id: int, message_id: int, lang: str, task_id: str, notice: str | None = None) -> None:
    quest = get_weekly_quest()
    tasks = quest.get('tasks', []) or []
    task = next((entry for entry in tasks if entry.get('id') == task_id), None)
    if task is None:
        await _render_quest_tasks_menu(bot, chat_id, message_id, lang, t(lang, 'tools_quest_task_missing'))
        return
    lines = [t(lang, 'tools_quest_task_header', term=task.get('term', '—'))]
    if notice:
        lines.extend(['', notice])
    lines.append(t(lang, 'tools_quest_task_detail_term', term=task.get('term', '—')))
    lines.append(t(lang, 'tools_quest_task_detail_count', count=task.get('count', 0)))
    titles = task.get('titles', {}) or {}
    lines.append('')
    lines.append(t(lang, 'tools_quest_task_titles_header'))
    for language in _TERM_LANGUAGES:
        lines.append(
            t(
                lang,
                'tools_quest_task_title_line',
                language=_language_label(lang, language),
                title=html.escape(str(titles.get(language, '')).strip()),
            )
        )
    markup = InlineKeyboardMarkup(row_width=2)
    markup.row(
        InlineKeyboardButton(t(lang, 'tools_quest_task_edit_term'), callback_data=f'quest_task_term_{task_id}'),
        InlineKeyboardButton(t(lang, 'tools_quest_task_edit_count'), callback_data=f'quest_task_count_{task_id}'),
    )
    markup.add(InlineKeyboardButton(t(lang, 'tools_quest_task_edit_titles'), callback_data=f'quest_task_titles_{task_id}'))
    markup.add(InlineKeyboardButton(t(lang, 'tools_quest_task_delete'), callback_data=f'quest_task_delete_{task_id}'))
    markup.add(InlineKeyboardButton(t(lang, 'back'), callback_data='quest_tasks'))
    await safe_edit_message_text(
        bot,
        '\n'.join(lines),
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


async def quest_task_view_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.SHOP_MANAGE):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    task_id = call.data[len('quest_task_view_'):]
    message_id = _progress_message_id(user_id, call.message.message_id)
    await call.answer()
    await _render_quest_task_detail(bot, call.message.chat.id, message_id, lang, task_id)


async def _render_task_term_selection(
    bot,
    chat_id: int,
    message_id: int,
    lang: str,
    user_id: int,
    target: str,
    notice: str | None = None,
) -> None:
    terms = list_terms()
    lines = [t(lang, 'tools_quest_select_term')]
    if notice:
        lines.extend(['', notice])
    if not terms:
        lines.append('')
        lines.append(t(lang, 'tools_quest_no_terms'))
    markup = InlineKeyboardMarkup(row_width=2)
    TgConfig.STATE[f'{user_id}_terms_back'] = 'quest_task_term_prompt'
    TgConfig.STATE[f'{user_id}_quest_term_target'] = target
    if terms:
        for term in terms:
            code = term.get('code')
            if target.startswith('edit:'):
                task_id = target.split(':', 1)[1]
                callback = f'quest_task_termselect:{task_id}:{code}'
            else:
                callback = f'quest_task_new_term:{code}'
            markup.insert(InlineKeyboardButton(code, callback_data=callback))
    markup.add(InlineKeyboardButton(t(lang, 'tools_quest_terms_manage'), callback_data='tools_progress_terms'))
    if target.startswith('edit:'):
        task_id = target.split(':', 1)[1]
        back_target = f'quest_task_view_{task_id}'
    else:
        back_target = 'quest_tasks'
    markup.add(InlineKeyboardButton(t(lang, 'back'), callback_data=_navback(back_target)))
    await safe_edit_message_text(
        bot,
        '\n'.join(lines),
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


async def quest_task_add_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.SHOP_MANAGE):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    message_id = _progress_message_id(user_id, call.message.message_id)
    TgConfig.STATE[user_id] = 'quest_task_new_term'
    await call.answer()
    await _render_task_term_selection(bot, call.message.chat.id, message_id, lang, user_id, 'new')


async def quest_task_select_term_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    lang = get_user_language(user_id) or 'en'
    if not str(TgConfig.STATE.get(user_id)).startswith('quest_task_new_'):
        await call.answer()
        return
    term_code = call.data.split(':', 1)[1]
    message_id = _progress_message_id(user_id, call.message.message_id)
    TgConfig.STATE[f'{user_id}_quest_new_task'] = {'term': term_code, 'titles': {}}
    TgConfig.STATE[f'{user_id}_quest_new_index'] = 0
    TgConfig.STATE[user_id] = 'quest_task_new_count'
    TgConfig.STATE.pop(f'{user_id}_terms_back', None)
    TgConfig.STATE.pop(f'{user_id}_quest_term_target', None)
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton(t(lang, 'back'), callback_data='quest_tasks'))
    await call.answer()
    await safe_edit_message_text(
        bot,
        t(lang, 'tools_quest_task_count_prompt', term=term_code),
        chat_id=call.message.chat.id,
        message_id=message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


async def quest_task_receive_count(message: Message):
    bot, user_id = await get_bot_user_ids(message)
    if TgConfig.STATE.get(user_id) != 'quest_task_new_count':
        return
    lang = get_user_language(user_id) or 'en'
    data = TgConfig.STATE.get(f'{user_id}_quest_new_task', {})
    term = data.get('term')
    try:
        count = int((message.text or '').strip())
    except (TypeError, ValueError):
        await message.answer(t(lang, 'invalid_number'))
        return
    if count <= 0:
        await message.answer(t(lang, 'invalid_number'))
        return
    data['count'] = count
    TgConfig.STATE[f'{user_id}_quest_new_task'] = data
    TgConfig.STATE[user_id] = 'quest_task_new_title'
    TgConfig.STATE[f'{user_id}_quest_new_index'] = 0
    message_id = _progress_message_id(user_id, message.message_id)
    with contextlib.suppress(Exception):
        await message.delete()
    await _prompt_new_task_title(bot, message.chat.id, message_id, user_id, lang)


async def _prompt_new_task_title(bot, chat_id: int, message_id: int, user_id: int, lang: str) -> None:
    index = TgConfig.STATE.get(f'{user_id}_quest_new_index', 0)
    data = TgConfig.STATE.get(f'{user_id}_quest_new_task', {})
    if index >= len(_TERM_LANGUAGES):
        term = data.get('term')
        count = data.get('count', 1)
        titles = data.get('titles', {})
        add_weekly_quest_task(term, count, titles)
        TgConfig.STATE.pop(f'{user_id}_quest_new_task', None)
        TgConfig.STATE.pop(f'{user_id}_quest_new_index', None)
        TgConfig.STATE[user_id] = None
        await _render_quest_tasks_menu(bot, chat_id, message_id, lang, t(lang, 'tools_quest_task_added', term=term))
        return
    language = _TERM_LANGUAGES[index]
    TgConfig.STATE[user_id] = 'quest_task_new_title'
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton(t(lang, 'back'), callback_data='quest_tasks'))
    await safe_edit_message_text(
        bot,
        t(lang, 'tools_quest_task_title_prompt', language=_language_label(lang, language)),
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


async def quest_task_receive_title(message: Message):
    bot, user_id = await get_bot_user_ids(message)
    if TgConfig.STATE.get(user_id) != 'quest_task_new_title':
        return
    lang = get_user_language(user_id) or 'en'
    index = TgConfig.STATE.get(f'{user_id}_quest_new_index', 0)
    data = TgConfig.STATE.get(f'{user_id}_quest_new_task', {'titles': {}})
    language = _TERM_LANGUAGES[index]
    titles = data.get('titles', {})
    titles[language] = (message.text or '').strip()
    data['titles'] = titles
    TgConfig.STATE[f'{user_id}_quest_new_task'] = data
    TgConfig.STATE[f'{user_id}_quest_new_index'] = index + 1
    message_id = _progress_message_id(user_id, message.message_id)
    with contextlib.suppress(Exception):
        await message.delete()
    await _prompt_new_task_title(bot, message.chat.id, message_id, user_id, lang)


async def quest_task_term_edit_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.SHOP_MANAGE):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    task_id = call.data[len('quest_task_term_'):]
    message_id = _progress_message_id(user_id, call.message.message_id)
    TgConfig.STATE[user_id] = f'quest_task_edit_term:{task_id}'
    await call.answer()
    await _render_task_term_selection(bot, call.message.chat.id, message_id, lang, user_id, f'edit:{task_id}')


async def quest_task_term_prompt_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    state = str(TgConfig.STATE.get(user_id) or '')
    lang = get_user_language(user_id) or 'en'
    message_id = _progress_message_id(user_id, call.message.message_id)
    target = TgConfig.STATE.get(f'{user_id}_quest_term_target') or 'new'
    if state.startswith('quest_task_edit_term:'):
        target = f"edit:{state.split(':', 1)[1]}"
    elif state.startswith('quest_task_new_'):
        target = 'new'
    if target.startswith('edit:') or target == 'new':
        await call.answer()
        await _render_task_term_selection(bot, call.message.chat.id, message_id, lang, user_id, target)
        return
    await call.answer()
    await _render_quest_tasks_menu(
        bot,
        call.message.chat.id,
        message_id,
        lang,
        t(lang, 'tools_quest_invalid_state'),
    )


async def quest_task_termselect_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    state = str(TgConfig.STATE.get(user_id) or '')
    if not state.startswith('quest_task_edit_term:'):
        await call.answer()
        return
    _, task_id = state.split(':', 1)
    _, payload = call.data.split(':', 1)
    term_code = payload.split(':', 1)[1]
    lang = get_user_language(user_id) or 'en'
    message_id = _progress_message_id(user_id, call.message.message_id)
    update_weekly_quest_task(task_id, term=term_code)
    TgConfig.STATE[user_id] = None
    TgConfig.STATE.pop(f'{user_id}_quest_term_target', None)
    TgConfig.STATE.pop(f'{user_id}_terms_back', None)
    await call.answer(t(lang, 'settings_saved'))
    await _render_quest_task_detail(
        bot,
        call.message.chat.id,
        message_id,
        lang,
        task_id,
        notice=t(lang, 'tools_quest_task_term_saved', term=term_code),
    )


async def quest_task_count_edit_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.SHOP_MANAGE):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    task_id = call.data[len('quest_task_count_'):]
    message_id = _progress_message_id(user_id, call.message.message_id)
    TgConfig.STATE[user_id] = f'quest_task_edit_count:{task_id}'
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton(t(lang, 'back'), callback_data=f'quest_task_view_{task_id}'))
    await call.answer()
    await safe_edit_message_text(
        bot,
        t(lang, 'tools_quest_task_count_edit_prompt'),
        chat_id=call.message.chat.id,
        message_id=message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


async def quest_task_receive_edit_count(message: Message):
    bot, user_id = await get_bot_user_ids(message)
    state = str(TgConfig.STATE.get(user_id) or '')
    if not state.startswith('quest_task_edit_count:'):
        return
    _, task_id = state.split(':', 1)
    lang = get_user_language(user_id) or 'en'
    try:
        count = int((message.text or '').strip())
    except (TypeError, ValueError):
        await message.answer(t(lang, 'invalid_number'))
        return
    if count <= 0:
        await message.answer(t(lang, 'invalid_number'))
        return
    update_weekly_quest_task(task_id, count=count)
    TgConfig.STATE[user_id] = None
    with contextlib.suppress(Exception):
        await message.delete()
    message_id = _progress_message_id(user_id, message.message_id)
    await _render_quest_task_detail(
        bot,
        message.chat.id,
        message_id,
        lang,
        task_id,
        notice=t(lang, 'tools_quest_task_count_saved', count=count),
    )


async def quest_task_titles_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.SHOP_MANAGE):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    task_id = call.data[len('quest_task_titles_'):]
    message_id = _progress_message_id(user_id, call.message.message_id)
    lines = [t(lang, 'tools_quest_task_titles_prompt')]
    markup = InlineKeyboardMarkup(row_width=2)
    for language in _TERM_LANGUAGES:
        markup.insert(
            InlineKeyboardButton(
                _language_label(lang, language),
                callback_data=f'quest_task_title_{task_id}_{language}',
            )
        )
    markup.add(InlineKeyboardButton(t(lang, 'back'), callback_data=f'quest_task_view_{task_id}'))
    await call.answer()
    await safe_edit_message_text(
        bot,
        '\n'.join(lines),
        chat_id=call.message.chat.id,
        message_id=message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


async def quest_task_title_language_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.SHOP_MANAGE):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    _, task_id, language = call.data.split('_', 3)[1:4]
    quest = get_weekly_quest()
    tasks = quest.get('tasks', []) or []
    task = next((entry for entry in tasks if entry.get('id') == task_id), None)
    titles = (task or {}).get('titles', {}) or {}
    existing = str(titles.get(language, '')).strip()
    message_id = _progress_message_id(user_id, call.message.message_id)
    TgConfig.STATE[user_id] = f'quest_task_edit_title:{task_id}:{language}'
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton(t(lang, 'back'), callback_data=f'quest_task_titles_{task_id}'))
    prompt = t(
        lang,
        'tools_quest_task_title_edit_prompt',
        language=_language_label(lang, language),
        current=existing,
    )
    await call.answer()
    await safe_edit_message_text(
        bot,
        prompt,
        chat_id=call.message.chat.id,
        message_id=message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


async def quest_task_receive_edit_title(message: Message):
    bot, user_id = await get_bot_user_ids(message)
    state = str(TgConfig.STATE.get(user_id) or '')
    if not state.startswith('quest_task_edit_title:'):
        return
    _, task_id, language = state.split(':', 2)
    lang = get_user_language(user_id) or 'en'
    text = (message.text or '').strip()
    update_weekly_quest_task(task_id, titles={language: text})
    TgConfig.STATE[user_id] = None
    with contextlib.suppress(Exception):
        await message.delete()
    message_id = _progress_message_id(user_id, message.message_id)
    await _render_quest_task_detail(
        bot,
        message.chat.id,
        message_id,
        lang,
        task_id,
        notice=t(lang, 'tools_quest_task_title_saved', language=_language_label(lang, language)),
    )


async def quest_task_delete_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.SHOP_MANAGE):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    task_id = call.data[len('quest_task_delete_'):]
    message_id = _progress_message_id(user_id, call.message.message_id)
    deleted = delete_weekly_quest_task(task_id)
    await call.answer(t(lang, 'settings_saved'))
    if not deleted:
        await _render_quest_task_detail(
            bot,
            call.message.chat.id,
            message_id,
            lang,
            task_id,
            notice=t(lang, 'tools_quest_task_missing'),
        )
        return
    await _render_quest_tasks_menu(
        bot,
        call.message.chat.id,
        message_id,
        lang,
        t(lang, 'tools_quest_task_deleted'),
    )


async def _render_achievements_menu(bot, chat_id: int, message_id: int, lang: str, notice: str | None = None) -> None:
    achievements = list_achievements()
    lines = [t(lang, 'tools_achievements_heading')]
    if notice:
        lines.extend(['', notice])
    if achievements:
        for entry in achievements:
            code = entry.get('code')
            config = entry.get('config', {})
            ach_type = config.get('type', 'builtin')
            if ach_type == 'term_purchase':
                lines.append(
                    t(
                        lang,
                        'tools_achievement_entry_term',
                        code=code,
                        term=config.get('term', '—'),
                        target=config.get('target', 0),
                    )
                )
            else:
                lines.append(t(lang, 'tools_achievement_entry_builtin', code=code))
    else:
        lines.append(t(lang, 'tools_achievements_empty'))
    markup = InlineKeyboardMarkup(row_width=1)
    for entry in achievements:
        code = entry.get('code')
        markup.add(InlineKeyboardButton(f"#{code}", callback_data=f'achievement_view_{code}'))
    markup.add(InlineKeyboardButton(t(lang, 'tools_achievement_create'), callback_data='achievement_create'))
    markup.add(InlineKeyboardButton(t(lang, 'back'), callback_data='tools_cat_progress'))
    await safe_edit_message_text(
        bot,
        '\n'.join(lines),
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


async def tools_progress_achievements_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.SHOP_MANAGE):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    message_id = _progress_message_id(user_id, call.message.message_id)
    TgConfig.STATE[user_id] = None
    await call.answer()
    await _render_achievements_menu(bot, call.message.chat.id, message_id, lang)


async def _render_achievement_detail(bot, chat_id: int, message_id: int, lang: str, code: str, notice: str | None = None) -> None:
    entry = get_achievement(code)
    if entry is None:
        await _render_achievements_menu(bot, chat_id, message_id, lang, t(lang, 'tools_achievement_missing'))
        return
    config = entry.get('config', {})
    ach_type = config.get('type', 'builtin')
    lines = [t(lang, 'tools_achievement_header', code=code)]
    if notice:
        lines.extend(['', notice])
    if ach_type == 'term_purchase':
        lines.append(t(lang, 'tools_achievement_type_term'))
        lines.append(t(lang, 'tools_achievement_term_line', term=config.get('term', '—')))
        lines.append(t(lang, 'tools_achievement_target_line', target=config.get('target', 0)))
    else:
        lines.append(t(lang, 'tools_achievement_type_builtin'))
    titles = config.get('titles', {}) or {}
    lines.append('')
    lines.append(t(lang, 'tools_achievement_titles_header'))
    for language in _TERM_LANGUAGES:
        lines.append(
            t(
                lang,
                'tools_achievement_title_line',
                language=_language_label(lang, language),
                title=html.escape(str(titles.get(language, '')).strip()),
            )
        )
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton(t(lang, 'tools_achievement_edit_titles'), callback_data=f'achievement_titles_{code}'))
    if config.get('type') == 'term_purchase':
        markup.row(
            InlineKeyboardButton(t(lang, 'tools_achievement_edit_term'), callback_data=f'achievement_term_{code}'),
            InlineKeyboardButton(t(lang, 'tools_achievement_edit_target'), callback_data=f'achievement_target_{code}'),
        )
    is_custom = code not in DEFAULT_ACHIEVEMENTS
    if is_custom:
        markup.add(InlineKeyboardButton(t(lang, 'tools_achievement_delete'), callback_data=f'achievement_delete_{code}'))
    markup.add(InlineKeyboardButton(t(lang, 'back'), callback_data='tools_progress_achievements'))
    await safe_edit_message_text(
        bot,
        '\n'.join(lines),
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


async def achievement_view_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.SHOP_MANAGE):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    code = call.data[len('achievement_view_'):]
    message_id = _progress_message_id(user_id, call.message.message_id)
    await call.answer()
    await _render_achievement_detail(bot, call.message.chat.id, message_id, lang, code)


async def achievement_titles_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.SHOP_MANAGE):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    code = call.data[len('achievement_titles_'):]
    message_id = _progress_message_id(user_id, call.message.message_id)
    lines = [t(lang, 'tools_achievement_titles_prompt', code=code)]
    markup = InlineKeyboardMarkup(row_width=2)
    for language in _TERM_LANGUAGES:
        markup.insert(
            InlineKeyboardButton(
                _language_label(lang, language),
                callback_data=f'achievement_title_{code}_{language}',
            )
        )
    markup.add(InlineKeyboardButton(t(lang, 'back'), callback_data=f'achievement_view_{code}'))
    await call.answer()
    await safe_edit_message_text(
        bot,
        '\n'.join(lines),
        chat_id=call.message.chat.id,
        message_id=message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


async def achievement_title_language_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.SHOP_MANAGE):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    _, code, language = call.data.split('_', 2)
    entry = get_achievement(code) or {'config': {}}
    titles = (entry.get('config') or {}).get('titles', {}) or {}
    existing = str(titles.get(language, '')).strip()
    message_id = _progress_message_id(user_id, call.message.message_id)
    TgConfig.STATE[user_id] = f'achievement_edit_title:{code}:{language}'
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton(t(lang, 'back'), callback_data=f'achievement_titles_{code}'))
    prompt = t(
        lang,
        'tools_achievement_title_prompt',
        language=_language_label(lang, language),
        current=existing,
    )
    await call.answer()
    await safe_edit_message_text(
        bot,
        prompt,
        chat_id=call.message.chat.id,
        message_id=message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


async def achievement_receive_title(message: Message):
    bot, user_id = await get_bot_user_ids(message)
    state = str(TgConfig.STATE.get(user_id) or '')
    if not state.startswith('achievement_edit_title:'):
        return
    _, code, language = state.split(':', 2)
    lang = get_user_language(user_id) or 'en'
    text_value = (message.text or '').strip()
    set_achievement_titles(code, {language: text_value})
    TgConfig.STATE[user_id] = None
    with contextlib.suppress(Exception):
        await message.delete()
    message_id = _progress_message_id(user_id, message.message_id)
    notice = t(lang, 'tools_achievement_title_saved', language=_language_label(lang, language))
    await _render_achievement_detail(bot, message.chat.id, message_id, lang, code, notice)


async def _render_achievement_term_selection(
    bot,
    chat_id: int,
    message_id: int,
    lang: str,
    code: str,
    *,
    creation: bool = False,
    notice: str | None = None,
) -> None:
    terms = list_terms()
    lines = [t(lang, 'tools_achievement_term_prompt', code=code)]
    if notice:
        lines.extend(['', notice])
    if not terms:
        lines.append('')
        lines.append(t(lang, 'tools_achievement_no_terms'))
    markup = InlineKeyboardMarkup(row_width=2)
    if terms:
        for term in terms:
            term_code = term.get('code')
            prefix = 'achievement_new_termselect' if creation else 'achievement_termselect'
            markup.insert(InlineKeyboardButton(term_code, callback_data=f'{prefix}:{code}:{term_code}'))
    markup.add(InlineKeyboardButton(t(lang, 'tools_quest_terms_manage'), callback_data='tools_progress_terms'))
    back_target = 'achievement_create' if creation else f'achievement_view_{code}'
    markup.add(InlineKeyboardButton(t(lang, 'back'), callback_data=back_target))
    await safe_edit_message_text(
        bot,
        '\n'.join(lines),
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


async def achievement_term_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.SHOP_MANAGE):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    code = call.data[len('achievement_term_'):]
    message_id = _progress_message_id(user_id, call.message.message_id)
    TgConfig.STATE[user_id] = f'achievement_term:{code}'
    await call.answer()
    await _render_achievement_term_selection(bot, call.message.chat.id, message_id, lang, code)


async def achievement_term_select_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    state = str(TgConfig.STATE.get(user_id) or '')
    if not state.startswith('achievement_term:'):
        await call.answer()
        return
    _, code = state.split(':', 1)
    _, payload = call.data.split(':', 1)
    term_code = payload.split(':', 1)[1]
    lang = get_user_language(user_id) or 'en'
    message_id = _progress_message_id(user_id, call.message.message_id)
    try:
        configure_term_achievement(code, term_code, get_achievement(code)['config'].get('target', 1))
    except ValueError:
        await call.answer(t(lang, 'tools_achievement_term_invalid'), show_alert=True)
        return
    TgConfig.STATE[user_id] = None
    await call.answer(t(lang, 'settings_saved'))
    notice = t(lang, 'tools_achievement_term_saved', term=term_code)
    await _render_achievement_detail(bot, call.message.chat.id, message_id, lang, code, notice)


async def achievement_set_target_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.SHOP_MANAGE):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    code = call.data[len('achievement_target_'):]
    message_id = _progress_message_id(user_id, call.message.message_id)
    TgConfig.STATE[user_id] = f'achievement_target:{code}'
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton(t(lang, 'back'), callback_data=f'achievement_view_{code}'))
    await call.answer()
    await safe_edit_message_text(
        bot,
        t(lang, 'tools_achievement_target_prompt'),
        chat_id=call.message.chat.id,
        message_id=message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


async def achievement_receive_target(message: Message):
    bot, user_id = await get_bot_user_ids(message)
    state = str(TgConfig.STATE.get(user_id) or '')
    if not state.startswith('achievement_target:'):
        return
    _, code = state.split(':', 1)
    lang = get_user_language(user_id) or 'en'
    try:
        target = int((message.text or '').strip())
    except (TypeError, ValueError):
        await message.answer(t(lang, 'invalid_number'))
        return
    if target <= 0:
        await message.answer(t(lang, 'invalid_number'))
        return
    achievement = get_achievement(code)
    if achievement is None:
        await message.answer(t(lang, 'tools_achievement_missing'))
        return
    config = achievement.get('config', {})
    try:
        configure_term_achievement(code, config.get('term', ''), target)
    except ValueError:
        await message.answer(t(lang, 'tools_achievement_term_required'))
        return
    TgConfig.STATE[user_id] = None
    with contextlib.suppress(Exception):
        await message.delete()
    message_id = _progress_message_id(user_id, message.message_id)
    notice = t(lang, 'tools_achievement_target_saved', target=target)
    await _render_achievement_detail(bot, message.chat.id, message_id, lang, code, notice)


async def achievement_delete_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.SHOP_MANAGE):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    code = call.data[len('achievement_delete_'):]
    message_id = _progress_message_id(user_id, call.message.message_id)
    try:
        delete_custom_achievement(code)
    except ValueError:
        await call.answer(t(lang, 'tools_achievement_delete_denied'), show_alert=True)
        return
    await call.answer(t(lang, 'settings_saved'))
    await _render_achievements_menu(bot, call.message.chat.id, message_id, lang, t(lang, 'tools_achievement_deleted', code=code))


async def achievement_create_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    lang = get_user_language(user_id) or 'en'
    if not (role & Permission.SHOP_MANAGE):
        await call.answer(t(lang, 'insufficient_rights'))
        return
    message_id = _progress_message_id(user_id, call.message.message_id)
    TgConfig.STATE[user_id] = 'achievement_create_code'
    TgConfig.STATE.pop(f'{user_id}_achievement_new', None)
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton(t(lang, 'back'), callback_data='tools_progress_achievements'))
    await call.answer()
    await safe_edit_message_text(
        bot,
        t(lang, 'tools_achievement_create_prompt'),
        chat_id=call.message.chat.id,
        message_id=message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


async def achievement_create_receive_code(message: Message):
    bot, user_id = await get_bot_user_ids(message)
    if TgConfig.STATE.get(user_id) != 'achievement_create_code':
        return
    lang = get_user_language(user_id) or 'en'
    code_raw = (message.text or '').strip().lower()
    safe_code = re.sub(r'[^a-z0-9_]+', '_', code_raw).strip('_')
    if not safe_code:
        await message.answer(t(lang, 'tools_achievement_code_invalid'))
        return
    if get_achievement(safe_code):
        await message.answer(t(lang, 'tools_achievement_code_exists'))
        return
    TgConfig.STATE[f'{user_id}_achievement_new'] = {'code': safe_code, 'titles': {}}
    TgConfig.STATE[user_id] = 'achievement_create_term'
    message_id = _progress_message_id(user_id, message.message_id)
    with contextlib.suppress(Exception):
        await message.delete()
    await _render_achievement_term_selection(bot, message.chat.id, message_id, lang, safe_code, creation=True)


async def achievement_create_term_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    if TgConfig.STATE.get(user_id) != 'achievement_create_term':
        await call.answer()
        return
    lang = get_user_language(user_id) or 'en'
    data = TgConfig.STATE.get(f'{user_id}_achievement_new', {})
    code = data.get('code', '')
    message_id = _progress_message_id(user_id, call.message.message_id)
    await call.answer()
    await _render_achievement_term_selection(bot, call.message.chat.id, message_id, lang, code, creation=True)


async def achievement_create_term_select_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    if TgConfig.STATE.get(user_id) != 'achievement_create_term':
        await call.answer()
        return
    _, code, term_code = call.data.split(':', 2)
    data = TgConfig.STATE.get(f'{user_id}_achievement_new', {})
    data['code'] = code
    data['term'] = term_code
    TgConfig.STATE[f'{user_id}_achievement_new'] = data
    TgConfig.STATE[user_id] = 'achievement_create_target'
    lang = get_user_language(user_id) or 'en'
    message_id = _progress_message_id(user_id, call.message.message_id)
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton(t(lang, 'back'), callback_data='achievement_create_term'))
    await call.answer()
    await safe_edit_message_text(
        bot,
        t(lang, 'tools_achievement_target_prompt'),
        chat_id=call.message.chat.id,
        message_id=message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


async def achievement_create_receive_target(message: Message):
    bot, user_id = await get_bot_user_ids(message)
    if TgConfig.STATE.get(user_id) != 'achievement_create_target':
        return
    lang = get_user_language(user_id) or 'en'
    try:
        target = int((message.text or '').strip())
    except (TypeError, ValueError):
        await message.answer(t(lang, 'invalid_number'))
        return
    if target <= 0:
        await message.answer(t(lang, 'invalid_number'))
        return
    data = TgConfig.STATE.get(f'{user_id}_achievement_new', {})
    data['target'] = target
    data['titles'] = {}
    TgConfig.STATE[f'{user_id}_achievement_new'] = data
    TgConfig.STATE[user_id] = 'achievement_create_title'
    TgConfig.STATE[f'{user_id}_achievement_index'] = 0
    message_id = _progress_message_id(user_id, message.message_id)
    with contextlib.suppress(Exception):
        await message.delete()
    await _prompt_new_achievement_title(bot, message.chat.id, message_id, user_id, lang)


async def _prompt_new_achievement_title(bot, chat_id: int, message_id: int, user_id: int, lang: str) -> None:
    index = TgConfig.STATE.get(f'{user_id}_achievement_index', 0)
    data = TgConfig.STATE.get(f'{user_id}_achievement_new', {})
    if index >= len(_TERM_LANGUAGES):
        code = data.get('code')
        term = data.get('term')
        target = data.get('target', 1)
        titles = data.get('titles', {})
        create_custom_achievement(code, titles, term, target)
        TgConfig.STATE.pop(f'{user_id}_achievement_new', None)
        TgConfig.STATE.pop(f'{user_id}_achievement_index', None)
        TgConfig.STATE[user_id] = None
        await _render_achievements_menu(bot, chat_id, message_id, lang, t(lang, 'tools_achievement_created', code=code))
        return
    language = _TERM_LANGUAGES[index]
    TgConfig.STATE[user_id] = 'achievement_create_title'
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton(t(lang, 'back'), callback_data='tools_progress_achievements'))
    await safe_edit_message_text(
        bot,
        t(lang, 'tools_achievement_title_prompt', language=_language_label(lang, language), current=''),
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


async def achievement_create_receive_title(message: Message):
    bot, user_id = await get_bot_user_ids(message)
    if TgConfig.STATE.get(user_id) != 'achievement_create_title':
        return
    lang = get_user_language(user_id) or 'en'
    index = TgConfig.STATE.get(f'{user_id}_achievement_index', 0)
    language = _TERM_LANGUAGES[index]
    data = TgConfig.STATE.get(f'{user_id}_achievement_new', {'titles': {}})
    titles = data.get('titles', {})
    titles[language] = (message.text or '').strip()
    data['titles'] = titles
    TgConfig.STATE[f'{user_id}_achievement_new'] = data
    TgConfig.STATE[f'{user_id}_achievement_index'] = index + 1
    message_id = _progress_message_id(user_id, message.message_id)
    with contextlib.suppress(Exception):
        await message.delete()
    await _prompt_new_achievement_title(bot, message.chat.id, message_id, user_id, lang)


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
    dp.register_callback_query_handler(tools_progress_handler, lambda c: c.data == 'tools_cat_progress', state='*')
    dp.register_callback_query_handler(
        tools_profile_handler,
        lambda c: c.data in ('tools_cat_profile', 'profile_blackjack_settings'),
        state='*',
    )
    dp.register_callback_query_handler(tools_progress_quest_handler, lambda c: c.data == 'tools_progress_quest', state='*')
    dp.register_callback_query_handler(tools_progress_achievements_handler, lambda c: c.data == 'tools_progress_achievements', state='*')
    dp.register_callback_query_handler(tools_team_handler, lambda c: c.data == 'tools_cat_team', state='*')
    dp.register_callback_query_handler(tools_sales_handler, lambda c: c.data == 'tools_cat_sales', state='*')
    dp.register_callback_query_handler(tools_broadcast_handler, lambda c: c.data == 'tools_cat_broadcast', state='*')
    dp.register_callback_query_handler(tools_terms_handler, lambda c: c.data == 'tools_progress_terms', state='*')
    dp.register_callback_query_handler(tools_term_detail_handler, lambda c: c.data.startswith('term_view_'), state='*')
    dp.register_callback_query_handler(tools_term_add_handler, lambda c: c.data == 'term_add', state='*')
    dp.register_callback_query_handler(tools_term_edit_label_handler, lambda c: c.data.startswith('term_edit_'), state='*')
    dp.register_callback_query_handler(tools_term_delete_handler, lambda c: c.data.startswith('term_delete_'), state='*')
    dp.register_message_handler(terms_receive_code, lambda m: TgConfig.STATE.get(m.from_user.id) == 'terms:create_code', state='*')
    dp.register_message_handler(terms_receive_label, lambda m: TgConfig.STATE.get(m.from_user.id) == 'terms:create_label', state='*')
    dp.register_message_handler(terms_receive_edit_label, lambda m: TgConfig.STATE.get(m.from_user.id) == 'terms:edit_label', state='*')
    dp.register_callback_query_handler(profile_toggle_handler, lambda c: c.data.startswith('profile_toggle:'), state='*')
    dp.register_callback_query_handler(profile_blackjack_max_bet_prompt, lambda c: c.data == 'profile_blackjack_max_bet', state='*')
    dp.register_callback_query_handler(profile_edit_quests_prompt, lambda c: c.data == 'profile_edit_quests', state='*')
    dp.register_callback_query_handler(profile_edit_missions_prompt, lambda c: c.data == 'profile_edit_missions', state='*')
    dp.register_message_handler(
        profile_settings_receive_input,
        lambda m: str(TgConfig.STATE.get(m.from_user.id, '')).startswith('profile_settings:'),
        state='*',
    )
    dp.register_callback_query_handler(quest_titles_handler, lambda c: c.data == 'quest_titles', state='*')
    dp.register_callback_query_handler(quest_titles_language_handler, lambda c: c.data.startswith('quest_titles_lang_'), state='*')
    dp.register_message_handler(quest_titles_receive, lambda m: str(TgConfig.STATE.get(m.from_user.id, '')).startswith('quest_titles:'), state='*')
    dp.register_callback_query_handler(quest_reset_handler, lambda c: c.data == 'quest_reset', state='*')
    dp.register_message_handler(quest_reset_receive, lambda m: TgConfig.STATE.get(m.from_user.id) == 'quest_reset', state='*')
    dp.register_callback_query_handler(quest_reward_handler, lambda c: c.data == 'quest_reward', state='*')
    dp.register_callback_query_handler(quest_reward_set_discount_handler, lambda c: c.data == 'quest_reward_type_discount', state='*')
    dp.register_callback_query_handler(quest_reward_set_stock_handler, lambda c: c.data == 'quest_reward_type_stock', state='*')
    dp.register_callback_query_handler(quest_reward_titles_handler, lambda c: c.data == 'quest_reward_titles', state='*')
    dp.register_callback_query_handler(quest_reward_title_language_handler, lambda c: c.data.startswith('quest_reward_title_'), state='*')
    dp.register_message_handler(quest_reward_receive_input, lambda m: str(TgConfig.STATE.get(m.from_user.id, '')).startswith('quest_reward:'), state='*')
    dp.register_message_handler(quest_reward_receive_title, lambda m: str(TgConfig.STATE.get(m.from_user.id, '')).startswith('quest_reward_title:'), state='*')
    dp.register_callback_query_handler(tools_quest_tasks_handler, lambda c: c.data == 'quest_tasks', state='*')
    dp.register_callback_query_handler(quest_task_view_handler, lambda c: c.data.startswith('quest_task_view_'), state='*')
    dp.register_callback_query_handler(quest_task_add_handler, lambda c: c.data == 'quest_task_add', state='*')
    dp.register_callback_query_handler(quest_task_select_term_handler, lambda c: c.data.startswith('quest_task_new_term:'), state='*')
    dp.register_callback_query_handler(quest_task_term_edit_handler, lambda c: c.data.startswith('quest_task_term_'), state='*')
    dp.register_callback_query_handler(quest_task_term_prompt_handler, lambda c: c.data == 'quest_task_term_prompt', state='*')
    dp.register_callback_query_handler(quest_task_termselect_handler, lambda c: c.data.startswith('quest_task_termselect:'), state='*')
    dp.register_callback_query_handler(quest_task_count_edit_handler, lambda c: c.data.startswith('quest_task_count_'), state='*')
    dp.register_callback_query_handler(quest_task_titles_handler, lambda c: c.data.startswith('quest_task_titles_'), state='*')
    dp.register_callback_query_handler(quest_task_title_language_handler, lambda c: c.data.startswith('quest_task_title_'), state='*')
    dp.register_callback_query_handler(quest_task_delete_handler, lambda c: c.data.startswith('quest_task_delete_'), state='*')
    dp.register_message_handler(quest_task_receive_count, lambda m: TgConfig.STATE.get(m.from_user.id) == 'quest_task_new_count', state='*')
    dp.register_message_handler(quest_task_receive_title, lambda m: TgConfig.STATE.get(m.from_user.id) == 'quest_task_new_title', state='*')
    dp.register_message_handler(quest_task_receive_edit_count, lambda m: str(TgConfig.STATE.get(m.from_user.id, '')).startswith('quest_task_edit_count:'), state='*')
    dp.register_message_handler(quest_task_receive_edit_title, lambda m: str(TgConfig.STATE.get(m.from_user.id, '')).startswith('quest_task_edit_title:'), state='*')
    dp.register_callback_query_handler(achievement_view_handler, lambda c: c.data.startswith('achievement_view_'), state='*')
    dp.register_callback_query_handler(achievement_titles_handler, lambda c: c.data.startswith('achievement_titles_'), state='*')
    dp.register_callback_query_handler(achievement_title_language_handler, lambda c: c.data.startswith('achievement_title_'), state='*')
    dp.register_message_handler(achievement_receive_title, lambda m: str(TgConfig.STATE.get(m.from_user.id, '')).startswith('achievement_edit_title:'), state='*')
    dp.register_callback_query_handler(achievement_term_handler, lambda c: c.data.startswith('achievement_term_'), state='*')
    dp.register_callback_query_handler(achievement_term_select_handler, lambda c: c.data.startswith('achievement_termselect:'), state='*')
    dp.register_callback_query_handler(achievement_set_target_handler, lambda c: c.data.startswith('achievement_target_'), state='*')
    dp.register_message_handler(achievement_receive_target, lambda m: str(TgConfig.STATE.get(m.from_user.id, '')).startswith('achievement_target:'), state='*')
    dp.register_callback_query_handler(achievement_delete_handler, lambda c: c.data.startswith('achievement_delete_'), state='*')
    dp.register_callback_query_handler(achievement_create_handler, lambda c: c.data == 'achievement_create', state='*')
    dp.register_message_handler(achievement_create_receive_code, lambda m: TgConfig.STATE.get(m.from_user.id) == 'achievement_create_code', state='*')
    dp.register_callback_query_handler(achievement_create_term_handler, lambda c: c.data == 'achievement_create_term', state='*')
    dp.register_callback_query_handler(achievement_create_term_select_handler, lambda c: c.data.startswith('achievement_new_termselect:'), state='*')
    dp.register_message_handler(achievement_create_receive_target, lambda m: TgConfig.STATE.get(m.from_user.id) == 'achievement_create_target', state='*')
    dp.register_message_handler(achievement_create_receive_title, lambda m: TgConfig.STATE.get(m.from_user.id) == 'achievement_create_title', state='*')
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
