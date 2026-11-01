import calendar

from axes.models import AccessAttempt
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


MONTH_CHOICES = [
    (1, "Януари"),
    (2, "Февруари"),
    (3, "Март"),
    (4, "Април"),
    (5, "Май"),
    (6, "Юни"),
    (7, "Юли"),
    (8, "Август"),
    (9, "Септември"),
    (10, "Октомври"),
    (11, "Ноември"),
    (12, "Декември"),
]


def default_last_day():
    return settings.ADVENT_LAST_DAY


def default_month():
    return settings.ADVENT_MONTH


def default_year():
    return settings.ADVENT_YEAR


class AdventSettings(models.Model):
    """Единичен запис с настройките на календара, редактируем от админа."""

    last_day = models.PositiveSmallIntegerField(
        "последен ден",
        default=default_last_day,
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        help_text="Колко вратички има календарът (обикновено 24 или 25).",
    )
    month = models.PositiveSmallIntegerField(
        "месец",
        choices=MONTH_CHOICES,
        default=default_month,
    )
    year = models.PositiveSmallIntegerField(
        "година",
        default=default_year,
        validators=[MinValueValidator(2000), MaxValueValidator(2100)],
    )
    site_title = models.CharField(
        "заглавие на сайта",
        max_length=100,
        default="Адвент календар",
    )
    subtitle = models.CharField(
        "подзаглавие",
        max_length=200,
        blank=True,
        default="Отваряй по една вратичка всеки ден до Коледа",
    )
    greeting = models.CharField(
        "празнично пожелание",
        max_length=200,
        blank=True,
        help_text="Показва се като панделка под заглавието. Ако е празно: „Весели празници и успешна <следващата> година!“.",
    )
    finished_message = models.CharField(
        "съобщение след края",
        max_length=200,
        default="Календарът приключи – благодарим, че бяхте с нас!",
        help_text="Показва се след последния ден. Вратичките остават отворени.",
    )
    school_name = models.CharField(
        "име на училището",
        max_length=200,
        blank=True,
        default="ПГКНМА „Проф. Минко Балкански“",
    )
    school_city = models.CharField(
        "град",
        max_length=100,
        blank=True,
        default="Стара Загора",
    )
    school_url = models.URLField(
        "сайт на училището",
        blank=True,
        default="https://pgknma.com/",
    )
    logo = models.ImageField(
        "лого",
        upload_to="branding/",
        blank=True,
        help_text="По избор. Ако е празно, се използва логото на ПГКНМА от static/img/.",
    )

    class Meta:
        verbose_name = "настройки на календара"
        verbose_name_plural = "настройки на календара"

    def __str__(self):
        return f"{self.site_title}: 1–{self.last_day} {self.get_month_display().lower()} {self.year}"

    def clean(self):
        super().clean()
        if self.month and self.year and self.last_day:
            days_in_month = calendar.monthrange(self.year, self.month)[1]
            if self.last_day > days_in_month:
                raise ValidationError(
                    {"last_day": f"Избраният месец има само {days_in_month} дни."}
                )

    @property
    def greeting_text(self):
        return self.greeting or f"Весели празници и успешна {self.year + 1} година!"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Door(models.Model):
    class Type(models.TextChoices):
        WISH = "wish", "Пожелание"
        CHALLENGE = "challenge", "Предизвикателство"
        RIDDLE = "riddle", "Гатанка"
        QUOTE = "quote", "Цитат"
        JOKE = "joke", "Шега"
        FACT = "fact", "Интересен факт"
        PHOTO = "photo", "Снимка"

    day = models.PositiveSmallIntegerField(
        "ден",
        unique=True,
        validators=[MinValueValidator(1)],
    )
    type = models.CharField(
        "тип",
        max_length=20,
        choices=Type.choices,
        default=Type.WISH,
    )
    title = models.CharField("заглавие", max_length=200)
    text = models.TextField("текст", blank=True)
    image = models.ImageField(
        "снимка",
        upload_to="doors/",
        blank=True,
        help_text="По избор. Препоръчително за тип „Снимка“.",
    )
    answer = models.CharField(
        "отговор",
        max_length=300,
        blank=True,
        help_text="Показва се с бутон „Покажи отговора“ (за гатанки).",
    )
    is_published = models.BooleanField("публикувана", default=False)

    class Meta:
        ordering = ["day"]
        verbose_name = "вратичка"
        verbose_name_plural = "вратички"

    def __str__(self):
        return f"Ден {self.day}: {self.title}"

    def clean(self):
        super().clean()
        if self.day is not None:
            last_day = AdventSettings.load().last_day
            if self.day > last_day:
                raise ValidationError(
                    {"day": f"Денят трябва да е между 1 и {last_day} (виж „Настройки на календара“)."}
                )


# Статистика. Пазят се само общи броячи: без IP адреси, бисквитки или други лични данни.
# Броячите са в отделни таблици, за да не ги презапише записът на вратичка от админа.

class DoorStats(models.Model):
    door = models.OneToOneField(
        Door,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="stats",
        verbose_name="вратичка",
    )
    opens = models.PositiveIntegerField("отваряния", default=0)
    hearts = models.PositiveIntegerField("сърца", default=0)
    completions = models.PositiveIntegerField("изпълнени предизвикателства", default=0)

    class Meta:
        ordering = ["door__day"]
        verbose_name = "статистика на вратичка"
        verbose_name_plural = "статистика по вратички"

    def __str__(self):
        return str(self.door)


class DailyStats(models.Model):
    date = models.DateField("дата", primary_key=True)
    visitors = models.PositiveIntegerField("посетители", default=0)
    opens = models.PositiveIntegerField("отворени вратички", default=0)
    hearts = models.PositiveIntegerField("сърца", default=0)
    completions = models.PositiveIntegerField("изпълнени предизвикателства", default=0)

    class Meta:
        ordering = ["-date"]
        verbose_name = "статистика за ден"
        verbose_name_plural = "статистика по дни"

    def __str__(self):
        return self.date.strftime("%d.%m.%Y")


class LoginAttempt(AccessAttempt):
    """Неуспешни опити за вход в админа (django-axes), с български имена за админ панела."""

    class Meta:
        proxy = True
        verbose_name = "опит за вход с грешна парола"
        verbose_name_plural = "опити за вход с грешна парола"
