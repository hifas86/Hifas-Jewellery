#!/bin/bash
echo "⚙️ Running Django migrations..."
python manage.py makemigrations --noinput
python manage.py migrate --noinput

echo "📦 Collecting static files..."
python manage.py collectstatic --noinput

echo "🚀 Starting Gunicorn..."
gunicorn goldtrade.wsgi:application --config gunicorn.conf.py
