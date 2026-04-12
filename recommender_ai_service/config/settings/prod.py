"""Production settings — PostgreSQL, strict security, structured logging."""
import os
from .base import *  # noqa: F401, F403

DEBUG = False

SECRET_KEY = os.environ['SECRET_KEY']   # must be set, no fallback in prod

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# ── PostgreSQL ─────────────────────────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'recommender_db'),
        'USER': os.environ.get('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
        'HOST': os.environ.get('POSTGRES_HOST', 'db'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
        'OPTIONS': {'connect_timeout': 10},
        'CONN_MAX_AGE': 60,
    }
}

# ── Security ───────────────────────────────────────────────────────────────────
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# ── CORS ───────────────────────────────────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',') if o.strip()
]

# ── Structured Logging ─────────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {name} [{process}] {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {'handlers': ['console'], 'level': 'WARNING'},
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
        'apps': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'ml': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'etl': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'tasks': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
    },
}
