from .base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = ['*']

REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {  # type: ignore[index]
    'anon': '10000/min',
    'event_collector': '10000/min',
    'chat': '10000/min',  # ScopedRateThrottle cho POST /api/chat/ (môi trường dev: giới hạn rộng)
}
