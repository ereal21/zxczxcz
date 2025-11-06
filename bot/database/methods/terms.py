"""Database helpers for managing product terms (hashtags)."""

from __future__ import annotations

import datetime
import json
import re

from sqlalchemy import func

from bot.database import Database
from bot.database.models import Goods, Term, BoughtGoods

__all__ = [
    'normalise_term_code',
    'list_terms',
    'get_term',
    'create_or_update_term',
    'delete_term',
    'assign_term_to_item',
    'term_usage_stats',
]

_TERM_PATTERN = re.compile(r'[^A-Z0-9_]')


def normalise_term_code(raw: str) -> str:
    if not raw:
        return ''
    code = raw.strip().upper()
    code = code.replace(' ', '_')
    code = _TERM_PATTERN.sub('', code)
    return code


def _normalise_labels(labels: dict[str, str] | None) -> dict[str, str]:
    cleaned: dict[str, str] = {}
    if not isinstance(labels, dict):
        return cleaned
    for language, value in labels.items():
        if not language:
            continue
        cleaned[str(language).strip()] = str(value or '').strip()
    return cleaned


def list_terms() -> list[dict]:
    session = Database().session
    rows = session.query(Term).order_by(Term.code.asc()).all()
    results: list[dict] = []
    for row in rows:
        results.append({
            'code': row.code,
            'labels': row.labels_dict(),
            'created_at': row.created_at,
        })
    return results


def get_term(code: str) -> dict | None:
    if not code:
        return None
    session = Database().session
    row = session.query(Term).filter(Term.code == code).first()
    if not row:
        return None
    return {
        'code': row.code,
        'labels': row.labels_dict(),
        'created_at': row.created_at,
    }


def create_or_update_term(code: str, labels: dict[str, str]) -> dict:
    session = Database().session
    normalised = normalise_term_code(code)
    if not normalised:
        raise ValueError('Invalid term code')
    row = session.query(Term).filter(Term.code == normalised).first()
    timestamp = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    cleaned_labels = _normalise_labels(labels)
    if row is None:
        row = Term(code=normalised, labels=cleaned_labels, created_at=timestamp)
        session.add(row)
    else:
        row.labels = json.dumps(cleaned_labels, ensure_ascii=False)
    session.commit()
    session.refresh(row)
    return {
        'code': row.code,
        'labels': row.labels_dict(),
        'created_at': row.created_at,
    }


def delete_term(code: str) -> bool:
    session = Database().session
    row = session.query(Term).filter(Term.code == code).first()
    if not row:
        return False
    in_use = session.query(Goods).filter(Goods.term_code == code).first() is not None
    if in_use:
        raise ValueError('Term is used by products')
    session.delete(row)
    session.commit()
    return True


def assign_term_to_item(item_name: str, term_code: str | None) -> None:
    session = Database().session
    item = session.query(Goods).filter(Goods.name == item_name).first()
    if item is None:
        raise ValueError('Item not found')
    if term_code:
        normalised = normalise_term_code(term_code)
        if not normalised:
            raise ValueError('Invalid term code')
        term = session.query(Term).filter(Term.code == normalised).first()
        if term is None:
            raise ValueError('Term does not exist')
        item.term_code = normalised
    else:
        item.term_code = None
    session.commit()


def term_usage_stats(code: str) -> dict:
    session = Database().session
    total_goods = session.query(func.count(Goods.name)).filter(Goods.term_code == code).scalar() or 0
    total_sales = session.query(func.count(BoughtGoods.id)).filter(BoughtGoods.term_code == code).scalar() or 0
    return {
        'code': code,
        'products': int(total_goods),
        'sales': int(total_sales),
    }
