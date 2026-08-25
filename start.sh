#!/bin/bash
set -e

echo "=== [DMC SYSTEM] STARTING APPLICATION ==="

# 1. Wait for database
python manage.py wait_for_db || true

# 2. Run migrations
python manage.py migrate --noinput || true

# 3. Initialize Admin & Seed initial data
python manage.py init_admin || true

# 4. Collect static files
python manage.py collectstatic --noinput || true

# 5. Start Gunicorn Web Server
PORT="${PORT:-8000}"
echo "=== [DMC SYSTEM] LAUNCHING GUNICORN ON PORT ${PORT} ==="
exec gunicorn dms_project.wsgi:application --bind "0.0.0.0:${PORT}" --workers 2 --threads 2 --timeout 120 --access-logfile - --error-logfile -
