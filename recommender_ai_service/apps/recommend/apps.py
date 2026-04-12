"""
Recommend app — loads ML model on startup and runs inference.
"""
import logging
import os

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class RecommendConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.recommend'
    verbose_name = 'AI Recommendation'

    def ready(self):
        """
        Load the trained PyTorch model into memory when Django starts.
        Skipped when DJANGO_SKIP_ML_LOAD=1 (Celery workers, migrations, tests).
        """
        if os.environ.get('DJANGO_SKIP_ML_LOAD'):
            logger.info('ML model loading skipped (DJANGO_SKIP_ML_LOAD set)')
            return

        # Only load in the main Django process, not during autoreload child spawn
        if os.environ.get('RUN_MAIN') == 'true' or not os.environ.get('RUN_MAIN'):
            try:
                from ml.inference import ModelLoader
                loader = ModelLoader.instance()
                if loader.is_ready:
                    logger.info('✅ ML Model loaded successfully')
                else:
                    logger.warning('⚠️  ML Model not available — cold start fallback active')
            except Exception as exc:
                logger.error('❌ ML Model failed to load: %s', exc, exc_info=True)
