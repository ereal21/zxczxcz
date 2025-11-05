from aiogram import Dispatcher
from aiogram.types import CallbackQuery

from bot.keyboards import console, back, information_menu, admin_language_menu
from bot.database.methods import check_role, get_user_language, update_user_language
from bot.database.models import Permission
from bot.localization import t
from bot.misc import TgConfig
from bot.utils.statistics import collect_shop_statistics, format_admin_statistics
from bot.utils import safe_edit_message_text

from bot.handlers.admin.broadcast import register_mailing
from bot.handlers.admin.shop_management_states import register_shop_management
from bot.handlers.admin.user_management_states import register_user_management
from bot.handlers.admin.assistant_management_states import register_assistant_management
from bot.handlers.admin.owner_management_states import register_owner_management
from bot.handlers.admin.view_stock import register_view_stock
from bot.handlers.admin.purchases import register_purchases
from bot.handlers.admin.miscs import register_miscs
from bot.handlers.admin.passwords import register_passwords
from bot.handlers.admin.reseller_management_states import register_reseller_management
from bot.handlers.other import get_bot_user_ids


LANGUAGE_PROMPTS = {
    'lt': '🌐 Pasirinkite administravimo kalbą:',
    'en': '🌐 Choose the admin panel language:',
    'ru': '🌐 Выберите язык панели администратора:',
}

LANGUAGE_UPDATED = {
    'lt': '✅ Kalba atnaujinta!',
    'en': '✅ Language updated!',
    'ru': '✅ Язык обновлён!',
}


async def _render_console(bot, chat_id: int, message_id: int, role: int, lang: str) -> None:
    stats = collect_shop_statistics()
    text = format_admin_statistics(stats, lang)
    await safe_edit_message_text(bot, 
        text,
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=console(role),
        parse_mode='HTML',
    )


async def console_callback_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    TgConfig.STATE[user_id] = None
    role = check_role(user_id)
    if role != Permission.USE:
        lang = get_user_language(user_id) or 'en'
        await _render_console(
            bot,
            call.message.chat.id,
            call.message.message_id,
            role,
            lang,
        )
        return
    await call.answer('Nepakanka teisių')


async def admin_help_callback_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    TgConfig.STATE[user_id] = None
    role = check_role(user_id)
    user_lang = get_user_language(user_id) or 'en'
    assistant_role = Permission.USE | Permission.ASSIGN_PHOTOS
    key = 'assistant_help_info' if role == assistant_role else 'admin_help_info'
    text = t(user_lang, key)
    await safe_edit_message_text(bot, text,
                                chat_id=call.message.chat.id,
                                message_id=call.message.message_id,
                                reply_markup=back('console'))


async def information_callback_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    TgConfig.STATE[user_id] = None
    role = check_role(user_id)
    if role != Permission.USE:
        await safe_edit_message_text(bot, 'ℹ️ Informacijos meniu',
                                    chat_id=call.message.chat.id,
                                    message_id=call.message.message_id,
                                    reply_markup=information_menu(role))
        return
    await call.answer('Nepakanka teisių')


async def admin_language_callback_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    TgConfig.STATE[user_id] = None
    role = check_role(user_id)
    if role == Permission.USE:
        await call.answer('Nepakanka teisių')
        return
    current_lang = get_user_language(user_id) or 'en'
    prompt = LANGUAGE_PROMPTS.get(current_lang, LANGUAGE_PROMPTS['en'])
    await safe_edit_message_text(bot, 
        prompt,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=admin_language_menu(current_lang),
    )


async def admin_set_language_handler(call: CallbackQuery):
    bot, user_id = await get_bot_user_ids(call)
    role = check_role(user_id)
    if role == Permission.USE:
        await call.answer('Nepakanka teisių')
        return
    lang_code = call.data.split('_')[-1]
    update_user_language(user_id, lang_code)
    confirmation = LANGUAGE_UPDATED.get(lang_code, LANGUAGE_UPDATED['en'])
    await call.answer(confirmation, show_alert=True)
    await _render_console(
        bot,
        call.message.chat.id,
        call.message.message_id,
        role,
        lang_code,
    )


def register_admin_handlers(dp: Dispatcher) -> None:
    dp.register_callback_query_handler(console_callback_handler,
                                       lambda c: c.data == 'console',
                                       state='*')
    dp.register_callback_query_handler(admin_help_callback_handler,
                                       lambda c: c.data == 'admin_help',
                                       state='*')
    dp.register_callback_query_handler(information_callback_handler,
                                       lambda c: c.data == 'information',
                                       state='*')
    dp.register_callback_query_handler(admin_language_callback_handler,
                                       lambda c: c.data == 'admin_language',
                                       state='*')
    dp.register_callback_query_handler(admin_set_language_handler,
                                       lambda c: c.data.startswith('admin_lang_'),
                                       state='*')

    register_mailing(dp)
    register_shop_management(dp)
    register_user_management(dp)
    register_assistant_management(dp)
    register_owner_management(dp)
    register_view_stock(dp)
    register_purchases(dp)
    register_reseller_management(dp)
    register_miscs(dp)
    register_passwords(dp)
