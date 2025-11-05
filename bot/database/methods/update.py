import datetime
import json

from bot.database.models import (
    User,
    ItemValues,
    Goods,
    Categories,
    PromoCode,
    StockNotification,
    ResellerPrice,
    CartItem,
    CategoryPassword,
    UserCategoryPassword,
    MainMenuButton,
    MainMenuText,
    UiEmoji,
)
from bot.database import Database
from bot.constants.main_menu import DEFAULT_MAIN_MENU_BUTTONS, DEFAULT_MAIN_MENU_TEXTS
from bot.utils.emoji import invalidate_ui_emoji_cache


_MISSING = object()


def set_role(telegram_id: str, role: int) -> None:
    Database().session.query(User).filter(User.telegram_id == telegram_id).update(
        values={User.role_id: role})
    Database().session.commit()


def update_balance(telegram_id: int | str, summ: int) -> None:
    old_balance = User.balance
    new_balance = old_balance + summ
    Database().session.query(User).filter(User.telegram_id == telegram_id).update(
        values={User.balance: new_balance})
    Database().session.commit()


def update_user_language(telegram_id: int, language: str) -> None:
    Database().session.query(User).filter(User.telegram_id == telegram_id).update(
        values={User.language: language})
    Database().session.commit()


def update_lottery_tickets(telegram_id: int, delta: int) -> None:
    Database().session.query(User).filter(User.telegram_id == telegram_id).update(
        values={User.lottery_tickets: User.lottery_tickets + delta}, synchronize_session=False)
    Database().session.commit()


def reset_lottery_tickets() -> None:
    Database().session.query(User).update({User.lottery_tickets: 0})
    Database().session.commit()


def buy_item_for_balance(telegram_id: str, summ: int) -> int:
    old_balance = User.balance
    new_balance = old_balance - summ
    Database().session.query(User).filter(User.telegram_id == telegram_id).update(
        values={User.balance: new_balance})
    Database().session.commit()
    return Database().session.query(User.balance).filter(User.telegram_id == telegram_id).one()[0]


def update_item(item_name: str, new_name: str, new_description: str, new_price: int,
                new_category_name: str, new_delivery_description: str | None) -> None:
    Database().session.query(ItemValues).filter(ItemValues.item_name == item_name).update(
        values={ItemValues.item_name: new_name}
    )
    Database().session.query(Goods).filter(Goods.name == item_name).update(
        values={Goods.name: new_name,
                Goods.description: new_description,
                Goods.price: new_price,
                Goods.category_name: new_category_name,
                Goods.delivery_description: new_delivery_description}
    )
    Database().session.commit()


def update_category(category_name: str, new_name: str) -> None:
    Database().session.query(Categories).filter(Categories.name == category_name).update(
        values={Categories.title: new_name}
    )
    Database().session.commit()


def set_category_options(category_name: str,
                         allow_discounts: bool | None = None,
                         allow_referral_rewards: bool | None = None) -> None:
    values = {}
    if allow_discounts is not None:
        values[Categories.allow_discounts] = allow_discounts
    if allow_referral_rewards is not None:
        values[Categories.allow_referral_rewards] = allow_referral_rewards
    if not values:
        return
    Database().session.query(Categories).filter(Categories.name == category_name).update(values=values)
    Database().session.commit()


def update_promocode(
    code: str,
    discount: int | None = _MISSING,
    expires_at: str | None = _MISSING,
    items: list[str] | None = _MISSING,
) -> None:
    """Update promo code discount, expiry date or applicable items."""
    values = {}
    if discount is not _MISSING:
        values[PromoCode.discount] = discount
    if expires_at is not _MISSING:
        values[PromoCode.expires_at] = expires_at
    if items is not _MISSING:
        stored = json.dumps(sorted(set(items))) if items else None
        values[PromoCode.applicable_items] = stored
    if not values:
        return
    Database().session.query(PromoCode).filter(PromoCode.code == code).update(values=values)
    Database().session.commit()


def set_promocode_items(code: str, items: list[str]) -> None:
    """Update which items a promo code applies to."""
    update_promocode(code, items=items)


def set_reseller_price(reseller_id: int | None, item_name: str, price: int) -> None:
    session = Database().session
    entry = session.query(ResellerPrice).filter_by(
        reseller_id=reseller_id, item_name=item_name
    ).first()
    if entry:
        entry.price = price
    else:
        session.add(ResellerPrice(reseller_id=reseller_id, item_name=item_name, price=price))
    session.commit()


def clear_stock_notifications(item_name: str) -> None:
    Database().session.query(StockNotification).filter(
        StockNotification.item_name == item_name
    ).delete(synchronize_session=False)
    Database().session.commit()


def set_cart_quantity(user_id: int, item_name: str, quantity: int) -> None:
    """Update stored quantity for a cart item, removing it when quantity <= 0."""
    session = Database().session
    entry = session.query(CartItem).filter_by(user_id=user_id, item_name=item_name).first()
    if not entry:
        return
    if quantity <= 0:
        session.delete(entry)
    else:
        entry.quantity = quantity
    session.commit()


def set_category_requires_password(category_name: str, requires_password: bool) -> None:
    session = Database().session
    session.query(Categories).filter(Categories.name == category_name).update(
        {Categories.requires_password: requires_password}
    )
    session.commit()


def upsert_user_category_password(
    user_id: int,
    category_name: str,
    password: str,
    generated_password_id: int | None = None,
    *,
    acknowledged: bool | None = None,
) -> UserCategoryPassword:
    session = Database().session
    entry = (
        session.query(UserCategoryPassword)
        .filter(
            UserCategoryPassword.user_id == user_id,
            UserCategoryPassword.category_name == category_name,
        )
        .first()
    )
    now = datetime.datetime.utcnow().isoformat()
    if entry:
        entry.password = password
        entry.generated_password_id = generated_password_id
        entry.updated_at = now
        if acknowledged is not None:
            entry.acknowledged = acknowledged
    else:
        ack_value = acknowledged if acknowledged is not None else False
        entry = UserCategoryPassword(
            user_id=user_id,
            category_name=category_name,
            password=password,
            updated_at=now,
            generated_password_id=generated_password_id,
            acknowledged=ack_value,
        )
        session.add(entry)
    session.commit()


def _get_or_create_menu_button(session, key: str) -> MainMenuButton:
    entry = session.query(MainMenuButton).filter(MainMenuButton.key == key).first()
    if entry:
        return entry
    default = DEFAULT_MAIN_MENU_BUTTONS.get(key)
    labels = json.dumps(default.get('labels', {}), ensure_ascii=False) if default else json.dumps({})
    entry = MainMenuButton(
        key=key,
        label=labels,
        row=default.get('row', 0) if default else 0,
        position=default.get('position', 0) if default else 0,
        enabled=default.get('enabled', True) if default else True,
        url=default.get('url'),
    )
    session.add(entry)
    session.flush()
    return entry


def update_main_menu_button(
    key: str,
    *,
    labels: dict[str, str] | None = None,
    row: int | None = None,
    position: int | None = None,
    enabled: bool | None = None,
    url: str | None = _MISSING,
) -> None:
    session = Database().session
    entry = _get_or_create_menu_button(session, key)
    if labels is not None:
        entry.label = json.dumps(labels, ensure_ascii=False)
    if row is not None:
        entry.row = row
    if position is not None:
        entry.position = position
    if enabled is not None:
        entry.enabled = enabled
    if url is not _MISSING:
        entry.url = url
    session.commit()


def reset_main_menu_buttons() -> None:
    session = Database().session
    session.query(MainMenuButton).delete()
    for key, data in DEFAULT_MAIN_MENU_BUTTONS.items():
        session.add(
            MainMenuButton(
                key=key,
                label=json.dumps(data.get('labels', {}), ensure_ascii=False),
                row=data.get('row', 0),
                position=data.get('position', 0),
                enabled=data.get('enabled', True),
                url=data.get('url'),
            )
        )
    session.commit()


def update_main_menu_text(language: str, template: str) -> None:
    session = Database().session
    entry = (
        session.query(MainMenuText)
        .filter(MainMenuText.language == language)
        .first()
    )
    if not entry:
        entry = MainMenuText(language=language, template=template)
        session.add(entry)
    else:
        entry.template = template
    session.commit()


def reset_main_menu_text(language: str) -> None:
    session = Database().session
    default = DEFAULT_MAIN_MENU_TEXTS.get(language, DEFAULT_MAIN_MENU_TEXTS['en'])
    entry = (
        session.query(MainMenuText)
        .filter(MainMenuText.language == language)
        .first()
    )
    if not entry:
        session.add(MainMenuText(language=language, template=default))
    else:
        entry.template = default
    session.commit()


def set_ui_emoji_override(original: str, replacement: str) -> None:
    session = Database().session
    entry = session.query(UiEmoji).filter(UiEmoji.original == original).first()
    if entry:
        entry.replacement = replacement
    else:
        entry = UiEmoji(original=original, replacement=replacement)
        session.add(entry)
    session.commit()
    invalidate_ui_emoji_cache()


def delete_ui_emoji_override(original: str) -> None:
    session = Database().session
    entry = session.query(UiEmoji).filter(UiEmoji.original == original).first()
    if not entry:
        return
    session.delete(entry)
    session.commit()
    invalidate_ui_emoji_cache()


def clear_ui_emoji_overrides() -> None:
    session = Database().session
    session.query(UiEmoji).delete()
    session.commit()
    invalidate_ui_emoji_cache()


def set_user_category_password_ack(
    user_id: int,
    category_name: str,
    acknowledged: bool,
) -> None:
    session = Database().session
    entry = (
        session.query(UserCategoryPassword)
        .filter(
            UserCategoryPassword.user_id == user_id,
            UserCategoryPassword.category_name == category_name,
        )
        .first()
    )
    if not entry:
        return
    entry.acknowledged = acknowledged
    session.commit()


def mark_generated_password_used(password_id: int, user_id: int, category_name: str) -> None:
    session = Database().session
    entry = session.query(CategoryPassword).filter(CategoryPassword.id == password_id).first()
    if not entry:
        return
    entry.used_by_user_id = user_id
    entry.used_for_category = category_name
    session.commit()


def clear_generated_password_usage(password_id: int) -> None:
    session = Database().session
    entry = session.query(CategoryPassword).filter(CategoryPassword.id == password_id).first()
    if not entry:
        return
    entry.used_by_user_id = None
    entry.used_for_category = None
    session.commit()


def process_purchase_streak(telegram_id: int) -> None:
    """Update streak data after a successful purchase."""
    session = Database().session
    user = session.query(User).filter(User.telegram_id == telegram_id).one()
    today = datetime.date.today()

    if user.streak_discount:
        user.streak_discount = False
        user.purchase_streak = 0

    if user.last_purchase_date:
        last_date = datetime.date.fromisoformat(user.last_purchase_date)
        diff = (today - last_date).days
        if diff == 1:
            user.purchase_streak += 1
        elif diff > 1:
            user.purchase_streak = 1
    else:
        user.purchase_streak = 1

    user.last_purchase_date = today.isoformat()

    if user.purchase_streak >= 3:
        user.purchase_streak = 0
        user.streak_discount = True

    session.commit()
