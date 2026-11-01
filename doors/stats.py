"""Анонимни броячи: посещения по дни, отваряния, сърца и изпълнени предизвикателства.

Не се пазят IP адреси, бисквитки или идентификатори. IP адресът се ползва само за
кратко ограничение на заявките и само като хеш в кеша (изтрива се след минута).
"""

import hashlib

from django.conf import settings
from django.core.cache import cache
from django.db.models import F

from . import unlock
from .models import DailyStats, DoorStats

ACTIONS = {"open": "opens", "heart": "hearts", "done": "completions"}

RATE_LIMIT = 60  # заявки
RATE_WINDOW = 60  # секунди


def _bump(model, field, delta, **lookup):
    obj, _ = model.objects.get_or_create(**lookup)
    rows = model.objects.filter(pk=obj.pk)
    if delta > 0:
        rows.update(**{field: F(field) + delta})
    else:
        # Без отрицателни стойности (колоните в MySQL са UNSIGNED).
        rows.filter(**{f"{field}__gt": 0}).update(**{field: F(field) - 1})


def record_visit():
    _bump(DailyStats, "visitors", 1, date=unlock.today_sofia())


def record_reaction(door, year, action, active=True):
    field = ACTIONS[action]
    _bump(DoorStats, field, 1 if active else -1, door=door, year=year)
    # Дневната статистика брои само действията, не и отмяната им.
    if active:
        _bump(DailyStats, field, 1, date=unlock.today_sofia())


def door_counts(door, year):
    counts = DoorStats.objects.filter(door=door, year=year).values("hearts", "completions").first()
    return counts or {"hearts": 0, "completions": 0}


def rate_limited(request):
    ip = request.META.get("REMOTE_ADDR", "")
    digest = hashlib.sha256(f"{settings.SECRET_KEY}:{ip}".encode()).hexdigest()[:32]
    key = f"advent-rate:{digest}"
    if cache.add(key, 1, RATE_WINDOW):
        return False
    try:
        return cache.incr(key) > RATE_LIMIT
    except ValueError:  # ключът е изтекъл междувременно
        cache.set(key, 1, RATE_WINDOW)
        return False
