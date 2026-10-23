import os
import sys
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

# DEBUG is True by default for local development unless DEBUG=False is explicitly set (e.g. in Production)
DEBUG = os.environ.get('DEBUG', 'True').strip().lower() in ['true', '1', 'yes']

# ALLOWED_HOSTS configuration
allowed_hosts_env = os.environ.get('ALLOWED_HOSTS', '*')
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_env.split(',') if host.strip()]

# CSRF Trusted Origins for Local Network, Domains, and Cloud
CSRF_TRUSTED_ORIGINS = [
    'http://127.0.0.1:8000',
    'http://localhost:8000',
    'http://127.0.0.1',
    'http://localhost',
    'https://hrmismaffpl.netlify.app',
    'https://*.netlify.app',
    'https://*.trycloudflare.com',
]

# Auto-detect all active LAN / Wi-Fi IP addresses on this host
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0.5)
    s.connect(('8.8.8.8', 80))
    detected_lan_ip = s.getsockname()[0]
    s.close()
    if detected_lan_ip and not detected_lan_ip.startswith('127.'):
        CSRF_TRUSTED_ORIGINS.extend([
            f'http://{detected_lan_ip}:8000',
            f'http://{detected_lan_ip}',
            f'https://{detected_lan_ip}:8000',
            f'https://{detected_lan_ip}',
        ])
except Exception:
    pass

try:
    hostname = socket.gethostname()
    for addr_info in socket.getaddrinfo(hostname, None):
        ip = addr_info[4][0]
        if ':' not in ip and not ip.startswith('127.') and not ip.startswith('169.254.'):
            CSRF_TRUSTED_ORIGINS.extend([
                f'http://{ip}:8000',
                f'http://{ip}',
                f'https://{ip}:8000',
                f'https://{ip}',
            ])
except Exception:
    pass

csrf_origins_env = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
if csrf_origins_env:
    CSRF_TRUSTED_ORIGINS.extend([
        origin.strip() for origin in csrf_origins_env.split(',') if origin.strip()
    ])

# Deduplicate origins
CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(CSRF_TRUSTED_ORIGINS))

# Synchronization Security Token
SYNC_AUTH_TOKEN = os.environ.get('SYNC_AUTH_TOKEN', 'dms-secure-sync-token-2026-cambodia-gov')

# CSRF & Security settings
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_AGE = 60 * 60 * 12  # 12 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # Discard session on window close
# Session Optimization: Read sessions from local memory cache first, avoiding Neon roundtrips
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
SESSION_SAVE_EVERY_REQUEST = False  # Only save when session data is actually modified!
X_FRAME_OPTIONS = 'SAMEORIGIN'

# Reverse Proxy HTTPS Headers
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# High-speed in-memory cache for Neon Cloud query results and dashboard statistics
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'dms_memory_cache',
        'TIMEOUT': 180,
        'OPTIONS': {
            'MAX_ENTRIES': 3000
        }
    }
}


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
    'dms.middleware.NeonDatabaseRetryMiddleware',
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
    WHITENOISE_USE_FINDERS = True
    WHITENOISE_AUTOREFRESH = True
except ImportError:
    pass

ROOT_URLCONF = 'dms_project.urls'

# Disk templates support: allows templates on disk to override frozen bundle in PyInstaller
DISK_TEMPLATE_DIRS = []
if getattr(sys, 'frozen', False):
    exe_dir = Path(sys.executable).resolve().parent
    if (exe_dir / 'dms' / 'templates').exists():
        DISK_TEMPLATE_DIRS.append(str(exe_dir / 'dms' / 'templates'))
    if (exe_dir.parent / 'dms' / 'templates').exists():
        DISK_TEMPLATE_DIRS.append(str(exe_dir.parent / 'dms' / 'templates'))

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': DISK_TEMPLATE_DIRS + [os.path.join(BASE_DIR, 'dms', 'templates')],
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

# Database Configuration: STRICT NEON CLOUD DATABASE (PRIMARY)
# db.sqlite3 is deactivated / placed on standby as requested by the user.
USE_LOCAL_SQLITE = os.environ.get('USE_LOCAL_SQLITE', 'False').strip().lower() in ['true', '1', 'yes']
NEON_CLOUD_DATABASE_URL = "postgresql://neondb_owner:npg_bw8CSyjXtql6@ep-wandering-fire-awc8mlbh-pooler.c-12.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
DATABASE_URL = os.environ.get('DATABASE_URL', NEON_CLOUD_DATABASE_URL)

if not USE_LOCAL_SQLITE and DATABASE_URL:
    try:
        import dj_database_url
        DATABASES = {
            'default': dj_database_url.config(
                default=DATABASE_URL,
                conn_max_age=0,  # 0 recommended for Neon PgBouncer pooler to prevent dead socket errors
                conn_health_checks=True,
                ssl_require=True
            )
        }
        DATABASES['default']['DISABLE_SERVER_SIDE_CURSORS'] = True
        
        # Add TCP Keepalives and connect timeout for robust serverless cloud connectivity
        db_options = DATABASES['default'].get('OPTIONS', {})
        db_options.setdefault('connect_timeout', 15)
        db_options.setdefault('keepalives', 1)
        db_options.setdefault('keepalives_idle', 30)
        db_options.setdefault('keepalives_interval', 10)
        db_options.setdefault('keepalives_count', 5)
        DATABASES['default']['OPTIONS'] = db_options
    except Exception as e:
        print(f"Warning: Neon Cloud PostgreSQL configuration error ({e}). Falling back to local db.sqlite3.")
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        }
else:
    # Local SQLite standby mode (activated only when USE_LOCAL_SQLITE=True is explicitly set)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# High-speed cached session engine (Memory cached reads + background DB persistence for Neon Cloud)
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

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
if getattr(sys, 'frozen', False):
    exe_dir = Path(sys.executable).resolve().parent
    disk_static = exe_dir / 'staticfiles'
    if disk_static.is_dir():
        STATIC_ROOT = str(disk_static)
    else:
        STATIC_ROOT = os.path.join(str(BASE_DIR), 'staticfiles')
else:
    STATIC_ROOT = os.path.join(str(BASE_DIR), 'staticfiles')

try:
    os.makedirs(STATIC_ROOT, exist_ok=True)
except OSError:
    pass

# Media files (Uploads - persistent detection & multi-location fallback)
MEDIA_URL = '/media/'
media_candidate = os.environ.get('MEDIA_ROOT')
if not media_candidate:
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).resolve().parent
        # 1. If 'media' folder is placed directly next to DMC_System.exe, prioritize it!
        if (exe_dir / 'media').is_dir() and any((exe_dir / 'media').iterdir()):
            media_candidate = str(exe_dir / 'media')
        elif (exe_dir.parent / 'media').is_dir() and any((exe_dir.parent / 'media').iterdir()):
            media_candidate = str(exe_dir.parent / 'media')
        else:
            # 2. Use persistent folder in %LOCALAPPDATA%\DMC_System\media
            local_app = os.environ.get('LOCALAPPDATA', '')
            if local_app:
                media_candidate = os.path.join(local_app, 'DMC_System', 'media')
            else:
                media_candidate = str(exe_dir / 'media')
    elif os.environ.get('AWS_LAMBDA_FUNCTION_NAME') or os.environ.get('NETLIFY'):
        media_candidate = '/tmp/media'
    else:
        # Check project media folder
        if (BASE_DIR / 'media').is_dir():
            media_candidate = str(BASE_DIR / 'media')
        else:
            volume_mount = os.environ.get('VOLUME_MOUNT_PATH') or os.environ.get('DATA_DIR')
            if volume_mount and os.path.isdir(volume_mount):
                media_candidate = os.path.join(volume_mount, 'media')
            elif os.path.isdir('/app/media'):
                media_candidate = '/app/media'
            else:
                media_candidate = str(BASE_DIR / 'media')

MEDIA_ROOT = str(media_candidate)
# Uploads fail if the directory is missing; ignore read-only FS errors on Lambda boot
try:
    os.makedirs(MEDIA_ROOT, exist_ok=True)
except OSError:
    pass

# Allow uploading files without size restriction
DATA_UPLOAD_MAX_MEMORY_SIZE = None
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10240

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

