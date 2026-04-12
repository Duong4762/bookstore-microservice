"""
Celery tasks for ETL-related periodic jobs.

Tasks:
    update_bestsellers_cache — runs every hour to refresh cold-start pool
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name='tasks.etl_tasks.update_bestsellers_cache', bind=True, max_retries=3)
def update_bestsellers_cache(self):
    """
    Recompute bestselling products from EventLog and refresh the Redis cache.
    Runs every hour via Celery Beat.
    """
    try:
        logger.info('Updating bestsellers cache...')
        from apps.recommend.services import RecommendationService
        service = RecommendationService()
        bestsellers = service._compute_bestsellers()

        if bestsellers:
            service.cache.set_bestsellers(bestsellers)
            logger.info('Bestsellers cache updated: %d products', len(bestsellers))
        else:
            logger.warning('No bestsellers found in event logs')

        return {'status': 'ok', 'count': len(bestsellers)}

    except Exception as exc:
        logger.error('update_bestsellers_cache failed: %s', exc, exc_info=True)
        raise self.retry(exc=exc, countdown=300)  # retry in 5 minutes


@shared_task(name='tasks.etl_tasks.compute_trending')
def compute_trending():
    """
    Compute trending products from the last 7 days (view + click weighted).
    Less strict than bestsellers — uses engagement signals, not just purchases.
    """
    try:
        from datetime import timedelta
        from django.db.models import Count
        from django.utils import timezone
        from apps.tracking.models import EventLog
        from apps.recommend.cache import RecommendCache

        since = timezone.now() - timedelta(days=7)
        weights = {'product_view': 1, 'product_click': 2, 'add_to_cart': 3, 'purchase': 5}

        # Score each product by weighted event count
        trending_map = {}
        for event_type, weight in weights.items():
            rows = (
                EventLog.objects
                .filter(event_type=event_type, timestamp__gte=since, product_id__isnull=False)
                .values('product_id')
                .annotate(cnt=Count('id'))
            )
            for row in rows:
                pid = row['product_id']
                trending_map[pid] = trending_map.get(pid, 0) + row['cnt'] * weight

        sorted_products = sorted(trending_map, key=trending_map.get, reverse=True)[:20]

        cache = RecommendCache()
        cache.set_trending(sorted_products)
        logger.info('Trending updated: %d products', len(sorted_products))

        return {'status': 'ok', 'count': len(sorted_products)}

    except Exception as exc:
        logger.error('compute_trending failed: %s', exc, exc_info=True)
        return {'status': 'error', 'message': str(exc)}
