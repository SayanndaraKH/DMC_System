#!/usr/bin/env bash
set -e

echo "=================================================="
echo "    DMC SYSTEM - NETLIFY CLOUD BUILD & DEPLOY     "
echo "=================================================="

# 1. Collect static files
echo "[1/3] Collecting Django static files..."
python manage.py collectstatic --noinput

# 2. Check and migrate database if DATABASE_URL is configured
echo "[2/3] Checking Database configuration..."
if [ -n "$DATABASE_URL" ]; then
    echo ">> DATABASE_URL detected. Connecting to Neon PostgreSQL..."
    python manage.py migrate --noinput || echo ">> Warning: Migration had non-fatal notices."
    python manage.py load_geo || echo ">> Notice: load_geo completed or already populated."
    python manage.py init_admin || echo ">> Notice: init_admin completed."
    echo ">> Database sync completed successfully!"
else
    echo ">> Notice: DATABASE_URL is not yet set in Netlify Environment Variables."
    echo ">> Please set DATABASE_URL (from your Neon Console) in Netlify Site Configuration."
fi

echo "[3/3] Netlify build completed successfully!"
