#!/bin/bash
set -e
export PYTHONUNBUFFERED=1

echo "=== [DMC SYSTEM] STARTING APPLICATION ==="

# 1. Wait for database
python manage.py wait_for_db

# 2. Run migrations
python manage.py migrate --noinput

# 3. Load Cambodia geography (idempotent - repairs a partial/failed load).
#    Non-fatal: a failure prints its traceback but must not block the web server.
python manage.py load_geo || echo "!!! [DMC SYSTEM] load_geo FAILED - see traceback above"

# 4. Initialize Admin & Seed initial data
python manage.py init_admin

# 5. Report where uploaded media lives (warns loudly if it is not a volume)
python manage.py check_media || true

# 6. Collect static files
python manage.py collectstatic --noinput

# 7. Start Gunicorn Web Server
PORT="${PORT:-8000}"
echo "=== [DMC SYSTEM] LAUNCHING GUNICORN ON PORT ${PORT} ==="
exec gunicorn dms_project.wsgi:application --bind "0.0.0.0:${PORT}" --workers 2 --threads 2 --timeout 120 --access-logfile - --error-logfile -
