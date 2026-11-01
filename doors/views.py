import json
from datetime import date
from urllib.parse import urlparse

from django.conf import settings
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from . import stats, unlock
from .models import AdventSettings, Door


def get_published_door(cfg, day):
    try:
        return Door.objects.get(day=day, is_published=True, day__lte=cfg.last_day)
    except Door.DoesNotExist:
        raise Http404("Няма такава вратичка.")


def countdown(cfg, today):
    """Обратно броене до първата вратичка или None, ако календарът вече е започнал."""
    start = unlock.calendar_start(cfg)
    if today >= start.date():
        return None
    now = timezone.now()
    seconds = max(0, int((start - now).total_seconds()))
    days, rest = divmod(seconds, 86400)
    hours, rest = divmod(rest, 3600)
    minutes, secs = divmod(rest, 60)
    return {
        "days_left": (start.date() - today).days,
        "start": start,
        "start_iso": start.isoformat(),
        "now_iso": now.isoformat(),
        "parts": {"days": days, "hours": hours, "minutes": minutes, "seconds": secs},
    }


@require_GET
def index(request):
    cfg = AdventSettings.load()
    today = unlock.today_sofia()
    context = {
        "cfg": cfg,
        "today_iso": today.isoformat(),
        "today_day": unlock.today_door_day(cfg, today),
        "days_to_christmas": (date(cfg.year, 12, 25) - today).days,
        "countdown": countdown(cfg, today),
        "finished": unlock.is_finished(cfg, today),
        "logo_url": cfg.logo.url if cfg.logo else static("img/pgknma-logo.svg"),
        "school_host": urlparse(cfg.school_url).netloc.removeprefix("www."),
        "preview": unlock.preview_enabled(request),
        "source_code_url": settings.SOURCE_CODE_URL,
    }
    return render(request, "doors/index.html", context)


@require_GET
@never_cache
def door_list(request):
    cfg = AdventSettings.load()
    preview = unlock.preview_enabled(request)
    today = unlock.today_sofia()
    doors = Door.objects.filter(is_published=True, day__lte=cfg.last_day).values("day", "type")
    data = [
        {
            "day": door["day"],
            "type": door["type"],
            "unlocked": preview or unlock.is_unlocked(door["day"], cfg, today),
        }
        for door in doors
    ]
    return JsonResponse(
        {
            "last_day": cfg.last_day,
            "today": unlock.today_door_day(cfg, today),
            "doors": data,
        }
    )


@require_GET
@never_cache
def door_detail(request, day):
    cfg = AdventSettings.load()
    door = get_published_door(cfg, day)

    if not (unlock.preview_enabled(request) or unlock.is_unlocked(door.day, cfg)):
        return JsonResponse({"detail": "Още не е време!"}, status=403)

    return JsonResponse(
        {
            "day": door.day,
            "type": door.type,
            "type_label": door.get_type_display(),
            "title": door.title,
            "text": door.text,
            "image": request.build_absolute_uri(door.image.url) if door.image else None,
            "answer": door.answer or None,
            **stats.door_counts(door, cfg.year),
        }
    )


# Броячите са анонимни и не ползват сесии, затова са без CSRF токен и без бисквитки.

@csrf_exempt
@require_POST
def visit(request):
    if stats.rate_limited(request):
        return JsonResponse({"detail": "Твърде много заявки."}, status=429)
    stats.record_visit()
    return JsonResponse({"ok": True})


@csrf_exempt
@require_POST
def door_react(request, day):
    if stats.rate_limited(request):
        return JsonResponse({"detail": "Твърде много заявки."}, status=429)

    cfg = AdventSettings.load()
    door = get_published_door(cfg, day)
    # Тестовият режим нарочно не важи тук: реакции само за наистина отключени вратички.
    if not unlock.is_unlocked(door.day, cfg):
        return JsonResponse({"detail": "Още не е време!"}, status=403)

    try:
        payload = json.loads(request.body or b"{}")
    except ValueError:
        return JsonResponse({"detail": "Невалидни данни."}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({"detail": "Невалидни данни."}, status=400)

    action = payload.get("action")
    active = payload.get("active", True) is not False
    if action not in stats.ACTIONS:
        return JsonResponse({"detail": "Непознато действие."}, status=400)
    if action == "done" and door.type != Door.Type.CHALLENGE:
        return JsonResponse({"detail": "Само предизвикателствата се отбелязват като изпълнени."}, status=400)
    if action == "open" and not active:
        return JsonResponse({"detail": "Отварянето не може да се отмени."}, status=400)

    stats.record_reaction(door, cfg.year, action, active)
    return JsonResponse(stats.door_counts(door, cfg.year))
