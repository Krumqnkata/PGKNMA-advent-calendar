# Пускане на сървъра – koleda.pgknma.space

Гайдът е за Ubuntu/Debian сървър, на който вече работи Apache с Cloudflare Origin
сертификат на порт 8443 (както главният сайт pgknma.space).

```
Посетител ──HTTPS──▶ Cloudflare ──HTTPS :8443──▶ Apache ──HTTP 127.0.0.1:8003──▶ Waitress → Django ──▶ MySQL
                                                   │
                                                   └─ /static/ и /media/ директно от диска
```

| Какво | Къде |
|---|---|
| Код | `/var/www/koleda` |
| Waitress (Django) | `127.0.0.1:8003` |
| systemd услуга | `koleda` |
| Apache сайт | `/etc/apache2/sites-available/koleda.pgknma.space.conf` |
| Готови файлове | `deploy/apache/…`, `deploy/systemd/koleda.service`, `deploy/update.sh` |

Командите се пускат като твоя потребител със `sudo` права (не като root).
Където пише `<…>`, сложи своя стойност **без самите знаци `<` и `>`**.

---

## 1. Cloudflare

1. **DNS → Add record**: тип `CNAME`, име `koleda`, цел `pgknma.space`, **Proxied** (оранжев облак).
2. **SSL/TLS → Overview**: режим **Full (strict)** (вероятно вече е така за главния сайт).
3. **Сертификатът на сървъра трябва да покрива субдомейна.** Провери на сървъра:

   ```bash
   sudo openssl x509 -in /etc/ssl/certs/cloudflare.pem -noout -ext subjectAltName
   ```

   Трябва да видиш `DNS:*.pgknma.space`. Ако го няма: **SSL/TLS → Origin Server → Create
   Certificate** с имена `pgknma.space, *.pgknma.space`, запиши го на сървъра (напр.
   `/etc/ssl/certs/cloudflare.pem` и `/etc/ssl/private/cloudflare.key`, права `600` за ключа)
   и презареди Apache. Иначе Cloudflare връща грешка **526**.
4. **Порт 8443.** Cloudflare по подразбиране се свързва със сървъра на порта, на който е дошъл
   посетителят (443). Щом главният сайт работи на 8443, в **Rules → Origin Rules** вероятно има
   правило „Destination Port → 8443“ за `pgknma.space`. Добави и `koleda.pgknma.space` към него
   (Hostname equals …) или направи ново правило със същата настройка. Иначе – грешка **521/522**.
5. **Speed → Optimization → Rocket Loader: Off** (или поне за `koleda`) – пренарежда скриптовете
   и може да счупи вратичките/брояча.
6. Не включвай „Cache Everything“ за HTML: страницата зависи от датата (обратно броене, днешна
   вратичка). CSS/JS/снимките Cloudflare кешира сам – имената им съдържат хеш, така че няма
   нужда от ръчно „Purge cache“ след обновяване.

## 2. Пакети на сървъра

```bash
sudo apt update
sudo apt install -y git python3-venv python3-dev build-essential pkg-config default-libmysqlclient-dev
python3 --version     # нужно е 3.10 – 3.13
mysql --version       # MySQL 8.0.11+ или MariaDB 10.5+
```

> Django 5.2 работи с MySQL 8.0. (Django 6 изисква MySQL 8.4+ – затова проектът стои на 5.2 LTS.)

## 3. Кодът

```bash
sudo mkdir -p /var/www/koleda
sudo chown "$USER":www-data /var/www/koleda
git clone https://github.com/Krumqnkata/PGKNMA-advent-calendar.git /var/www/koleda
cd /var/www/koleda
```

Кодът е твой (`$USER`), а услугата работи като `www-data` и може само да го чете –
пише единствено в `media/` (качените снимки).

## 4. Python среда

```bash
cd /var/www/koleda
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

## 5. MySQL база

Генерирай парола и я запиши – трябва ти в следващата стъпка:

```bash
openssl rand -base64 24
```

```bash
sudo mysql
```

```sql
CREATE DATABASE koleda CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'koleda'@'127.0.0.1' IDENTIFIED BY '<паролата>';
GRANT ALL PRIVILEGES ON koleda.* TO 'koleda'@'127.0.0.1';
FLUSH PRIVILEGES;
EXIT;
```

Връзката е през TCP на `127.0.0.1` (не през socket) – така работи и със защитата на
systemd услугата.

## 6. Настройки (`.env`)

Генерирай таен ключ:

```bash
.venv/bin/python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

```bash
cp .env.example .env
nano .env
```

Съдържанието трябва да е (замени `<…>` заедно със знаците `< >`):

```ini
SECRET_KEY='<ключът от командата по-горе>'
DEBUG=False

ALLOWED_HOSTS=koleda.pgknma.space
CSRF_TRUSTED_ORIGINS=https://koleda.pgknma.space

# Свой, трудно отгатваем адрес на админа – смени k7x2 с нещо свое и не го споделяй.
# Само латински букви, цифри, - и _ (без < >), иначе сайтът няма да тръгне.
ADMIN_URL=upravlenie-k7x2/

DB_ENGINE=mysql
DB_NAME=koleda
DB_USER=koleda
DB_PASSWORD=<паролата от стъпка 5>
DB_HOST=127.0.0.1
DB_PORT=3306

# По избор
# WAITRESS_LISTEN=127.0.0.1:8003
# WAITRESS_THREADS=8
```

```bash
chmod 640 .env
sudo chgrp www-data .env
```

## 7. Django: база, статични файлове, админ

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py seed_doors        # по избор: 25 готови вратички, 8 от тях със снимки
.venv/bin/python manage.py check --deploy
```

`check --deploy` може да предупреди за **HSTS** (`security.W004`) и **SSL redirect**
(`security.W008`) – това се поема от Cloudflare (**SSL/TLS → Edge Certificates →
Always Use HTTPS** и **HSTS**). Други предупреждения не би трябвало да има.

## 8. Права

```bash
sudo chown -R www-data:www-data /var/www/koleda/media
chmod -R a+rX /var/www/koleda/staticfiles
```

## 9. Waitress като услуга

```bash
sudo cp deploy/systemd/koleda.service /etc/systemd/system/koleda.service
sudo systemctl daemon-reload
sudo systemctl enable --now koleda
systemctl status koleda
```

Проверка направо към Waitress (без Apache):

```bash
curl -sI -H "Host: koleda.pgknma.space" http://127.0.0.1:8003/ | head -1    # HTTP/1.1 200 OK
```

Ако портът е зает (`sudo ss -ltnp | grep 8003`), сложи друг в `.env` (`WAITRESS_LISTEN`) и във
vhost-а на Apache.

Дневник: `journalctl -u koleda -f`

## 10. Apache

```bash
sudo cp deploy/apache/koleda.pgknma.space.conf /etc/apache2/sites-available/
sudo a2enmod ssl proxy proxy_http headers
sudo a2ensite koleda.pgknma.space
sudo apache2ctl configtest           # трябва: Syntax OK
sudo systemctl reload apache2
```

`Listen 8443` вече трябва да е в `/etc/apache2/ports.conf` (за главния сайт).

Проверка от самия сървър, без Cloudflare:

```bash
curl -skI --resolve koleda.pgknma.space:8443:127.0.0.1 https://koleda.pgknma.space:8443/ | head -1
```

## 11. Проверка отвън

1. Отвори **https://koleda.pgknma.space** – виждаш заглавието, панделката и обратното броене.
2. Отвори адреса на админа, напр. **https://koleda.pgknma.space/upravlenie-k7x2/**, и влез с потребителя от стъпка 7.
   `https://koleda.pgknma.space/admin/` трябва да дава 404.
3. В **Настройки на календара** провери периода (1–24/25 декември 2026), текстовете и училището.
4. Качи тестова снимка към вратичка и провери, че се показва в тестовия ѝ ден.
5. Истинският IP: `sudo tail -f /var/log/apache2/koleda_access.log` – първата колона трябва да е
   твоят IP, не адрес на Cloudflare.
6. След тестовете изтрий тестовата статистика от админа (**Статистика → По дни / По вратички**).

## 12. Обновяване

След като качиш промени в GitHub:

```bash
cd /var/www/koleda
./deploy/update.sh
```

Скриптът прави `git pull`, инсталира пакетите, пуска миграциите и `collectstatic` и рестартира
услугата.

Команди, които пишат в `media/` (например повторно зареждане на примерните вратички със
снимки), се пускат като `www-data`, защото папката е негова:

```bash
sudo -u www-data .venv/bin/python manage.py seed_doors --force
```

## 13. Архивиране

Всяка нощ в 03:30: база + качени снимки, пазят се 14 дни.

```bash
sudo mkdir -p /var/backups/koleda
sudo chmod 700 /var/backups/koleda
sudo tee /etc/cron.d/koleda-backup > /dev/null <<'EOF'
30 3 * * * root mysqldump --single-transaction --default-character-set=utf8mb4 koleda | gzip > /var/backups/koleda/db-$(date +\%F).sql.gz && tar -czf /var/backups/koleda/media-$(date +\%F).tar.gz -C /var/www/koleda media && find /var/backups/koleda -type f -mtime +14 -delete
EOF
```

Възстановяване на базата:

```bash
gunzip -c /var/backups/koleda/db-<дата>.sql.gz | sudo mysql koleda
```

## 14. Проблеми

| Симптом | Причина / решение |
|---|---|
| Cloudflare **526** | Origin сертификатът не покрива `koleda.pgknma.space` → стъпка 1.3 |
| Cloudflare **521 / 522** | Cloudflare не стига до 8443 → Origin Rule за порта (1.4), Apache работи ли |
| **502 / 503** от Apache | Услугата е спряла → `journalctl -u koleda -n 50` |
| Админът дава **500**, `NoReverseMatch … (?P<…>` | В `ADMIN_URL` има `< >` → напиши го без тях и `sudo systemctl restart koleda` |
| **400 Bad Request** | Домейнът липсва в `ALLOWED_HOSTS` |
| **403 CSRF** при вход в админа | `CSRF_TRUSTED_ORIGINS=https://koleda.pgknma.space`; vhost-ът праща `X-Forwarded-Proto https` |
| Страницата е без стилове | `collectstatic` не е пуснат или пътят в `Alias /static/` е грешен |
| Снимките дават 403/404 | Права на `media/` (стъпка 8) |
| `PermissionError: … media/doors` при `manage.py` | Пусни командата като `sudo -u www-data .venv/bin/python manage.py …` |
| `Unknown column …` | Не са пуснати миграциите → `.venv/bin/python manage.py migrate` и `sudo systemctl restart koleda` |
| В „Грешни опити за вход“ всички IP-та са `127.0.0.1` | Липсват редовете `RequestHeader … X-Forwarded-For` във vhost-а |
| Не тръгва след рестарт: `Can't connect to MySQL` | `DB_HOST=127.0.0.1` и потребителят е `'koleda'@'127.0.0.1'` |

## Сигурност (по избор, за целия сървър)

Apache вярва на `CF-Connecting-IP`. Ако някой се свърже с порт 8443 **директно** (покрай
Cloudflare), може да подправи тази заглавка. За да няма как, разреши 8443 само за адресите на
Cloudflare (https://www.cloudflare.com/ips/) в защитната стена или включи **Authenticated
Origin Pulls**. Това засяга и главния сайт, който е на същия порт, затова го направи съзнателно.

Логовете на Apache съдържат IP адресите на посетителите; в Ubuntu/Debian се пазят 14 дни
(`/etc/logrotate.d/apache2`). Самото приложение не пази IP адреси.
