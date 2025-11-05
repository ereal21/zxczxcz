"""Default configuration for main menu buttons."""
from __future__ import annotations

DEFAULT_MAIN_MENU_BUTTONS: dict[str, dict] = {
    'shop': {
        'labels': {
            'en': '🛍 Shop',
            'ru': '🛍 Магазин',
            'lt': '🛍 Parduotuvė',
        },
        'row': 0,
        'position': 0,
    },
    'profile': {
        'labels': {
            'en': '👤 Profile',
            'ru': '👤 Профиль',
            'lt': '👤 Profilis',
        },
        'row': 1,
        'position': 0,
    },
    'cart': {
        'labels': {
            'en': '🧺 My cart',
            'ru': '🧺 Моя корзина',
            'lt': '🧺 Mano krepšelis',
        },
        'row': 1,
        'position': 1,
    },
    'channel': {
        'labels': {
            'en': '📢 Channel',
            'ru': '📢 Канал',
            'lt': '📢 Kanalas',
        },
        'row': 2,
        'position': 0,
    },
    'price_list': {
        'labels': {
            'en': '💲 Price List',
            'ru': '💲 Прайс-лист',
            'lt': '💲 Kainoraštis',
        },
        'row': 2,
        'position': 1,
    },
    'language': {
        'labels': {
            'en': '🌐 Language',
            'ru': '🌐 Язык',
            'lt': '🌐 Kalba',
        },
        'row': 3,
        'position': 0,
    },
    'admin_panel': {
        'labels': {
            'en': '🎛 Admin Panel',
            'ru': '🎛 Админ панель',
            'lt': '🎛 Admin pultas',
        },
        'row': 4,
        'position': 0,
    },
}

DEFAULT_MAIN_MENU_TEXTS: dict[str, str] = {
    'en': (
        "👋 Hello, {user}!\n"
        "💼 Balance: {balance} {currency}\n"
        "📦 Orders completed: {purchases}\n"
        "👤 Loyalty status: {status}\n"
        "🔥 Purchase streak: {streak_days} days\n\n"
        "{note}"
    ),
    'ru': (
        "👋 Привет, {user}!\n"
        "💼 Баланс: {balance} {currency}\n"
        "📦 Покупок всего: {purchases}\n"
        "👤 Статус лояльности: {status}\n"
        "🔥 Серия покупок: {streak_days} дн.\n\n"
        "{note}"
    ),
    'lt': (
        "👋 Sveiki, {user}!\n"
        "💼 Balansas: {balance} {currency}\n"
        "📦 Viso pirkinių: {purchases}\n"
        "👤 Statusas: {status}\n"
        "🔥 Pirkimų serija: {streak_days} d.\n\n"
        "{note}"
    ),
}

MENU_BUTTON_CALLBACKS: dict[str, str] = {
    'shop': 'shop',
    'profile': 'profile',
    'cart': 'cart_view',
    'price_list': 'price_list',
    'language': 'change_language',
    'admin_panel': 'console',
}

MENU_BUTTON_TRANSLATIONS: dict[str, str] = {
    'shop': 'shop',
    'profile': 'profile',
    'cart': 'view_cart',
    'channel': 'channel',
    'price_list': 'price_list',
    'language': 'language',
    'admin_panel': 'admin_panel',
}
