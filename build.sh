#!/usr/bin/env bash
# Render har deployda shu skriptni ishga tushiradi
set -o errexit

pip install -r requirements.txt
python manage.py compile_translations   # locale/*.po -> .mo (uz/ru/en)
python manage.py collectstatic --no-input
python manage.py migrate --no-input
python manage.py seed_watches   # bo'sh katalogni to'ldiradi; bor bo'lsa faqat yetishmaganini (tasmalar, tarjimalar)
python manage.py ensure_admin   # DJANGO_SUPERUSER_PASSWORD bo'yicha admin
