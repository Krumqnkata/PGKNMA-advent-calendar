"""
Настройки на проекта „Адвент календар“.

Чувствителните стойности (SECRET_KEY, DEBUG, данни за базата) идват от
environment променливи. Ако в корена на проекта има файл .env, той се зарежда
автоматично (удобно и за локална разработка, и под Apache + mod_wsgi).
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.templatetags.static import static
from django.urls import reverse_lazy
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


DEBUG = env_bool("DEBUG", False)

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "django-insecure-local-dev-only-change-me"
    else:
        raise ImproperlyConfigured("Задай environment променливата SECRET_KEY.")

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")


# Приложения

INSTALLED_APPS = [
    "unfold",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "doors",
    "axes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Трябва да е последен: блокира входа след твърде много грешни пароли.
    "axes.middleware.AxesMiddleware",
]

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]


# Админ панел: адресът не е стандартният /admin/, за да не е лесна мишена.
# В продукция задай свой, трудно отгатваем адрес в ADMIN_URL (напр. upravlenie-k7x2/).

ADMIN_URL = os.environ.get("ADMIN_URL", "upravlenie/").strip("/") + "/"


# Ограничение на опитите за вход (django-axes): 5 грешни пароли за едно и също
# потребителско име от един и същ IP адрес → блокиране за 1 час. Пазят се само
# неуспешните опити и само докато изтече блокирането; пълният дневник е изключен.

AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # часа
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True
AXES_USE_ATTEMPT_EXPIRATION = True
AXES_DISABLE_ACCESS_LOG = True
AXES_ENABLE_ADMIN = False  # регистрираме го сами, в стила на Unfold
AXES_LOCKOUT_TEMPLATE = "doors/locked_out.html"

ROOT_URLCONF = "advent.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "advent.wsgi.application"


# База данни: MySQL. DB_ENGINE=sqlite е само за бърз локален тест.

if os.environ.get("DB_ENGINE", "mysql").lower() == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.environ.get("DB_NAME", "advent"),
            "USER": os.environ.get("DB_USER", "advent"),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
            "PORT": os.environ.get("DB_PORT", "3306"),
            "OPTIONS": {
                "charset": "utf8mb4",
                "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            },
            "TEST": {
                "CHARSET": "utf8mb4",
                "COLLATION": "utf8mb4_unicode_ci",
            },
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Език и време

LANGUAGE_CODE = "bg"
LANGUAGES = [("bg", "Български")]
TIME_ZONE = "Europe/Sofia"
USE_I18N = True
USE_TZ = True


# Статични файлове и качени снимки

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024


# Сигурност в продукция

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = env_bool("SECURE_COOKIES", True)
    CSRF_COOKIE_SECURE = env_bool("SECURE_COOKIES", True)
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"


# Адвент календар: стойности по подразбиране.
# Реалните стойности се редактират от админ панела („Настройки на календара“);
# тези тук се използват само при първото създаване на записа.

ADVENT_LAST_DAY = 24
ADVENT_MONTH = 12
ADVENT_YEAR = 2026
ADVENT_TIME_ZONE = "Europe/Sofia"

# Връзка към изходния код в долната част на сайта (AGPL-3.0, раздел 13).
SOURCE_CODE_URL = os.environ.get("SOURCE_CODE_URL", "https://github.com/Krumqnkata/PGKNMA-advent-calendar")


# Админ панел (django-unfold)

UNFOLD = {
    "SITE_TITLE": "Адвент календар",
    "SITE_HEADER": "Адвент календар",
    "SITE_SUBHEADER": "ПГКНМА „Проф. Минко Балкански“",
    "SITE_ICON": lambda request: static("img/pgknma-logo.svg"),
    "SITE_URL": "/",
    "SITE_FAVICONS": [
        {
            "rel": "icon",
            "type": "image/png",
            "href": lambda request: static("img/pgknma-logo.png"),
        },
    ],
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    # Цветовете на ПГКНМА (#4fa392 / #27665a)
    "COLORS": {
        "primary": {
            "50": "240 250 247",
            "100": "214 241 234",
            "200": "174 226 214",
            "300": "128 205 189",
            "400": "95 184 166",
            "500": "79 163 146",
            "600": "58 135 120",
            "700": "39 102 90",
            "800": "31 82 73",
            "900": "26 66 59",
            "950": "13 40 36",
        },
    },
    "SIDEBAR": {
        "show_search": False,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Адвент календар",
                "separator": False,
                "items": [
                    {
                        "title": "Вратички",
                        "icon": "door_front",
                        "link": reverse_lazy("admin:doors_door_changelist"),
                    },
                    {
                        "title": "Настройки на календара",
                        "icon": "settings",
                        "link": reverse_lazy("admin:doors_adventsettings_changelist"),
                    },
                ],
            },
            {
                "title": "Статистика",
                "separator": True,
                "items": [
                    {
                        "title": "По дни",
                        "icon": "bar_chart",
                        "link": reverse_lazy("admin:doors_dailystats_changelist"),
                    },
                    {
                        "title": "По вратички",
                        "icon": "favorite",
                        "link": reverse_lazy("admin:doors_doorstats_changelist"),
                    },
                ],
            },
            {
                "title": "Потребители",
                "separator": True,
                "items": [
                    {
                        "title": "Потребители",
                        "icon": "person",
                        "link": reverse_lazy("admin:auth_user_changelist"),
                    },
                    {
                        "title": "Групи",
                        "icon": "group",
                        "link": reverse_lazy("admin:auth_group_changelist"),
                    },
                    {
                        "title": "Грешни опити за вход",
                        "icon": "lock",
                        "link": reverse_lazy("admin:doors_loginattempt_changelist"),
                    },
                ],
            },
        ],
    },
}
