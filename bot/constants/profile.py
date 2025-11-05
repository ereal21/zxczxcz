"""Default configuration for profile-related features."""

DEFAULT_PROFILE_SETTINGS: dict[str, object] = {
    'profile_enabled': True,
    'blackjack_enabled': True,
    'blackjack_max_bet': 5,
    'quests_enabled': True,
    'quests_description': '',
    'missions_enabled': False,
    'missions_description': '',
}

PROFILE_BOOLEAN_FIELDS = {
    'profile_enabled',
    'blackjack_enabled',
    'quests_enabled',
    'missions_enabled',
}

PROFILE_TEXT_FIELDS = {
    'quests_description',
    'missions_description',
}

PROFILE_NUMERIC_FIELDS = {
    'blackjack_max_bet',
}
