import json
from datetime import date
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import AdventSettings, DailyStats, Door, DoorStats


def on(day, month=12, year=2026):
    """Патчва „днес“ (Europe/Sofia) за кода в doors.unlock."""
    return mock.patch("doors.unlock.today_sofia", return_value=date(year, month, day))


class AdventSettingsTests(TestCase):
    def test_load_uses_defaults_and_is_singleton(self):
        cfg = AdventSettings.load()
        self.assertEqual((cfg.last_day, cfg.month, cfg.year), (24, 12, 2026))
        AdventSettings(last_day=25).save()
        self.assertEqual(AdventSettings.objects.count(), 1)
        self.assertEqual(AdventSettings.load().last_day, 25)

    def test_rejects_day_outside_month(self):
        cfg = AdventSettings(last_day=31, month=11, year=2026)
        with self.assertRaises(ValidationError):
            cfg.full_clean()


class DoorValidationTests(TestCase):
    def test_day_must_be_within_last_day(self):
        for day in (0, 25):
            with self.assertRaises(ValidationError):
                Door(day=day, title="x").full_clean()
        Door(day=24, title="x").full_clean()

    def test_last_day_change_allows_day_25(self):
        cfg = AdventSettings.load()
        cfg.last_day = 25
        cfg.save()
        Door(day=25, title="x").full_clean()


class ApiTests(TestCase):
    def setUp(self):
        for day in (1, 2, 3, 24):
            Door.objects.create(day=day, type="riddle", title=f"Тайна {day}", text="текст", answer="отговор", is_published=True)
        Door.objects.create(day=5, title="Скрита", is_published=False)
        self.list_url = reverse("doors:door-list")

    def detail(self, day, **params):
        return self.client.get(reverse("doors:door-detail", args=[day]), params)

    def test_list_contains_only_day_type_unlocked(self):
        with on(2):
            data = self.client.get(self.list_url).json()
        self.assertEqual([d["day"] for d in data["doors"]], [1, 2, 3, 24])
        for door in data["doors"]:
            self.assertEqual(set(door), {"day", "type", "unlocked"})
        self.assertEqual([d["unlocked"] for d in data["doors"]], [True, True, False, False])
        self.assertEqual(data["today"], 2)
        self.assertNotIn("Тайна", self.client.get(self.list_url).content.decode())

    def test_detail_past_door(self):
        with on(2):
            response = self.detail(1)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "Тайна 1")
        self.assertEqual(response.json()["answer"], "отговор")

    def test_detail_future_door_is_forbidden(self):
        with on(2):
            response = self.detail(3)
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("Тайна", response.content.decode())

    def test_before_december_everything_is_locked(self):
        with on(30, month=11):
            self.assertEqual(self.detail(1).status_code, 403)

    def test_unpublished_door_is_404(self):
        with on(31):
            self.assertEqual(self.detail(5).status_code, 404)

    def test_settings_month_controls_unlocking(self):
        cfg = AdventSettings.load()
        cfg.month = 11
        cfg.save()
        with on(2, month=11):
            self.assertEqual(self.detail(2).status_code, 200)
            self.assertEqual(self.detail(3).status_code, 403)

    def test_doors_above_last_day_are_hidden(self):
        cfg = AdventSettings.load()
        cfg.last_day = 3
        cfg.save()
        with on(31):
            days = [d["day"] for d in self.client.get(self.list_url).json()["doors"]]
            self.assertEqual(days, [1, 2, 3])
            self.assertEqual(self.detail(24).status_code, 404)

    @override_settings(DEBUG=True)
    def test_preview_unlocks_in_debug(self):
        with on(1):
            self.assertEqual(self.detail(24, preview=1).status_code, 200)
            data = self.client.get(self.list_url, {"preview": 1}).json()
        self.assertTrue(all(d["unlocked"] for d in data["doors"]))

    @override_settings(DEBUG=False)
    def test_preview_ignored_in_production(self):
        with on(1):
            self.assertEqual(self.detail(24, preview=1).status_code, 403)


class AdminAndSeedTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser("admin", "admin@example.com", "pass")
        self.client.force_login(self.admin)

    def test_generate_empty_doors(self):
        Door.objects.create(day=3, title="Моята", is_published=True)
        url = reverse("admin:doors_door_generate_empty_doors")
        self.client.get(url)
        self.client.get(url)
        self.assertEqual(Door.objects.count(), 24)
        self.assertEqual(Door.objects.get(day=3).title, "Моята")

    def test_settings_changelist_redirects_to_form(self):
        response = self.client.get(reverse("admin:doors_adventsettings_changelist"))
        self.assertRedirects(response, reverse("admin:doors_adventsettings_change", args=[1]))

    def test_seed_doors(self):
        call_command("seed_doors", stdout=mock.MagicMock())
        self.assertEqual(Door.objects.filter(is_published=True).count(), 24)
        self.assertEqual(set(Door.objects.values_list("type", flat=True)), set(Door.Type.values))


class CountdownTests(TestCase):
    def test_countdown_before_start(self):
        with on(1, month=11):
            response = self.client.get(reverse("doors:index"))
        self.assertEqual(response.context["countdown"]["days_left"], 30)
        self.assertContains(response, "Календарът се отваря след")

    def test_no_countdown_once_started(self):
        with on(1):
            response = self.client.get(reverse("doors:index"))
        self.assertIsNone(response.context["countdown"])
        self.assertNotContains(response, "Календарът се отваря след")


class StatsTests(TestCase):
    def setUp(self):
        cache.clear()
        self.challenge = Door.objects.create(day=1, type="challenge", title="Мисия", is_published=True)
        self.joke = Door.objects.create(day=2, type="joke", title="Шега", is_published=True)
        Door.objects.create(day=10, type="wish", title="Бъдеща", is_published=True)

    def react(self, day, **payload):
        return self.client.post(
            reverse("doors:door-react", args=[day]),
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_visit_counts_per_day(self):
        with on(5):
            self.client.post(reverse("doors:visit"))
            self.client.post(reverse("doors:visit"))
        self.assertEqual(DailyStats.objects.get(date=date(2026, 12, 5)).visitors, 2)

    def test_visit_requires_post(self):
        self.assertEqual(self.client.get(reverse("doors:visit")).status_code, 405)

    def test_heart_toggle_and_never_negative(self):
        with on(5):
            self.assertEqual(self.react(2, action="heart").json()["hearts"], 1)
            self.assertEqual(self.react(2, action="heart", active=False).json()["hearts"], 0)
            self.assertEqual(self.react(2, action="heart", active=False).json()["hearts"], 0)
        self.assertEqual(DailyStats.objects.get(date=date(2026, 12, 5)).hearts, 1)

    def test_done_only_for_challenges(self):
        with on(5):
            self.assertEqual(self.react(1, action="done").json()["completions"], 1)
            self.assertEqual(self.react(2, action="done").status_code, 400)

    def test_open_is_counted_and_cannot_be_undone(self):
        with on(5):
            self.react(1, action="open")
            self.assertEqual(self.react(1, action="open", active=False).status_code, 400)
        self.assertEqual(DoorStats.objects.get(door=self.challenge).opens, 1)

    @override_settings(DEBUG=True)
    def test_locked_door_rejects_reactions_even_in_preview(self):
        with on(5):
            response = self.client.post(
                reverse("doors:door-react", args=[10]) + "?preview=1",
                data=json.dumps({"action": "heart"}),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(DoorStats.objects.exists())

    def test_bad_payload(self):
        with on(5):
            self.assertEqual(self.react(2, action="hack").status_code, 400)
            response = self.client.post(
                reverse("doors:door-react", args=[2]), data="не е json", content_type="application/json"
            )
        self.assertEqual(response.status_code, 400)

    def test_detail_includes_counts(self):
        with on(5):
            self.react(1, action="heart")
            data = self.client.get(reverse("doors:door-detail", args=[1])).json()
        self.assertEqual((data["hearts"], data["completions"]), (1, 0))

    def test_rate_limit(self):
        with on(5), mock.patch("doors.stats.RATE_LIMIT", 3):
            codes = [self.client.post(reverse("doors:visit")).status_code for _ in range(5)]
        self.assertEqual(codes, [200, 200, 200, 429, 429])

    def test_admin_stats_pages(self):
        admin = get_user_model().objects.create_superuser("admin", "admin@example.com", "pass")
        self.client.force_login(admin)
        with on(5):
            self.client.post(reverse("doors:visit"))
            self.react(1, action="done")
        for name in ("doors_dailystats_changelist", "doors_doorstats_changelist", "doors_door_changelist"):
            self.assertEqual(self.client.get(reverse(f"admin:{name}")).status_code, 200, name)


class GreetingTests(TestCase):
    def test_default_greeting_uses_next_year(self):
        self.assertEqual(AdventSettings.load().greeting_text, "Весели празници и успешна 2027 година!")
        with on(1):
            self.assertContains(self.client.get(reverse("doors:index")), "успешна 2027 година!")

    def test_custom_greeting(self):
        cfg = AdventSettings.load()
        cfg.greeting = "Честито Рождество!"
        cfg.save()
        with on(1):
            self.assertContains(self.client.get(reverse("doors:index")), "Честито Рождество!")
