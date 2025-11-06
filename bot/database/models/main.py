import datetime
import json

from sqlalchemy import (
    Column,
    Integer,
    String,
    BigInteger,
    ForeignKey,
    Text,
    Boolean,
    VARCHAR,
    UniqueConstraint,
    inspect,
    text,
)
from bot.constants.main_menu import DEFAULT_MAIN_MENU_BUTTONS, DEFAULT_MAIN_MENU_TEXTS
from bot.constants.levels import DEFAULT_LEVEL_NAMES, DEFAULT_LEVEL_THRESHOLDS
from bot.constants.profile import DEFAULT_PROFILE_SETTINGS
from bot.constants.quests import (
    DEFAULT_QUEST_TITLES,
    DEFAULT_QUEST_RESET,
    DEFAULT_QUEST_TASKS,
    DEFAULT_QUEST_REWARD,
)
from bot.constants.achievements import DEFAULT_ACHIEVEMENTS
from bot.database.main import Database
from sqlalchemy.orm import relationship


class Permission:
    USE = 1
    BROADCAST = 2
    SETTINGS_MANAGE = 4
    USERS_MANAGE = 8
    SHOP_MANAGE = 16
    ADMINS_MANAGE = 32
    OWN = 64
    ASSIGN_PHOTOS = 128


class Role(Database.BASE):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True)
    name = Column(String(64), unique=True)
    default = Column(Boolean, default=False, index=True)
    permissions = Column(Integer)
    users = relationship('User', backref='role', lazy='dynamic')

    def __init__(self, name: str, permissions=None, **kwargs):
        super(Role, self).__init__(**kwargs)
        if self.permissions is None:
            self.permissions = 0
        self.name = name
        self.permissions = permissions

    @staticmethod
    def insert_roles():
        roles = {
            'USER': [Permission.USE],
            'ADMIN': [Permission.USE, Permission.BROADCAST,
                      Permission.SETTINGS_MANAGE, Permission.USERS_MANAGE,
                      Permission.SHOP_MANAGE, Permission.ASSIGN_PHOTOS],
            'OWNER': [Permission.USE, Permission.BROADCAST,
                      Permission.SETTINGS_MANAGE, Permission.USERS_MANAGE,
                      Permission.SHOP_MANAGE, Permission.ADMINS_MANAGE,
                      Permission.OWN, Permission.ASSIGN_PHOTOS],
            'ASSISTANT': [Permission.USE, Permission.ASSIGN_PHOTOS],
        }
        default_role = 'USER'
        for r in roles:
            role = Database().session.query(Role).filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.reset_permissions()
            for perm in roles[r]:
                role.add_permission(perm)
            role.default = (role.name == default_role)
            Database().session.add(role)
        Database().session.commit()

    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm

    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permissions -= perm

    def reset_permissions(self):
        self.permissions = 0

    def has_permission(self, perm):
        return self.permissions & perm == perm

    def __repr__(self):
        return '<Role %r>' % self.name


class User(Database.BASE):
    __tablename__ = 'users'
    telegram_id = Column(BigInteger, nullable=False, unique=True, primary_key=True)
    username = Column(String(64), nullable=True)
    role_id = Column(Integer, ForeignKey('roles.id'), default=1)
    balance = Column(BigInteger, nullable=False, default=0)
    lottery_tickets = Column(Integer, nullable=False, default=0)
    purchase_streak = Column(Integer, nullable=False, default=0)
    last_purchase_date = Column(VARCHAR, nullable=True)
    streak_discount = Column(Boolean, nullable=False, default=False)
    language = Column(String(5), nullable=True)
    referral_id = Column(BigInteger, nullable=True)
    registration_date = Column(VARCHAR, nullable=False)
    user_operations = relationship("Operations", back_populates="user_telegram_id")
    user_unfinished_operations = relationship("UnfinishedOperations", back_populates="user_telegram_id")
    user_goods = relationship("BoughtGoods", back_populates="user_telegram_id")

    def __init__(self, telegram_id: int, registration_date: datetime.datetime, balance: int = 0,
                 referral_id=None, role_id: int = 1, language: str | None = None,
                 username: str | None = None, purchase_streak: int = 0,
                 last_purchase_date: str | None = None, streak_discount: bool = False):
        self.telegram_id = telegram_id
        self.username = username
        self.role_id = role_id
        self.balance = balance
        self.referral_id = referral_id
        self.registration_date = registration_date
        self.language = language
        self.purchase_streak = purchase_streak
        self.last_purchase_date = last_purchase_date
        self.streak_discount = streak_discount


class Categories(Database.BASE):
    __tablename__ = 'categories'
    name = Column(String(100), primary_key=True, unique=True, nullable=False)
    title = Column(String(100), nullable=False, default='')
    parent_name = Column(String(100), nullable=True)
    allow_discounts = Column(Boolean, nullable=False, default=True)
    allow_referral_rewards = Column(Boolean, nullable=False, default=True)
    requires_password = Column(Boolean, nullable=False, default=False)
    item = relationship("Goods", back_populates="category")

    def __init__(
        self,
        name: str,
        parent_name: str | None = None,
        allow_discounts: bool = True,
        allow_referral_rewards: bool = True,
        requires_password: bool = False,
        title: str | None = None,
    ):
        self.name = name
        self.title = title or name
        self.parent_name = parent_name
        self.allow_discounts = allow_discounts
        self.allow_referral_rewards = allow_referral_rewards
        self.requires_password = requires_password


class Term(Database.BASE):
    __tablename__ = 'terms'

    code = Column(String(64), primary_key=True, unique=True)
    labels = Column(Text, nullable=False)
    created_at = Column(VARCHAR, nullable=False)

    def __init__(self, code: str, labels: dict[str, str] | None = None, created_at: str | None = None):
        self.code = code
        self.labels = json.dumps(labels or {}, ensure_ascii=False)
        timestamp = created_at or datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        self.created_at = timestamp

    def labels_dict(self) -> dict[str, str]:
        try:
            data = json.loads(self.labels) if self.labels else {}
        except (TypeError, ValueError):
            data = {}
        return data


class Goods(Database.BASE):
    __tablename__ = 'goods'
    name = Column(String(100), nullable=False, unique=True, primary_key=True)
    price = Column(BigInteger, nullable=False)
    description = Column(Text, nullable=False)
    delivery_description = Column(Text, nullable=True)
    category_name = Column(String(100), ForeignKey('categories.name'), nullable=False)
    term_code = Column(String(64), ForeignKey('terms.code'), nullable=True)
    category = relationship("Categories", back_populates="item")
    term = relationship("Term", lazy='joined')
    values = relationship("ItemValues", back_populates="item")

    def __init__(self, name: str, price: int, description: str, category_name: str,
                 delivery_description: str | None = None, term_code: str | None = None):
        self.name = name
        self.price = price
        self.description = description
        self.delivery_description = delivery_description
        self.category_name = category_name
        self.term_code = term_code


class ItemValues(Database.BASE):
    __tablename__ = 'item_values'
    id = Column(Integer, nullable=False, primary_key=True)
    item_name = Column(String(100), ForeignKey('goods.name'), nullable=False)
    value = Column(Text, nullable=True)
    is_infinity = Column(Boolean, nullable=False)
    item = relationship("Goods", back_populates="values")

    def __init__(self, name: str, value: str, is_infinity: bool):
        self.item_name = name
        self.value = value
        self.is_infinity = is_infinity


class BoughtGoods(Database.BASE):
    __tablename__ = 'bought_goods'
    id = Column(Integer, nullable=False, primary_key=True)
    item_name = Column(String(100), nullable=False)
    value = Column(Text, nullable=False)
    price = Column(BigInteger, nullable=False)
    buyer_id = Column(BigInteger, ForeignKey('users.telegram_id'), nullable=False)
    bought_datetime = Column(VARCHAR, nullable=False)
    unique_id = Column(BigInteger, nullable=False, unique=True)
    term_code = Column(String(64), ForeignKey('terms.code'), nullable=True)
    user_telegram_id = relationship("User", back_populates="user_goods")

    def __init__(self, name: str, value: str, price: int, bought_datetime: str, unique_id,
                 buyer_id: int = 0, term_code: str | None = None):
        self.item_name = name
        self.value = value
        self.price = price
        self.buyer_id = buyer_id
        self.bought_datetime = bought_datetime
        self.unique_id = unique_id
        self.term_code = term_code


class Operations(Database.BASE):
    __tablename__ = 'operations'
    id = Column(Integer, nullable=False, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.telegram_id'), nullable=False)
    operation_value = Column(BigInteger, nullable=False)
    operation_time = Column(VARCHAR, nullable=False)
    user_telegram_id = relationship("User", back_populates="user_operations")

    def __init__(self, user_id: int, operation_value: int, operation_time: str):
        self.user_id = user_id
        self.operation_value = operation_value
        self.operation_time = operation_time


class UnfinishedOperations(Database.BASE):
    __tablename__ = 'unfinished_operations'
    id = Column(Integer, nullable=False, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.telegram_id'), nullable=False)
    operation_value = Column(BigInteger, nullable=False)
    operation_id = Column(String(500), nullable=False)
    message_id = Column(BigInteger, nullable=True)
    user_telegram_id = relationship("User", back_populates="user_unfinished_operations")

    def __init__(self, user_id: int, operation_value: int, operation_id: str, message_id: int | None = None):
        self.user_id = user_id
        self.operation_value = operation_value
        self.operation_id = operation_id
        self.message_id = message_id


class Achievement(Database.BASE):
    __tablename__ = 'achievements'
    code = Column(String(50), primary_key=True, unique=True)
    config = Column(Text, nullable=True)

    def __init__(self, code: str, config: dict | None = None):
        self.code = code
        self.config = json.dumps(config or {}, ensure_ascii=False)

    def config_dict(self) -> dict:
        try:
            data = json.loads(self.config) if self.config else {}
        except (TypeError, ValueError):
            data = {}
        if not isinstance(data, dict):
            data = {}
        return data


class UserAchievement(Database.BASE):
    __tablename__ = 'user_achievements'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.telegram_id'), nullable=False)
    achievement_code = Column(String(50), ForeignKey('achievements.code'), nullable=False)
    achieved_at = Column(VARCHAR, nullable=False)

    def __init__(self, user_id: int, achievement_code: str, achieved_at: str):
        self.user_id = user_id
        self.achievement_code = achievement_code
        self.achieved_at = achieved_at


class PromoCode(Database.BASE):
    __tablename__ = 'promo_codes'
    code = Column(String(50), primary_key=True, unique=True)
    discount = Column(Integer, nullable=False)
    expires_at = Column(VARCHAR, nullable=True)
    active = Column(Boolean, default=True)
    applicable_items = Column(Text, nullable=True)

    def __init__(self, code: str, discount: int, expires_at: str | None = None,
                 active: bool = True, applicable_items: str | None = None):
        self.code = code
        self.discount = discount
        self.expires_at = expires_at
        self.active = active
        self.applicable_items = applicable_items


class Reseller(Database.BASE):
    __tablename__ = 'resellers'
    user_id = Column(BigInteger, ForeignKey('users.telegram_id'), primary_key=True, unique=True)

    def __init__(self, user_id: int):
        self.user_id = user_id


class ResellerPrice(Database.BASE):
    __tablename__ = 'reseller_prices'
    id = Column(Integer, primary_key=True)
    reseller_id = Column(BigInteger, ForeignKey('resellers.user_id'), nullable=True)
    item_name = Column(String(100), ForeignKey('goods.name'), nullable=False)
    price = Column(BigInteger, nullable=False)

    def __init__(self, reseller_id: int | None, item_name: str, price: int):
        self.reseller_id = reseller_id
        self.item_name = item_name
        self.price = price


class StockNotification(Database.BASE):
    __tablename__ = 'stock_notifications'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.telegram_id'), nullable=False)
    item_name = Column(String(100), ForeignKey('goods.name'), nullable=False)

    def __init__(self, user_id: int, item_name: str):
        self.user_id = user_id
        self.item_name = item_name


class CartItem(Database.BASE):
    __tablename__ = 'cart_items'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.telegram_id'), nullable=False)
    item_name = Column(String(100), ForeignKey('goods.name'), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)

    def __init__(self, user_id: int, item_name: str, quantity: int = 1):
        self.user_id = user_id
        self.item_name = item_name
        self.quantity = quantity


class CategoryPassword(Database.BASE):
    __tablename__ = 'category_passwords'
    id = Column(Integer, primary_key=True)
    password = Column(String(64), nullable=False, unique=True)
    created_at = Column(VARCHAR, nullable=False)
    used_by_user_id = Column(BigInteger, ForeignKey('users.telegram_id'), nullable=True)
    used_for_category = Column(String(100), ForeignKey('categories.name'), nullable=True)

    user = relationship('User', backref='category_passwords', lazy='joined')
    category = relationship('Categories', lazy='joined')

    def __init__(self, password: str, created_at: str):
        self.password = password
        self.created_at = created_at


class UserCategoryPassword(Database.BASE):
    __tablename__ = 'user_category_passwords'
    __table_args__ = (
        UniqueConstraint('user_id', 'category_name', name='uq_user_category_password'),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.telegram_id'), nullable=False)
    category_name = Column(String(100), ForeignKey('categories.name'), nullable=False)
    password = Column(String(64), nullable=False)
    generated_password_id = Column(Integer, ForeignKey('category_passwords.id'), nullable=True)
    updated_at = Column(VARCHAR, nullable=False)
    acknowledged = Column(Boolean, nullable=False, server_default=text('0'))

    user = relationship('User', backref='category_password_entries', lazy='joined')
    category = relationship('Categories', lazy='joined')
    generated_password = relationship('CategoryPassword', lazy='joined')

    def __init__(self, user_id: int, category_name: str, password: str,
                 updated_at: str, generated_password_id: int | None = None,
                 acknowledged: bool = False):
        self.user_id = user_id
        self.category_name = category_name
        self.password = password
        self.updated_at = updated_at
        self.generated_password_id = generated_password_id
        self.acknowledged = acknowledged


class MainMenuButton(Database.BASE):
    __tablename__ = 'main_menu_buttons'

    key = Column(String(50), primary_key=True, unique=True, nullable=False)
    label = Column(Text, nullable=False)
    row = Column(Integer, nullable=False, default=0)
    position = Column(Integer, nullable=False, default=0)
    enabled = Column(Boolean, nullable=False, default=True)
    url = Column(String(255), nullable=True)

    def __init__(
        self,
        key: str,
        label: str | None = None,
        row: int = 0,
        position: int = 0,
        enabled: bool = True,
        url: str | None = None,
    ):
        default = DEFAULT_MAIN_MENU_BUTTONS.get(key, {})
        self.key = key
        self.label = label or json.dumps(default.get('labels', {}), ensure_ascii=False)
        self.row = row if row is not None else default.get('row', 0)
        self.position = position if position is not None else default.get('position', 0)
        self.enabled = enabled
        self.url = url


class MainMenuText(Database.BASE):
    __tablename__ = 'main_menu_texts'

    language = Column(String(5), primary_key=True, unique=True, nullable=False)
    template = Column(Text, nullable=False)

    def __init__(self, language: str, template: str | None = None):
        self.language = language
        self.template = template or DEFAULT_MAIN_MENU_TEXTS.get(language, DEFAULT_MAIN_MENU_TEXTS['en'])


class UiEmoji(Database.BASE):
    __tablename__ = 'ui_emojis'

    original = Column(String(16), primary_key=True, unique=True, nullable=False)
    replacement = Column(String(16), nullable=False)

    def __init__(self, original: str, replacement: str):
        self.original = original
        self.replacement = replacement


class LevelSettings(Database.BASE):
    __tablename__ = 'level_settings'

    id = Column(Integer, primary_key=True)
    thresholds = Column(Text, nullable=False)
    names = Column(Text, nullable=False)
    rewards = Column(Text, nullable=False)

    def __init__(self, thresholds: list[int] | None = None, names: dict[str, list[str]] | None = None,
                 rewards: list[int] | None = None):
        base_thresholds = thresholds or list(DEFAULT_LEVEL_THRESHOLDS)
        base_names = names or DEFAULT_LEVEL_NAMES
        base_rewards = rewards or [0 for _ in base_thresholds]
        self.thresholds = json.dumps(list(base_thresholds))
        self.names = json.dumps(base_names, ensure_ascii=False)
        self.rewards = json.dumps(list(base_rewards))


class ProfileSettings(Database.BASE):
    __tablename__ = 'profile_settings'

    id = Column(Integer, primary_key=True)
    options = Column(Text, nullable=False)

    def __init__(self, options: dict | None = None):
        base_options = DEFAULT_PROFILE_SETTINGS.copy()
        if options:
            base_options.update(options)
        self.options = json.dumps(base_options, ensure_ascii=False)

    def as_dict(self) -> dict:
        try:
            stored = json.loads(self.options) if self.options else {}
        except (TypeError, ValueError):
            stored = {}
        merged = DEFAULT_PROFILE_SETTINGS.copy()
        merged.update(stored)
        return merged


class QuestSettings(Database.BASE):
    __tablename__ = 'quest_settings'

    id = Column(Integer, primary_key=True)
    titles = Column(Text, nullable=False)
    tasks = Column(Text, nullable=False)
    reward = Column(Text, nullable=False)
    reset_weekday = Column(Integer, nullable=False, default=0)
    reset_hour = Column(Integer, nullable=False, default=12)

    def __init__(self,
                 titles: dict | None = None,
                 tasks: list[dict] | None = None,
                 reward: dict | None = None,
                 reset_weekday: int | None = None,
                 reset_hour: int | None = None):
        self.titles = json.dumps(titles or DEFAULT_QUEST_TITLES, ensure_ascii=False)
        self.tasks = json.dumps(tasks or DEFAULT_QUEST_TASKS, ensure_ascii=False)
        self.reward = json.dumps(reward or DEFAULT_QUEST_REWARD, ensure_ascii=False)
        reset_defaults = DEFAULT_QUEST_RESET
        self.reset_weekday = reset_weekday if reset_weekday is not None else reset_defaults['weekday']
        self.reset_hour = reset_hour if reset_hour is not None else reset_defaults['hour']

    def titles_dict(self) -> dict:
        try:
            return json.loads(self.titles) if self.titles else DEFAULT_QUEST_TITLES
        except (TypeError, ValueError):  # pragma: no cover - unexpected data
            return DEFAULT_QUEST_TITLES

    def tasks_list(self) -> list[dict]:
        try:
            data = json.loads(self.tasks) if self.tasks else []
        except (TypeError, ValueError):
            data = []
        if not isinstance(data, list):
            return []
        return data

    def reward_dict(self) -> dict:
        try:
            data = json.loads(self.reward) if self.reward else {}
        except (TypeError, ValueError):
            data = {}
        if not isinstance(data, dict):
            data = {}
        return data


def register_models():
    engine = Database().engine
    inspector = inspect(engine)
    if 'categories' in inspector.get_table_names():
        columns = {column['name'] for column in inspector.get_columns('categories')}
        if 'title' not in columns:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE categories ADD COLUMN title VARCHAR(100)")
                )
                connection.execute(
                    text("UPDATE categories SET title = name WHERE title IS NULL OR title = ''")
                )
        if 'requires_password' not in columns:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE categories ADD COLUMN requires_password BOOLEAN DEFAULT 0"
                    )
                )
                connection.execute(
                    text("UPDATE categories SET requires_password = 0 WHERE requires_password IS NULL")
                )
    if 'user_category_passwords' in inspector.get_table_names():
        columns = {column['name'] for column in inspector.get_columns('user_category_passwords')}
        if 'acknowledged' not in columns:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE user_category_passwords ADD COLUMN acknowledged BOOLEAN DEFAULT 0"
                    )
                )
                connection.execute(
                    text(
                        "UPDATE user_category_passwords SET acknowledged = 0 WHERE acknowledged IS NULL"
                    )
                )
    if 'promo_codes' in inspector.get_table_names():
        promo_columns = {column['name'] for column in inspector.get_columns('promo_codes')}
        if 'applicable_items' not in promo_columns:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE promo_codes ADD COLUMN applicable_items TEXT")
                )
    if 'goods' in inspector.get_table_names():
        goods_columns = {column['name'] for column in inspector.get_columns('goods')}
        if 'term_code' not in goods_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE goods ADD COLUMN term_code VARCHAR(64)"))
    if 'bought_goods' in inspector.get_table_names():
        bought_columns = {column['name'] for column in inspector.get_columns('bought_goods')}
        if 'term_code' not in bought_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE bought_goods ADD COLUMN term_code VARCHAR(64)"))
    if 'achievements' in inspector.get_table_names():
        achievement_columns = {column['name'] for column in inspector.get_columns('achievements')}
        if 'config' not in achievement_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE achievements ADD COLUMN config TEXT"))
    if 'level_settings' in inspector.get_table_names():
        level_columns = {column['name'] for column in inspector.get_columns('level_settings')}
        if 'rewards' not in level_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE level_settings ADD COLUMN rewards TEXT"))
                connection.execute(text("UPDATE level_settings SET rewards = '[]' WHERE rewards IS NULL"))
    if 'reseller_prices' in inspector.get_table_names():
        for column in inspector.get_columns('reseller_prices'):
            if column['name'] == 'reseller_id' and not column['nullable']:
                ResellerPrice.__table__.drop(engine)
                break
    Database.BASE.metadata.create_all(engine)
    _ensure_main_menu_defaults()
    _ensure_level_settings()
    _ensure_profile_settings()
    _ensure_quest_settings()
    _ensure_achievement_defaults()
    Role.insert_roles()


def _ensure_main_menu_defaults() -> None:
    session = Database().session
    existing = {
        entry.key: entry
        for entry in session.query(MainMenuButton).all()
    }
    changed = False
    for key, data in DEFAULT_MAIN_MENU_BUTTONS.items():
        if key not in existing:
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
            changed = True
        else:
            entry = existing[key]
            if not entry.label:
                entry.label = json.dumps(data.get('labels', {}), ensure_ascii=False)
                changed = True
    existing_texts = {
        entry.language: entry
        for entry in session.query(MainMenuText).all()
    }
    for language, template in DEFAULT_MAIN_MENU_TEXTS.items():
        if language not in existing_texts:
            session.add(MainMenuText(language=language, template=template))
            changed = True
    if changed:
        session.commit()


def _ensure_level_settings() -> None:
    session = Database().session
    entry = session.query(LevelSettings).first()
    if entry is None:
        session.add(LevelSettings())
        session.commit()
        return
    changed = False
    try:
        raw_thresholds = json.loads(entry.thresholds or '[]')
    except (TypeError, ValueError):
        raw_thresholds = []
    if not isinstance(raw_thresholds, list):
        raw_thresholds = []
    thresholds: list[int] = []
    for value in raw_thresholds:
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        if number < 0 or number in thresholds:
            continue
        thresholds.append(number)
    if not thresholds:
        thresholds = list(DEFAULT_LEVEL_THRESHOLDS)
    if 0 not in thresholds:
        thresholds.append(0)
    thresholds.sort()
    if thresholds != raw_thresholds:
        changed = True

    try:
        raw_names = json.loads(entry.names or '{}')
    except (TypeError, ValueError):
        raw_names = {}
    if not isinstance(raw_names, dict):
        raw_names = {}
    languages = set(DEFAULT_LEVEL_NAMES.keys()) | set(raw_names.keys())
    cleaned_names: dict[str, list[str]] = {}
    for language in languages:
        defaults = DEFAULT_LEVEL_NAMES.get(language, DEFAULT_LEVEL_NAMES.get('en', []))
        existing = raw_names.get(language)
        if not isinstance(existing, list):
            existing = []
        values: list[str] = []
        for index in range(len(thresholds)):
            text = ''
            if index < len(existing):
                raw_value = existing[index]
                if raw_value is not None:
                    text = str(raw_value).strip()
            if not text:
                if index < len(defaults):
                    text = defaults[index]
                else:
                    text = f'Level {index + 1}'
            values.append(text)
        cleaned_names[language] = values
    if cleaned_names != raw_names:
        changed = True

    try:
        raw_rewards = json.loads(entry.rewards or '[]')
    except (TypeError, ValueError):
        raw_rewards = []
    if not isinstance(raw_rewards, list):
        raw_rewards = []
    rewards: list[int] = []
    for index in range(len(thresholds)):
        value = 0
        if index < len(raw_rewards):
            try:
                number = int(raw_rewards[index])
            except (TypeError, ValueError):
                number = 0
            if number < 0:
                number = 0
            if number > 100:
                number = 100
            value = number
        rewards.append(value)
    if rewards != raw_rewards:
        changed = True

    if changed:
        entry.thresholds = json.dumps(thresholds)
        entry.names = json.dumps(cleaned_names, ensure_ascii=False)
        entry.rewards = json.dumps(rewards)
        session.commit()


def _ensure_profile_settings() -> None:
    session = Database().session
    if session.query(ProfileSettings).first() is None:
        session.add(ProfileSettings())
        session.commit()


def _ensure_quest_settings() -> None:
    session = Database().session
    entry = session.query(QuestSettings).first()
    if entry is None:
        session.add(QuestSettings())
        session.commit()
        return
    changed = False
    titles = entry.titles_dict()
    languages = set(DEFAULT_QUEST_TITLES.keys()) | set(titles.keys())
    merged_titles: dict[str, dict[str, str]] = {}
    for language in languages:
        defaults = DEFAULT_QUEST_TITLES.get(language, DEFAULT_QUEST_TITLES['en'])
        existing = titles.get(language, {})
        if not isinstance(existing, dict):
            existing = {}
        title_text = existing.get('title') or defaults['title']
        desc_text = existing.get('description') or defaults['description']
        merged_titles[language] = {
            'title': str(title_text).strip(),
            'description': str(desc_text).strip(),
        }
    if merged_titles != titles:
        entry.titles = json.dumps(merged_titles, ensure_ascii=False)
        changed = True

    tasks = entry.tasks_list()
    if not isinstance(tasks, list):
        tasks = []
        entry.tasks = json.dumps([], ensure_ascii=False)
        changed = True

    reward = entry.reward_dict()
    if 'type' not in reward:
        reward['type'] = DEFAULT_QUEST_REWARD['type']
        changed = True
    if reward['type'] not in {'discount', 'stock'}:
        reward['type'] = 'discount'
        changed = True
    if reward['type'] == 'discount':
        try:
            value = int(reward.get('value', DEFAULT_QUEST_REWARD['value']))
        except (TypeError, ValueError):
            value = DEFAULT_QUEST_REWARD['value']
        value = max(0, min(100, value))
        reward['value'] = value
    else:
        reward['value'] = str(reward.get('value') or '')
    titles_map = reward.get('title')
    if not isinstance(titles_map, dict):
        titles_map = {}
    reward_titles: dict[str, str] = {}
    for language in languages:
        base = DEFAULT_QUEST_REWARD['title'].get(language, DEFAULT_QUEST_REWARD['title']['en'])
        reward_titles[language] = str(titles_map.get(language) or base).strip()
    reward['title'] = reward_titles
    reset_weekday = entry.reset_weekday if entry.reset_weekday is not None else DEFAULT_QUEST_RESET['weekday']
    reset_hour = entry.reset_hour if entry.reset_hour is not None else DEFAULT_QUEST_RESET['hour']
    if reset_weekday < 0 or reset_weekday > 6:
        reset_weekday = DEFAULT_QUEST_RESET['weekday']
    if reset_hour < 0 or reset_hour > 23:
        reset_hour = DEFAULT_QUEST_RESET['hour']
    if entry.reset_weekday != reset_weekday:
        entry.reset_weekday = reset_weekday
        changed = True
    if entry.reset_hour != reset_hour:
        entry.reset_hour = reset_hour
        changed = True
    if changed:
        entry.reward = json.dumps(reward, ensure_ascii=False)
        session.commit()


def _ensure_achievement_defaults() -> None:
    session = Database().session
    existing = {ach.code: ach for ach in session.query(Achievement).all()}
    changed = False
    for code, defaults in DEFAULT_ACHIEVEMENTS.items():
        if code not in existing:
            session.add(Achievement(code=code, config=defaults))
            changed = True
        else:
            entry = existing[code]
            config = entry.config_dict()
            original = dict(config)
            for key, value in defaults.items():
                config.setdefault(key, value)
            if config != original:
                entry.config = json.dumps(config, ensure_ascii=False)
                changed = True
    if changed:
        session.commit()
