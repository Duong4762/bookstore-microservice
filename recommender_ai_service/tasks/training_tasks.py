"""
Celery tasks for nightly model retraining pipeline.

Tasks:
    nightly_etl_and_train  — runs at 2AM: ETL + train + reload model
    check_data_drift       — runs every 6h: detect when retraining is needed

Retraining flow:
    1. run_etl() → export fresh parquet + update vocab.json
    2. train()   → train new model, save checkpoint
    3. Compare recall@5 against current production model
    4. If new >= old * ROLLBACK_THRESHOLD → reload; else keep old
    5. Invalidate all user recommendation caches
"""
import json
import logging
from pathlib import Path

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name='tasks.training_tasks.nightly_etl_and_train', bind=True, max_retries=1)
def nightly_etl_and_train(self):
    """
    Nightly job: ETL → train → deploy new model.
    Runs at 2AM via Celery Beat.
    """
    logger.info('🌙 Nightly ETL + Train pipeline started')

    from django.conf import settings
    ml = settings.ML_SETTINGS

    # ── Step 1: ETL ───────────────────────────────────────────────────────
    try:
        from etl.pipeline import run_etl
        etl_stats = run_etl(
            data_dir=ml['DATA_DIR'],
            vocab_path=ml['VOCAB_PATH'],
            days=90,               # use last 90 days of data
            min_seq_len=2,
        )
        logger.info('ETL complete: %s', etl_stats)

        if etl_stats.get('total_samples', 0) < 100:
            logger.warning('Too few samples (%d) — skipping training', etl_stats.get('total_samples', 0))
            return {'status': 'skipped', 'reason': 'insufficient_data', 'etl': etl_stats}

    except Exception as exc:
        logger.error('ETL failed: %s', exc, exc_info=True)
        raise self.retry(exc=exc, countdown=1800)

    # ── Step 2: Get recall@5 of current model ─────────────────────────────
    old_recall = _get_current_model_recall()

    # ── Step 3: Train new model ───────────────────────────────────────────
    try:
        from ml.train import train
        new_metrics = train(
            data_dir=ml['DATA_DIR'],
            checkpoint_dir=ml['CHECKPOINT_DIR'],
            vocab_path=ml['VOCAB_PATH'],
            epochs=ml['TRAIN_EPOCHS'],
            batch_size=ml['BATCH_SIZE'],
            lr=ml['LEARNING_RATE'],
            weight_decay=ml['WEIGHT_DECAY'],
            patience=ml['EARLY_STOPPING_PATIENCE'],
            device_str='auto',
            max_keep=ml['MAX_CHECKPOINTS_TO_KEEP'],
        )
        new_recall = new_metrics.get('recall@5', 0.0)
        logger.info('New model recall@5=%.4f (old=%.4f)', new_recall, old_recall)

    except Exception as exc:
        logger.error('Training failed: %s', exc, exc_info=True)
        return {'status': 'error', 'phase': 'training', 'message': str(exc)}

    # ── Step 4: Rollback check ────────────────────────────────────────────
    threshold = ml['ROLLBACK_THRESHOLD']
    if old_recall > 0 and new_recall < old_recall * threshold:
        logger.warning(
            'New model (%.4f) below rollback threshold (%.4f × %.2f = %.4f). Keeping old.',
            new_recall, old_recall, threshold, old_recall * threshold,
        )
        # Remove the just-saved checkpoint that failed the bar
        _remove_latest_checkpoint(ml['CHECKPOINT_DIR'])
        return {
            'status': 'rolled_back',
            'old_recall': old_recall,
            'new_recall': new_recall,
        }

    # ── Step 5: Reload model in Django process ────────────────────────────
    try:
        from ml.inference import ModelLoader
        ModelLoader.instance().reload()
        logger.info('✅ Model reloaded successfully')
    except Exception as exc:
        logger.error('Model reload failed: %s', exc, exc_info=True)

    # ── Step 6: Invalidate all user caches ────────────────────────────────
    try:
        from django.core.cache import cache
        cache.delete_pattern('recommender:rec:user:*')
        logger.info('User recommendation caches invalidated')
    except Exception as exc:
        logger.warning('Cache invalidation failed (non-fatal): %s', exc)

    return {
        'status': 'ok',
        'old_recall@5': old_recall,
        'new_recall@5': new_recall,
        'metrics': new_metrics,
        'etl': etl_stats,
    }


@shared_task(name='tasks.training_tasks.check_data_drift')
def check_data_drift():
    """
    Detect whether the distribution of incoming events has drifted
    significantly from the training data distribution.

    Compares event_type distribution from last 24h vs last 7-day baseline.
    If JS divergence > threshold → trigger retraining.
    """
    try:
        from datetime import timedelta
        from django.db.models import Count
        from django.utils import timezone
        from apps.tracking.models import EventLog

        now = timezone.now()
        event_types = ['product_view', 'product_click', 'add_to_cart', 'purchase', 'search']

        def get_dist(since):
            counts = {e: 0 for e in event_types}
            rows = (
                EventLog.objects
                .filter(timestamp__gte=since)
                .values('event_type')
                .annotate(cnt=Count('id'))
            )
            total = 0
            for row in rows:
                if row['event_type'] in counts:
                    counts[row['event_type']] = row['cnt']
                    total += row['cnt']
            if total == 0:
                return {e: 1 / len(event_types) for e in event_types}
            return {e: counts[e] / total for e in event_types}

        dist_24h = get_dist(now - timedelta(hours=24))
        dist_7d = get_dist(now - timedelta(days=7))

        # Jensen-Shannon divergence (simplified)
        import numpy as np
        p = np.array([dist_24h[e] for e in event_types])
        q = np.array([dist_7d[e] for e in event_types])
        m = (p + q) / 2
        # Clip to avoid log(0)
        p = np.clip(p, 1e-10, 1)
        q = np.clip(q, 1e-10, 1)
        m = np.clip(m, 1e-10, 1)
        js_div = 0.5 * np.sum(p * np.log(p / m)) + 0.5 * np.sum(q * np.log(q / m))

        logger.info('Data drift check: JS divergence=%.4f', js_div)

        DRIFT_THRESHOLD = 0.15
        if js_div > DRIFT_THRESHOLD:
            logger.warning(
                'Data drift detected (JS=%.4f > %.2f) — triggering retraining',
                js_div, DRIFT_THRESHOLD,
            )
            nightly_etl_and_train.delay()

        return {'js_divergence': float(js_div), 'drifted': js_div > DRIFT_THRESHOLD}

    except Exception as exc:
        logger.error('Drift detection failed: %s', exc, exc_info=True)
        return {'status': 'error', 'message': str(exc)}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_current_model_recall() -> float:
    """Get recall@5 of the currently loaded model from the latest checkpoint."""
    try:
        from django.conf import settings
        checkpoint_dir = Path(settings.ML_SETTINGS['CHECKPOINT_DIR'])
        checkpoints = sorted(checkpoint_dir.glob('model_v*.pt'), key=lambda p: p.stat().st_mtime, reverse=True)
        if not checkpoints:
            return 0.0
        import torch
        ckpt = torch.load(checkpoints[0], map_location='cpu')
        return float(ckpt.get('recall_at_5', 0.0))
    except Exception:
        return 0.0


def _remove_latest_checkpoint(checkpoint_dir):
    """Remove the most recently saved checkpoint (failed rollback check)."""
    try:
        checkpoints = sorted(
            Path(checkpoint_dir).glob('model_v*.pt'),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if checkpoints:
            checkpoints[0].unlink()
            logger.info('Removed failed checkpoint: %s', checkpoints[0].name)
    except Exception as exc:
        logger.warning('Failed to remove checkpoint: %s', exc)
