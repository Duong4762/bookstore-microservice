"""
Base Django settings for AI Recommendation Service.
All environments inherit from this file.
"""
import os
from pathlib import Path
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dev-key-change-in-production')

DEBUG = False

ALLOWED_HOSTS = []

# ── Application definition ─────────────────────────────────────────────────────

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'corsheaders',
    # Internal apps
    'apps.tracking',
    'apps.recommend',
    'apps.catalog_proxy',
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

# ── Internationalisation ───────────────────────────────────────────────────────

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_I18N = True
USE_TZ = True

# ── Static files ───────────────────────────────────────────────────────────────

STATIC_URL = '/static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── REST Framework ─────────────────────────────────────────────────────────────

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '200/min',
        'event_collector': '60/min',   # per IP for tracking endpoint
    },
}

# ── CORS ───────────────────────────────────────────────────────────────────────

CORS_ALLOW_ALL_ORIGINS = True  # tighten in production

# ── Redis / Cache ──────────────────────────────────────────────────────────────

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'IGNORE_EXCEPTIONS': True,   # graceful fallback when Redis down
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        },
        'KEY_PREFIX': 'recommender',
    }
}

# ── Celery ─────────────────────────────────────────────────────────────────────

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', REDIS_URL)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 4 * 3600  # 4 hours max per task (training can take time)

CELERY_BEAT_SCHEDULE = {
    # Nightly ETL + retrain at 02:00 AM
    'nightly-etl-and-train': {
        'task': 'tasks.training_tasks.nightly_etl_and_train',
        'schedule': crontab(hour=2, minute=0),
    },
    # Bestseller cache refresh every hour
    'hourly-update-bestsellers': {
        'task': 'tasks.etl_tasks.update_bestsellers_cache',
        'schedule': crontab(minute=0),
    },
    # Data drift check every 6 hours
    'drift-detection': {
        'task': 'tasks.training_tasks.check_data_drift',
        'schedule': crontab(hour='*/6', minute=30),
    },
}

# ── External Service URLs ──────────────────────────────────────────────────────

PRODUCT_SERVICE_URL = os.environ.get('PRODUCT_SERVICE_URL', 'http://localhost:8002')

# ── ML Settings ────────────────────────────────────────────────────────────────

ML_SETTINGS = {
    # Paths
    'CHECKPOINT_DIR': BASE_DIR / 'ml' / 'checkpoints',
    'DATA_DIR': BASE_DIR / 'ml' / 'data',
    'VOCAB_PATH': BASE_DIR / 'ml' / 'checkpoints' / 'vocab.json',

    # Inference
    'SEQUENCE_LENGTH': 20,          # max past events to consider
    'TOP_K': 5,                     # default recommendation count
    'RECOMMEND_CACHE_TTL': 300,     # 5 minutes per user
    'BESTSELLER_CACHE_TTL': 3600,   # 1 hour
    'BESTSELLER_COUNT': 20,         # pool size for cold start
    'COLD_START_DAYS': 30,          # days to look back for bestsellers

    # Model architecture (must match checkpoint)
    'EMBED_DIM_EVENT': 8,
    'EMBED_DIM_PRODUCT': 64,
    'EMBED_DIM_CATEGORY': 16,
    'EMBED_DIM_BRAND': 16,
    'LSTM_HIDDEN': 256,
    'LSTM_LAYERS': 2,
    'LSTM_DROPOUT': 0.2,

    # Training
    'TRAIN_EPOCHS': 50,
    'BATCH_SIZE': 64,
    'LEARNING_RATE': 1e-3,
    'WEIGHT_DECAY': 1e-5,
    'EARLY_STOPPING_PATIENCE': 5,
    'WINDOW_SIZE': 20,      # sliding window for ETL
    'WINDOW_STEP': 1,
    'TRAIN_RATIO': 0.70,
    'VAL_RATIO': 0.15,

    # Model versioning: keep N latest checkpoints
    'MAX_CHECKPOINTS_TO_KEEP': 3,

    # Rollback threshold: accept new model only if recall@5 >= old * this factor
    'ROLLBACK_THRESHOLD': 0.95,
}
