"""Default loyalty level configuration."""

DEFAULT_LEVEL_THRESHOLDS = [0, 1, 5, 15, 30, 50]

DEFAULT_LEVEL_NAMES = {
    'lt': [
        '😶‍🌫️ Niekšas',
        '👏 Fanas',
        '🎛️ Prodiuseris',
        '🛹 Mobo narys',
        '🧠 Mobo lyderis',
        '🎤 Reperis',
    ],
    'en': [
        '😶‍🌫️ Scoundrel',
        '👏 Fan',
        '🎛️ Producer',
        '🛹 Crew member',
        '🧠 Crew leader',
        '🎤 Rapper',
    ],
    'ru': [
        '😶‍🌫️ Негодяй',
        '👏 Фанат',
        '🎛️ Продюсер',
        '🛹 Участник банды',
        '🧠 Лидер банды',
        '🎤 Рэпер',
    ],
}

__all__ = ['DEFAULT_LEVEL_THRESHOLDS', 'DEFAULT_LEVEL_NAMES']
