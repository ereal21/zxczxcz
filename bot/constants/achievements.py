"""Default achievement configuration used when no overrides are stored."""

from __future__ import annotations

DEFAULT_ACHIEVEMENTS: dict[str, dict[str, object]] = {
    'start': {
        'type': 'builtin',
    },
    'first_purchase': {
        'type': 'builtin',
    },
    'first_topup': {
        'type': 'builtin',
    },
    'first_blackjack': {
        'type': 'builtin',
    },
    'first_coinflip': {
        'type': 'builtin',
    },
    'gift_sent': {
        'type': 'builtin',
    },
    'first_referral': {
        'type': 'builtin',
    },
    'five_purchases': {
        'type': 'builtin',
    },
    'streak_three': {
        'type': 'builtin',
    },
    'ten_referrals': {
        'type': 'builtin',
    },
}

ACHIEVEMENT_TYPES = {'builtin', 'term_purchase'}

__all__ = ['DEFAULT_ACHIEVEMENTS', 'ACHIEVEMENT_TYPES']
