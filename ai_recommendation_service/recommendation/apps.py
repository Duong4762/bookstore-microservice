from django.apps import AppConfig


class RecommendationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'recommendation'

    def ready(self):
        from .services.scheduler import start_scheduler_if_needed

        start_scheduler_if_needed()
