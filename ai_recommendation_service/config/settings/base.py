"""Cấu hình chung — AI Recommendation (BiLSTM sequence model)."""
import importlib.util
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dev-ai-rec-change-me')

DEBUG = False
ALLOWED_HOSTS: list[str] = []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'tracking',
    'catalog_proxy',
    'recommendation',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'ai_recommendation_db'),
        'USER': os.environ.get('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'postgres'),
        'HOST': os.environ.get('POSTGRES_HOST', 'postgres'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
    }
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_THROTTLE_CLASSES': ['rest_framework.throttling.AnonRateThrottle'],
    'DEFAULT_THROTTLE_RATES': {'anon': '200/min', 'event_collector': '60/min'},
}

CORS_ALLOW_ALL_ORIGINS = True

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
_has_django_redis = importlib.util.find_spec('django_redis') is not None
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache' if _has_django_redis else 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': REDIS_URL if _has_django_redis else 'ai-recommendation-local-cache',
        'KEY_PREFIX': 'ai_bilstm_rec',
    }
}
if _has_django_redis:
    CACHES['default']['OPTIONS'] = {
        'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        'SOCKET_CONNECT_TIMEOUT': 5,
        'SOCKET_TIMEOUT': 5,
        'IGNORE_EXCEPTIONS': True,
    }

PRODUCT_SERVICE_URL = os.environ.get('PRODUCT_SERVICE_URL', 'http://localhost:8002')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')
CHAT_STORE_BASE_URL = os.environ.get('CHAT_STORE_BASE_URL', '').rstrip('/')
NEO4J_HTTP_URL = os.environ.get('NEO4J_HTTP_URL', 'http://neo4j:7474')
NEO4J_USERNAME = os.environ.get('NEO4J_USERNAME', 'neo4j')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', 'password')

ARTIFACTS_DIR = BASE_DIR / 'ml' / 'artifacts'
RECOMMENDATION_ML = {
    'ARTIFACTS_DIR': ARTIFACTS_DIR,
    'MODEL_PATH': ARTIFACTS_DIR / 'bilstm_model.keras',
    'MODEL_METADATA_PATH': ARTIFACTS_DIR / 'bilstm_metadata.json',
    # BiLSTM / huấn luyện
    'MAX_SEQUENCE_LEN': int(os.environ.get('REC_MAX_LEN', '10')),
    'TRAIN_EPOCHS': int(os.environ.get('REC_EPOCHS', '20')),
    'BATCH_SIZE': int(os.environ.get('REC_BATCH', '128')),
    # Serving
    'USER_EMB_CACHE_TTL': int(os.environ.get('REC_USER_EMB_TTL', '300')),
    'CACHE_KEY_PREFIX': 'bilstm_rec:user:',
    'MONITORING_HOOK': None,
    # Scheduler nội bộ (không Celery)
    'AUTO_RETRAIN_ENABLED': os.environ.get('REC_AUTO_RETRAIN_ENABLED', '1').lower() in ('1', 'true', 'yes'),
    'AUTO_RETRAIN_INTERVAL_SECONDS': int(os.environ.get('REC_AUTO_RETRAIN_INTERVAL_SECONDS', '86400')),
    'AUTO_RETRAIN_EVENT_THRESHOLD': int(os.environ.get('REC_AUTO_RETRAIN_EVENT_THRESHOLD', '10')),
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {'std': {'format': '[{levelname}] {name}: {message}', 'style': '{'}},
    'handlers': {'console': {'class': 'logging.StreamHandler', 'formatter': 'std'}},
    'root': {'handlers': ['console'], 'level': 'INFO'},
    'loggers': {
        'django': {'level': 'INFO'},
        'recommendation': {'level': 'DEBUG'},
        'tracking': {'level': 'DEBUG'},
    },
}
