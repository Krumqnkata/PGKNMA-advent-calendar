#!/usr/bin/env bash
# Обновяване на сървъра с последната версия от GitHub.
# Пуска се от потребителя, който притежава /var/www/koleda (не от root):
#   cd /var/www/koleda && ./deploy/update.sh
set -euo pipefail

cd "$(dirname "$0")/.."

echo "→ Изтегляне от GitHub"
git pull --ff-only

echo "→ Пакети"
.venv/bin/pip install --quiet -r requirements.txt

echo "→ Миграции"
.venv/bin/python manage.py migrate --noinput

echo "→ Статични файлове"
.venv/bin/python manage.py collectstatic --noinput

echo "→ Проверка"
.venv/bin/python manage.py check

echo "→ Рестарт на услугата"
sudo systemctl restart koleda
sleep 2
systemctl --no-pager --lines=5 status koleda

echo "Готово."
