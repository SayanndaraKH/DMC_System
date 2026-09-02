import os
import socket
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env configuration if present locally
ENV_FILE = BASE_DIR / '.env'
if ENV_FILE.exists():
    with open(ENV_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ.setdefault(key.strip(), val.strip())

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-dms-cambodia-gov-doc-management-system-secret-key-2026'
)

# DEBUG is True by default for local development unless DEBUG=False is explicitly set (e.g. on Railway)
DEBUG = os.environ.get('DEBUG', 'True').strip().lower() in ['true', '1', 'yes']

# ALLOWED_HOSTS configuration
allowed_hosts_env = os.environ.get('ALLOWED_HOSTS', '*')
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_env.split(',') if host.strip()]

# CSRF Trusted Origins for Local Network, Domains, and Railway
CSRF_TRUSTED_ORIGINS = [
    'http://127.0.0.1:8000',
    'http://localhost:8000',
    'http://127.0.0.1',
    'http://localhost',
    'https://*.railway.app',
    'https://*.up.railway.app',
]

try:
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    CSRF_TRUSTED_ORIGINS.extend([
        f'http://{local_ip}:8000',
        f'http://{local_ip}',
    ])
except Exception:
    pass

csrf_origins_env = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
if csrf_origins_env:
    CSRF_TRUSTED_ORIGINS.extend([
        origin.strip() for origin in csrf_origins_env.split(',') if origin.strip()
    ])

# CSRF & Security settings
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
X_FRAME_OPTIONS = 'SAMEORIGIN'

# Railway / Reverse Proxy HTTPS Headers
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'dms',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Enable WhiteNoise for serving static files efficiently in production
try:
    import whitenoise  # noqa: F401
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
except ImportError:
    pass

ROOT_URLCONF = 'dms_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'dms', 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'dms.context_processors.dms_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'dms_project.wsgi.application'

# Database Configuration (Auto-detects Railway PostgreSQL or persistent storage / local SQLite)
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    try:
        import dj_database_url
        DATABASES = {
            'default': dj_database_url.config(
                default=DATABASE_URL,
                conn_max_age=600,
                conn_health_checks=True
            )
        }
    except Exception:
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        }
else:
    # If no PostgreSQL, check for persistent volume mount paths (/app/data, /data, /app/media, or DATA_DIR)
    persistent_db_dir = os.environ.get('DATA_DIR')
    if not persistent_db_dir:
        for candidate in ['/app/data', '/data', '/app/media']:
            if os.path.exists(candidate) and os.path.isdir(candidate):
                persistent_db_dir = candidate
                break

    if persistent_db_dir and os.path.exists(persistent_db_dir):
        db_file = os.path.join(persistent_db_dir, 'db.sqlite3')
    else:
        db_file = BASE_DIR / 'db.sqlite3'

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': db_file,
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
]

LANGUAGE_CODE = 'km-kh'
TIME_ZONE = 'Asia/Phnom_Penh'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'dms', 'static'),
]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Media files (Uploads - persistent detection)
MEDIA_URL = '/media/'
media_candidate = os.environ.get('MEDIA_ROOT')
if not media_candidate:
    # Railway sets RAILWAY_VOLUME_MOUNT_PATH on any service with a volume attached.
    # Using it means uploads land on the volume wherever it is mounted, so photos
    # survive a redeploy without anyone having to set MEDIA_ROOT by hand.
    volume_mount = os.environ.get('RAILWAY_VOLUME_MOUNT_PATH')
    if volume_mount and os.path.isdir(volume_mount):
        media_candidate = os.path.join(volume_mount, 'media')
    elif os.path.isdir('/app/media'):
        media_candidate = '/app/media'
    else:
        media_candidate = os.path.join(BASE_DIR, 'media')
MEDIA_ROOT = media_candidate
# Uploads fail with a 500 if the directory is missing (e.g. a freshly mounted volume).
os.makedirs(MEDIA_ROOT, exist_ok=True)

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email Configuration for OTP Verification
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() in ['true', '1', 'yes']
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '').strip()
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '').strip()

# Auto-select SMTP backend when user credentials exist
if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', f'DMS Cambodia <{EMAIL_HOST_USER}>')
else:
    EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
    DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'DMS Cambodia <no-reply@dms.gov.kh>')

# Logging Configuration to suppress noisy polling endpoint logs in runserver console
import logging

class SuppressPollingFilter(logging.Filter):
    """
    Filters out noisy routine polling requests (such as chat unread check / messages)
    and favicon redirects with 200/302/304 status so terminal console stays clean.
    """
    def filter(self, record):
        try:
            msg = record.getMessage()
            if any(endpoint in msg for endpoint in ['/chat/api/check-unread/', '/chat/api/messages/', '/favicon.ico']):
                if any(code in msg for code in ['" 200 ', '" 304 ', '" 302 ']):
                    return False
        except Exception:
            pass
        return True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'suppress_polling': {
            '()': 'dms_project.settings.SuppressPollingFilter',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'filters': ['suppress_polling'],
        },
    },
    'loggers': {
        'django.server': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

