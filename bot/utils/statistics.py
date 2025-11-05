from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Final

from bot.database.methods import (
    get_user_count,
    select_admins,
    select_all_operations,
    select_all_orders,
    select_count_bought_items,
    select_count_categories,
    select_count_goods,
    select_count_items,
    select_today_operations,
    select_today_orders,
    select_today_users,
    select_users_balance,
)

SUPPORTED_LANGS: Final = {"en", "ru", "lt"}


@dataclass(frozen=True)
class ShopStatistics:
    """Snapshot of shop metrics used across the admin panel."""

    today_users: int
    total_admins: int
    total_users: int
    sales_today: float
    sales_total: float
    topups_today: float
    funds_total: float
    topups_total: float
    items_available: int
    goods_positions: int
    categories_total: int
    items_sold_total: int
    generated_at: datetime.datetime


def collect_shop_statistics(reference: datetime.datetime | None = None) -> ShopStatistics:
    """Collect aggregated shop statistics for dashboards."""

    ref = reference or datetime.datetime.now()
    today_str = ref.strftime("%Y-%m-%d")

    def _num(value) -> float:
        return float(value or 0)

    return ShopStatistics(
        today_users=int(select_today_users(today_str) or 0),
        total_admins=int(select_admins() or 0),
        total_users=int(get_user_count() or 0),
        sales_today=_num(select_today_orders(today_str)),
        sales_total=_num(select_all_orders()),
        topups_today=_num(select_today_operations(today_str)),
        funds_total=_num(select_users_balance()),
        topups_total=_num(select_all_operations()),
        items_available=int(select_count_items() or 0),
        goods_positions=int(select_count_goods() or 0),
        categories_total=int(select_count_categories() or 0),
        items_sold_total=int(select_count_bought_items() or 0),
        generated_at=ref,
    )


def format_admin_statistics(stats: ShopStatistics, lang: str = "lt") -> str:
    """Return a professional statistics block for the admin panel."""

    code = lang if lang in SUPPORTED_LANGS else "en"
    timestamp = stats.generated_at.strftime("%Y-%m-%d %H:%M")

    translations = {
        "lt": {
            "headline": "📊 <b>Parduotuvės veiklos suvestinė</b>",
            "subtitle": "🔎 Svarbiausi šiandienos rodikliai",
            "timestamp": f"🕒 Atnaujinta: {timestamp}",
            "users": "👥 <b>Klientai ir komanda</b>",
            "treasury": "💼 <b>Finansiniai rodikliai</b>",
            "vault": "📦 <b>Sandėlio būklė</b>",
            "footer": "⚙️ Valdykite parduotuvę naudodami žemiau esančius mygtukus.",
            "lines": (
                f"• Nauji klientai per 24 h: <b>{stats.today_users}</b>",
                f"• Administratorių komanda: <b>{stats.total_admins}</b>",
                f"• Viso vartotojų: <b>{stats.total_users}</b>",
                f"• Pardavimai šiandien: <b>{stats.sales_today:.2f}€</b>",
                f"• Pardavimai viso: <b>{stats.sales_total:.2f}€</b>",
                f"• Papildymai šiandien: <b>{stats.topups_today:.2f}€</b>",
                f"• Lėšos balansuose: <b>{stats.funds_total:.2f}€</b>",
                f"• Papildymai viso: <b>{stats.topups_total:.2f}€</b>",
                f"• Turimų vienetų sandėlyje: <b>{stats.items_available}</b>",
                f"• Prekių pozicijų: <b>{stats.goods_positions}</b>",
                f"• Kategorijų: <b>{stats.categories_total}</b>",
                f"• Parduotų vienetų viso: <b>{stats.items_sold_total}</b>",
            ),
        },
        "en": {
            "headline": "📊 <b>Store performance snapshot</b>",
            "subtitle": "🔎 Key metrics for today",
            "timestamp": f"🕒 Updated: {timestamp}",
            "users": "👥 <b>Customers & team</b>",
            "treasury": "💼 <b>Financial indicators</b>",
            "vault": "📦 <b>Inventory overview</b>",
            "footer": "⚙️ Use the buttons below to manage the store.",
            "lines": (
                f"• New customers (24h): <b>{stats.today_users}</b>",
                f"• Admin team size: <b>{stats.total_admins}</b>",
                f"• Total users: <b>{stats.total_users}</b>",
                f"• Sales today: <b>{stats.sales_today:.2f}€</b>",
                f"• Lifetime sales: <b>{stats.sales_total:.2f}€</b>",
                f"• Top-ups today: <b>{stats.topups_today:.2f}€</b>",
                f"• Funds on balances: <b>{stats.funds_total:.2f}€</b>",
                f"• Lifetime top-ups: <b>{stats.topups_total:.2f}€</b>",
                f"• Items in stock: <b>{stats.items_available}</b>",
                f"• Goods positions: <b>{stats.goods_positions}</b>",
                f"• Categories online: <b>{stats.categories_total}</b>",
                f"• Units sold total: <b>{stats.items_sold_total}</b>",
            ),
        },
        "ru": {
            "headline": "📊 <b>Отчёт о работе магазина</b>",
            "subtitle": "🔎 Ключевые показатели за сегодня",
            "timestamp": f"🕒 Обновлено: {timestamp}",
            "users": "👥 <b>Клиенты и команда</b>",
            "treasury": "💼 <b>Финансовые показатели</b>",
            "vault": "📦 <b>Состояние склада</b>",
            "footer": "⚙️ Используйте кнопки ниже для управления магазином.",
            "lines": (
                f"• Новых клиентов за 24 ч: <b>{stats.today_users}</b>",
                f"• Администраторов: <b>{stats.total_admins}</b>",
                f"• Всего пользователей: <b>{stats.total_users}</b>",
                f"• Продажи сегодня: <b>{stats.sales_today:.2f}€</b>",
                f"• Продажи за всё время: <b>{stats.sales_total:.2f}€</b>",
                f"• Пополнения сегодня: <b>{stats.topups_today:.2f}€</b>",
                f"• Средств на балансах: <b>{stats.funds_total:.2f}€</b>",
                f"• Пополнения за всё время: <b>{stats.topups_total:.2f}€</b>",
                f"• Товаров на складе: <b>{stats.items_available}</b>",
                f"• Позиции товаров: <b>{stats.goods_positions}</b>",
                f"• Категорий: <b>{stats.categories_total}</b>",
                f"• Проданных единиц всего: <b>{stats.items_sold_total}</b>",
            ),
        },
    }

    strings = translations[code]

    users_block = "\n".join(strings["lines"][0:3])
    treasury_block = "\n".join(strings["lines"][3:8])
    vault_block = "\n".join(strings["lines"][8:])

    divider = "────────────────────"

    return (
        f"{strings['headline']}\n"
        f"{strings['subtitle']}\n"
        f"{strings['timestamp']}\n\n"
        f"{strings['users']}\n"
        f"{users_block}\n"
        f"{divider}\n"
        f"{strings['treasury']}\n"
        f"{treasury_block}\n"
        f"{divider}\n"
        f"{strings['vault']}\n"
        f"{vault_block}\n\n"
        f"{strings['footer']}"
    )
