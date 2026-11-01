# Адвент календар

[![Тестове](https://github.com/Krumqnkata/PGKNMA-advent-calendar/actions/workflows/tests.yml/badge.svg)](https://github.com/Krumqnkata/PGKNMA-advent-calendar/actions/workflows/tests.yml)

Уеб сайт с вратички, които се отварят по една на ден до Коледа, направен за
ПГКНМА „Проф. Минко Балкански“ – Стара Загора.
Django 5 + django-unfold (админ) + MySQL, фронтенд с чист HTML/CSS/JS (без build стъпка).

Кодът е под лиценз [GNU AGPL-3.0](LICENSE) – виж раздел [Лиценз](#лиценз).

## Какво има

- **Решетка от вратички** с 3D отваряне, модален прозорец, свой цвят/икона/стил за всеки тип:
  пожелание, предизвикателство, гатанка (с бутон „Покажи отговора“), цитат, шега, интересен факт, снимка.
- Вратичка N се отключва на N-ия ден от избрания месец по часова зона **Europe/Sofia**.
  Съдържанието на бъдещите вратички **никога** не се изпраща към браузъра (API връща 403).
- Без акаунти: отворените вратички се пазят в `localStorage`.
- Днешната вратичка свети; заключената се разклаща с „Още не е време!“.
- Сняг на canvas (бутон за изключване, спазва `prefers-reduced-motion`) и бутон за музика.
- **Съобщение след края**: след последния ден над вратичките излиза „Календарът приключи –
  благодарим, че бяхте с нас!“ (текстът се сменя от настройките); всички вратички остават отворени.
- **Админ панел** (`/upravlenie/` по подразбиране – виж „Сигурност на админа“):
  - *Вратички*: списък с филтри и търсене, редакция на цялото съдържание, качване на снимки,
    бутон „Генерирай празни врати 1-24“, масово публикуване/скриване.
  - *Настройки на календара*: последен ден (24/25…), месец, година, заглавие и подзаглавие на сайта,
    име, град и сайт на училището и лого (ако не е качено, се ползва `static/img/pgknma-logo.svg`).
    Стойностите `ADVENT_LAST_DAY`, `ADVENT_MONTH`, `ADVENT_YEAR` в `advent/settings.py`
    са само началните стойности при първото създаване на настройките.

- **Обратно броене**: преди първия ден страницата показва „Календарът се отваря след N дни“
  с часовник (дни/часове/минути/секунди) по часа на сървъра; в 00:00 страницата се презарежда сама.
- **Реакции**: ❤ за всяка вратичка и „Изпълних предизвикателството!“ за предизвикателствата.
- **Анонимна статистика** в админа („Статистика → По дни / По вратички“, плюс колони в списъка
  с вратички): посетители на ден, отваряния, сърца, изпълнени предизвикателства.
  Броячите на вратичките са отделни за всяка година на календара, а браузърът пази
  отворените/харесаните вратички също по години (`advent-2026-opened` и т.н.), така че нищо
  не се пренася, когато смениш годината в настройките.
  Не се пазят IP адреси, бисквитки или идентификатори. Браузърът помни в `localStorage`
  дали вече е отчел посещение/отваряне, а сървърът пази само общи броячи. IP адресът се ползва
  единствено като хеш в паметта за ограничение до 60 заявки/минута и се забравя след минута.

## API

| Метод | Адрес | Отговор |
|---|---|---|
| GET | `/api/doors/` | `{last_day, today, doors: [{day, type, unlocked}]}` – само публикуваните вратички, без съдържание |
| GET | `/api/doors/<day>/` | `{day, type, type_label, title, text, image, answer, hearts, completions}` ако денят е настъпил; иначе **403**, а за липсваща/непубликувана – 404 |
| POST | `/api/doors/<day>/react/` | тяло `{"action": "open" \| "heart" \| "done", "active": true/false}` → `{hearts, completions}`; само за отключени вратички (тестовият режим не важи) |
| POST | `/api/visit/` | отчита едно посещение за днешния ден |

**Тестов режим:** при `DEBUG=True` добави `?preview=1` към адреса (напр. `http://127.0.0.1:8000/?preview=1`)
и всички вратички се отключват. При `DEBUG=False` параметърът се игнорира.

## Локално пускане (Windows / PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # и попълни стойностите
```

Създай MySQL база (в `mysql` клиента):

```sql
CREATE DATABASE advent CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'advent'@'localhost' IDENTIFIED BY 'силна-парола';
GRANT ALL PRIVILEGES ON advent.* TO 'advent'@'localhost';
-- за `manage.py test` върху MySQL потребителят трябва да може да създава база test_advent:
GRANT ALL PRIVILEGES ON test_advent.* TO 'advent'@'localhost';
```

После:

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_doors          # 24 примерни вратички (--force презаписва)
python manage.py runserver
```

- Сайт: http://127.0.0.1:8000/ (тест: http://127.0.0.1:8000/?preview=1)
- Админ: http://127.0.0.1:8000/upravlenie/ (или адресът от `ADMIN_URL`)

## Сигурност на админа

- **Адрес**: админът не е на стандартния `/admin/` (там връща 404), а на `/upravlenie/`.
  В продукция задай свой, трудно отгатваем адрес в `.env`, напр. `ADMIN_URL=upravlenie-k7x2/`.
- **Ограничение на опитите за вход** (django-axes): след 5 грешни пароли за едно потребителско
  име от един IP адрес входът се блокира за 1 час (страница „Входът е временно блокиран“).
  Блокираните опити се виждат в админа („Потребители → Грешни опити за вход“); изтриването на
  запис отключва входа веднага. От командния ред: `python manage.py axes_reset`.
  Пазят се само неуспешните опити и само докато изтече блокирането.
  Ако сайтът е зад reverse proxy (напр. Cloudflare или nginx пред Apache), настрой
  `AXES_IPWARE_PROXY_COUNT` / `AXES_IPWARE_META_PRECEDENCE_ORDER`, за да се вижда истинският IP адрес.

Без MySQL (само за бърз опит): сложи `DB_ENGINE=sqlite` в `.env`.

Тестове: `python manage.py test doors`

## Музика

`static/music/theme.mp3` е **празен placeholder**. Замени го с MP3 файл със **свободен лиценз
(без авторски права или с лиценз, който позволява използване)**, например от:

- Pixabay Music – https://pixabay.com/music/search/christmas/
- Incompetech (Kevin MacLeod, CC BY – изисква се посочване на автора) – https://incompetech.com/

Запази файла със същото име `theme.mp3`. Браузърите блокират автоматичното пускане на звук,
затова музиката тръгва само след натискане на бутона „Музика“; изборът се помни в `localStorage`.

## Deploy на Apache + mod_wsgi (Linux)

1. Качи проекта, напр. в `/var/www/advent`, и създай виртуална среда:

   ```bash
   cd /var/www/advent
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   sudo apt install libapache2-mod-wsgi-py3   # ако още не е инсталиран
   ```

   За `mysqlclient` на Debian/Ubuntu: `sudo apt install python3-dev default-libmysqlclient-dev build-essential pkg-config`.

2. Създай `/var/www/advent/.env`:

   ```ini
   SECRET_KEY=<дълъг-случаен-ключ>
   DEBUG=False
   ALLOWED_HOSTS=advent.example.bg
   CSRF_TRUSTED_ORIGINS=https://advent.example.bg
   DB_NAME=advent
   DB_USER=advent
   DB_PASSWORD=...
   DB_HOST=127.0.0.1
   ```

   Ако сайтът е без HTTPS, добави `SECURE_COOKIES=False`, иначе входът в админа няма да работи.

3. Миграции, статични файлове и права:

   ```bash
   .venv/bin/python manage.py migrate
   .venv/bin/python manage.py collectstatic --noinput
   .venv/bin/python manage.py createsuperuser
   .venv/bin/python manage.py seed_doors
   sudo chown -R www-data:www-data media
   sudo chmod 640 .env && sudo chown root:www-data .env
   ```

4. Виртуален хост `/etc/apache2/sites-available/advent.conf`:

   ```apache
   <VirtualHost *:80>
       ServerName advent.example.bg

       WSGIDaemonProcess advent python-home=/var/www/advent/.venv python-path=/var/www/advent
       WSGIProcessGroup advent
       WSGIScriptAlias / /var/www/advent/advent/wsgi.py

       <Directory /var/www/advent/advent>
           <Files wsgi.py>
               Require all granted
           </Files>
       </Directory>

       Alias /static/ /var/www/advent/staticfiles/
       <Directory /var/www/advent/staticfiles>
           Require all granted
       </Directory>

       Alias /media/ /var/www/advent/media/
       <Directory /var/www/advent/media>
           Require all granted
           Options -Indexes
       </Directory>
   </VirtualHost>
   ```

   ```bash
   sudo a2ensite advent && sudo systemctl reload apache2
   ```

   След всяка промяна на кода: `collectstatic` и `sudo touch advent/wsgi.py` (рестартира приложението).

## Структура

```
advent/            настройки на проекта, urls, wsgi
doors/             модели (Door, AdventSettings), API, админ, seed_doors, тестове
templates/         base.html, doors/index.html
static/            css/style.css, js/app.js, js/snow.js, music/theme.mp3, img/pgknma-logo.(svg|png)
media/             качени снимки (doors/…)
```

## Лиценз

Copyright (C) 2026 Krum ([Krumqnkata](https://github.com/Krumqnkata))

Програмата е свободен софтуер: можеш да я разпространяваш и/или променяш при условията на
[GNU Affero General Public License](LICENSE), версия 3, публикуван от Free Software Foundation.
Накратко: всеки може да ползва, променя и споделя кода, но ако пусне променена версия
(включително само като уеб сайт), трябва да публикува изходния ѝ код под същия лиценз и
да запази бележките за авторство. Пълните условия са в [LICENSE](LICENSE).

**Не са под този лиценз:** логото и името на ПГКНМА „Проф. Минко Балкански“
(`static/img/pgknma-logo.svg`, `static/img/pgknma-logo.png`) принадлежат на училището и не
са част от лиценза на кода. Ако ползваш проекта за друго училище
или организация, замени ги със свои (логото и името се сменят и от админа).

Иконите са по мотиви от [Lucide](https://lucide.dev) (ISC лиценз). Шрифтовете Manrope,
Marck Script и Playfair Display са под SIL Open Font License.
