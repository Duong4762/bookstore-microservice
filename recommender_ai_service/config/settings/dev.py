"""Development settings — SQLite, debug toolbar, relaxed throttling."""
from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ['*']

# SQLite for fast local development
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db_dev.sqlite3',
    }
}

# Relax throttling in dev
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {  # type: ignore[index]
    'anon': '10000/min',
    'event_collector': '10000/min',
}

# Verbose logging for dev
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'colored': {
            'format': '[{levelname}] {name} — {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'colored',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'apps': {'handlers': ['console'], 'level': 'DEBUG', 'propagate': False},
        'ml': {'handlers': ['console'], 'level': 'DEBUG', 'propagate': False},
        'etl': {'handlers': ['console'], 'level': 'DEBUG', 'propagate': False},
        'tasks': {'handlers': ['console'], 'level': 'DEBUG', 'propagate': False},
    },
}
