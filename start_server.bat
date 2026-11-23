@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Aevum

if not exist venv (
    echo [Aevum] Virtual muhit yaratilmoqda...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

python manage.py compile_translations
python manage.py migrate
python manage.py seed_watches
rem Lokal admin: login admin, parol admin12345 (faqat birinchi marta yaratiladi)
set DJANGO_SUPERUSER_PASSWORD=admin12345
python manage.py ensure_admin
set DJANGO_SUPERUSER_PASSWORD=
start "" http://127.0.0.1:8001/
python manage.py runserver 127.0.0.1:8001
pause
