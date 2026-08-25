#!/bin/bash
set -e

echo "=== [DMC SYSTEM] STARTING APPLICATION ==="
echo "Python version: $(python --version)"

# 1. Wait for database
echo "--> Step 1/4: Checking database connection..."
python manage.py wait_for_db || true

# 2. Run migrations
echo "--> Step 2/4: Applying database migrations..."
python manage.py migrate --noinput || true

# 3. Initialize Admin & Seed initial data
echo "--> Step 3/4: Initializing Admin and initial data..."
python manage.py init_admin || true

# 4. Collect static files
echo "--> Step 4/4: Collecting static files..."
python manage.py collectstatic --noinput || true

# 5. Start Gunicorn Web Server
PORT="${PORT:-8000}"
echo "=== [DMC SYSTEM] LAUNCHING GUNICORN ON PORT ${PORT} ==="
exec gunicorn dms_project.wsgi:application \
    --bind "0.0.0.0:${PORT}" \
    --workers 2 \
    --threads 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -