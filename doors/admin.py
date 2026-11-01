from django.contrib import admin, messages
from django.db.models import F, Max, Value, Window
from django.db.models.functions import Coalesce
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.functional import lazy
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import action, display

from .models import AdventSettings, DailyStats, Door, DoorStats


@admin.register(AdventSettings)
class AdventSettingsAdmin(ModelAdmin):
    fieldsets = (
        (
            "Период",
            {
                "fields": ("last_day", "month", "year"),
                "description": "Вратичка N се отключва на N-ия ден от избрания месец (часова зона Europe/Sofia).",
            },
        ),
        ("Текстове на сайта", {"fields": ("site_title", "subtitle", "greeting")}),
        ("Училище", {"fields": ("school_name", "school_city", "school_url", "logo")}),
    )

    def has_add_permission(self, request):
        return not AdventSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # Има само един запис, затова списъкът води направо към формата му.
        obj = AdventSettings.load()
        return redirect(reverse("admin:doors_adventsettings_change", args=[obj.pk]))


@admin.register(Door)
class DoorAdmin(ModelAdmin):
    list_display = (
        "day",
        "type_badge",
        "title",
        "thumbnail",
        "opens_count",
        "hearts_count",
        "completions_count",
        "is_published",
    )
    list_display_links = ("day", "title")
    list_editable = ("is_published",)
    list_filter = ("type", "is_published")
    search_fields = ("title", "text", "answer")
    ordering = ("day",)
    list_per_page = 50
    actions = ["publish", "unpublish"]
    actions_list = ["generate_empty_doors"]
    readonly_fields = ("image_preview",)
    fieldsets = (
        ("Основно", {"fields": ("day", "type", "is_published")}),
        ("Съдържание", {"fields": ("title", "text", "image", "image_preview")}),
        (
            "Гатанка",
            {
                "fields": ("answer",),
                "description": "Отговорът се показва само при тип „Гатанка“, след бутона „Покажи отговора“.",
            },
        ),
    )

    @display(
        description="тип",
        ordering="type",
        label={
            Door.Type.WISH: "danger",
            Door.Type.CHALLENGE: "warning",
            Door.Type.RIDDLE: "info",
            Door.Type.QUOTE: "primary",
            Door.Type.JOKE: "success",
            Door.Type.FACT: "info",
            Door.Type.PHOTO: "primary",
        },
    )
    def type_badge(self, obj):
        return obj.type, obj.get_type_display()

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            stat_opens=Coalesce(F("stats__opens"), Value(0)),
            stat_hearts=Coalesce(F("stats__hearts"), Value(0)),
            stat_completions=Coalesce(F("stats__completions"), Value(0)),
        )

    @display(description="отваряния", ordering="stat_opens")
    def opens_count(self, obj):
        return obj.stat_opens

    @display(description="❤", ordering="stat_hearts")
    def hearts_count(self, obj):
        return obj.stat_hearts

    @display(description="изпълнени", ordering="stat_completions")
    def completions_count(self, obj):
        return obj.stat_completions if obj.type == Door.Type.CHALLENGE else "—"

    @display(description="снимка")
    def thumbnail(self, obj):
        if not obj.image:
            return "—"
        return format_html(
            '<img src="{}" alt="" style="height:40px;width:40px;object-fit:cover;border-radius:6px">',
            obj.image.url,
        )

    @display(description="преглед")
    def image_preview(self, obj):
        if not obj or not obj.image:
            return "Няма качена снимка."
        return format_html(
            '<img src="{}" alt="" style="max-height:240px;max-width:100%;border-radius:8px">',
            obj.image.url,
        )

    @admin.action(description="Публикувай избраните")
    def publish(self, request, queryset):
        count = queryset.update(is_published=True)
        self.message_user(request, f"Публикувани вратички: {count}.", messages.SUCCESS)

    @admin.action(description="Скрий избраните")
    def unpublish(self, request, queryset):
        count = queryset.update(is_published=False)
        self.message_user(request, f"Скрити вратички: {count}.", messages.SUCCESS)

    @action(
        description=lazy(lambda: f"Генерирай празни врати 1-{AdventSettings.load().last_day}", str)(),
        url_path="generate-empty-doors",
        icon="auto_awesome",
        permissions=["add"],
    )
    def generate_empty_doors(self, request):
        last_day = AdventSettings.load().last_day
        created = 0
        for day in range(1, last_day + 1):
            _, was_created = Door.objects.get_or_create(
                day=day,
                defaults={"title": f"Ден {day}", "is_published": False},
            )
            created += was_created
        if created:
            self.message_user(
                request,
                f"Създадени са {created} празни вратички (1–{last_day}). Не са публикувани.",
                messages.SUCCESS,
            )
        else:
            self.message_user(request, f"Всички вратички 1–{last_day} вече съществуват.", messages.INFO)
        return redirect(reverse("admin:doors_door_changelist"))


class ReadOnlyStatsAdmin(ModelAdmin):
    """Статистиката само се разглежда; изтриването е позволено (напр. след тестове)."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(DailyStats)
class DailyStatsAdmin(ReadOnlyStatsAdmin):
    list_display = ("date", "visitors_bar", "opens", "hearts", "completions")
    date_hierarchy = "date"
    list_per_page = 60

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(max_visitors=Window(Max("visitors")))

    @display(description="посетители", ordering="visitors")
    def visitors_bar(self, obj):
        width = round(100 * obj.visitors / obj.max_visitors) if obj.max_visitors else 0
        return format_html(
            '<div style="display:flex;align-items:center;gap:10px;min-width:180px">'
            '<span style="min-width:2.5em;font-weight:600">{}</span>'
            '<span style="flex:1;height:8px;border-radius:4px;background:rgba(79,163,146,.15)">'
            '<span style="display:block;width:{}%;height:100%;border-radius:4px;background:#4fa392"></span>'
            "</span></div>",
            obj.visitors,
            width,
        )


@admin.register(DoorStats)
class DoorStatsAdmin(ReadOnlyStatsAdmin):
    list_display = ("day", "door_title", "door_type", "opens", "hearts", "completions")
    list_select_related = ("door",)
    ordering = ("door__day",)

    @display(description="ден", ordering="door__day")
    def day(self, obj):
        return obj.door.day

    @display(description="заглавие", ordering="door__title")
    def door_title(self, obj):
        return obj.door.title

    @display(description="тип", ordering="door__type")
    def door_type(self, obj):
        return obj.door.get_type_display()
