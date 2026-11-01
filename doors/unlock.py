"""Единственото място с логиката кога една вратичка е отключена."""

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone


def today_sofia():
    return timezone.localdate(timezone.now(), ZoneInfo(settings.ADVENT_TIME_ZONE))


def door_date(day, cfg):
    return date(cfg.year, cfg.month, day)


def calendar_start(cfg):
    """Моментът, в който се отключва първата вратичка (полунощ в София)."""
    return datetime.combine(door_date(1, cfg), time.min, tzinfo=ZoneInfo(settings.ADVENT_TIME_ZONE))


def is_unlocked(day, cfg, today=None):
    today = today or today_sofia()
    return door_date(day, cfg) <= today


def today_door_day(cfg, today=None):
    """Номерът на днешната вратичка или None, ако днес не е ден от календара."""
    today = today or today_sofia()
    if today.year == cfg.year and today.month == cfg.month and today.day <= cfg.last_day:
        return today.day
    return None


def preview_enabled(request):
    """Тестов режим: ?preview=1 отключва всичко, но само при DEBUG=True."""
    return settings.DEBUG and request.GET.get("preview") == "1"
