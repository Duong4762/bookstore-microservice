"""
ETL Pipeline — transforms raw EventLog records into ML training sequences.

Steps:
1. Query EventLog from DB (configurable time range)
2. Sessionize: group events by user_id, sort by timestamp
3. Apply sliding window (size=WINDOW_SIZE, step=WINDOW_STEP)
4. For each window: input_seq = window[:-1], target = window[-1].product_id
5. Encode event_type / product_id / category_id / brand_id as integers (vocab)
6. Pad/truncate sequences to uniform length
7. Time-based split: train/val/test (70/15/15)
8. Export to Parquet files + vocab.json

Output files in data_dir/:
    vocab.json        — all integer mappings
    train.parquet
    val.parquet
    test.parquet
    etl_stats.json    — row counts, date ranges, run metadata
"""
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


# ── Constants ──────────────────────────────────────────────────────────────────

EVENT_TYPE_MAP = {
    'product_view':   1,
    'product_click':  2,
    'add_to_cart':    3,
    'purchase':       4,
    'search':         5,
}
PAD = 0
NUM_EVENTS = len(EVENT_TYPE_MAP)


# ── Main ETL function ──────────────────────────────────────────────────────────

def run_etl(
    data_dir: str | Path,
    vocab_path: str | Path,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    days: Optional[int] = None,
    min_seq_len: int = 2,
    dry_run: bool = False,
) -> dict:
    """
    Full ETL pipeline.

    Args:
        data_dir:       Where to write parquet + stats files
        vocab_path:     Where to write/update vocab.json
        start_date:     Earliest event timestamp (UTC)
        end_date:       Latest event timestamp (UTC, defaults to now)
        days:           Shortcut: use last N days (overrides start_date)
        min_seq_len:    Minimum events per user to include them
        dry_run:        If True, compute stats without writing files

    Returns:
        dict with stats: total_events, total_samples, train/val/test counts
    """
    data_dir = Path(data_dir)
    vocab_path = Path(vocab_path)
    ml = settings.ML_SETTINGS

    # ── Date range ────────────────────────────────────────────────────────
    if end_date is None:
        end_date = timezone.now()
    if days is not None:
        start_date = end_date - timedelta(days=days)

    logger.info('ETL start_date=%s end_date=%s', start_date, end_date)

    # ── Query DB ──────────────────────────────────────────────────────────
    from apps.tracking.models import EventLog
    qs = EventLog.objects.filter(product_id__isnull=False).order_by('user_id', 'timestamp')
    if start_date:
        qs = qs.filter(timestamp__gte=start_date)
    if end_date:
        qs = qs.filter(timestamp__lte=end_date)

    logger.info('Querying events...')
    df = pd.DataFrame(list(qs.values(
        'user_id', 'product_id', 'category_id', 'brand_id', 'event_type', 'timestamp'
    )))

    if df.empty:
        logger.warning('No events found for the given date range.')
        return {'total_events': 0, 'total_samples': 0}

    logger.info('Loaded %d raw events from %d users', len(df), df['user_id'].nunique())

    # ── Fill null  IDs with 0 (will be encoded as PAD) ───────────────────
    df['category_id'] = df['category_id'].fillna(0).astype(int)
    df['brand_id'] = df['brand_id'].fillna(0).astype(int)

    # ── Build vocab ───────────────────────────────────────────────────────
    vocab = _build_vocab(df)
    logger.info(
        'Vocab: products=%d categories=%d brands=%d',
        vocab['num_products'], vocab['num_categories'], vocab['num_brands'],
    )

    # ── Encode ────────────────────────────────────────────────────────────
    df['event_type_id'] = df['event_type'].map(EVENT_TYPE_MAP).fillna(0).astype(int)
    df['product_enc'] = df['product_id'].astype(str).map(vocab['product2id']).fillna(0).astype(int)
    df['category_enc'] = df['category_id'].astype(str).map(vocab['category2id']).fillna(0).astype(int)
    df['brand_enc'] = df['brand_id'].astype(str).map(vocab['brand2id']).fillna(0).astype(int)

    # ── Sliding window per user ───────────────────────────────────────────
    window_size = ml['WINDOW_SIZE']
    window_step = ml['WINDOW_STEP']
    samples = []

    for user_id, user_df in df.groupby('user_id'):
        user_df = user_df.sort_values('timestamp')
        if len(user_df) < min_seq_len + 1:
            continue

        ev = user_df['event_type_id'].tolist()
        pr = user_df['product_enc'].tolist()
        ca = user_df['category_enc'].tolist()
        br = user_df['brand_enc'].tolist()
        ts = user_df['timestamp'].tolist()

        # Sliding window
        for i in range(0, len(ev) - 1, window_step):
            end_idx = min(i + window_size, len(ev) - 1)
            if end_idx - i < 1:
                continue

            seq_ev = ev[i:end_idx]
            seq_pr = pr[i:end_idx]
            seq_ca = ca[i:end_idx]
            seq_br = br[i:end_idx]
            target = pr[end_idx]   # next product to predict

            if target == PAD:
                continue  # skip if target has no product

            # Pad to window_size
            actual_len = len(seq_ev)
            pad_len = window_size - actual_len
            seq_ev = [PAD] * pad_len + seq_ev
            seq_pr = [PAD] * pad_len + seq_pr
            seq_ca = [PAD] * pad_len + seq_ca
            seq_br = [PAD] * pad_len + seq_br

            samples.append({
                'user_id': user_id,
                'timestamp': ts[end_idx],
                'event_seq': seq_ev,
                'product_seq': seq_pr,
                'category_seq': seq_ca,
                'brand_seq': seq_br,
                'length': actual_len,
                'target': target,
            })

    logger.info('Generated %d training samples', len(samples))

    if not samples:
        return {'total_events': len(df), 'total_samples': 0}

    samples_df = pd.DataFrame(samples)
    samples_df = samples_df.sort_values('timestamp')

    # ── Time-based split ──────────────────────────────────────────────────
    n = len(samples_df)
    train_end = int(n * ml['TRAIN_RATIO'])
    val_end = int(n * (ml['TRAIN_RATIO'] + ml['VAL_RATIO']))

    train_df = samples_df.iloc[:train_end]
    val_df = samples_df.iloc[train_end:val_end]
    test_df = samples_df.iloc[val_end:]

    stats = {
        'total_events': len(df),
        'total_samples': n,
        'train': len(train_df),
        'val': len(val_df),
        'test': len(test_df),
        'num_users': df['user_id'].nunique(),
        'num_products': vocab['num_products'],
        'date_from': str(start_date),
        'date_to': str(end_date),
        'run_at': datetime.now().isoformat(),
    }

    if dry_run:
        logger.info('Dry run mode — no files written. Stats: %s', stats)
        return stats

    # ── Write files ───────────────────────────────────────────────────────
    data_dir.mkdir(parents=True, exist_ok=True)
    vocab_path.parent.mkdir(parents=True, exist_ok=True)

    train_df.to_parquet(data_dir / 'train.parquet', index=False)
    val_df.to_parquet(data_dir / 'val.parquet', index=False)
    test_df.to_parquet(data_dir / 'test.parquet', index=False)

    with open(vocab_path, 'w') as f:
        json.dump(vocab, f, indent=2)

    with open(data_dir / 'etl_stats.json', 'w') as f:
        json.dump(stats, f, indent=2)

    logger.info(
        'ETL complete. train=%d val=%d test=%d | vocab written to %s',
        len(train_df), len(val_df), len(test_df), vocab_path,
    )
    return stats


# ── Vocab builder ──────────────────────────────────────────────────────────────

def _build_vocab(df: pd.DataFrame) -> dict:
    """
    Build integer mappings for product_id, category_id, brand_id.
    Index 0 is always reserved for PAD.
    """
    products = sorted(df['product_id'].dropna().unique().astype(str))
    categories = sorted(df['category_id'].dropna().unique().astype(str))
    brands = sorted(df['brand_id'].dropna().unique().astype(str))

    # Start from 1 (0 = PAD)
    product2id = {p: i + 1 for i, p in enumerate(products)}
    category2id = {c: i + 1 for i, c in enumerate(categories)}
    brand2id = {b: i + 1 for i, b in enumerate(brands)}

    return {
        'num_events': NUM_EVENTS,
        'num_products': len(products),
        'num_categories': len(categories),
        'num_brands': len(brands),
        'event2id': {k: v for k, v in EVENT_TYPE_MAP.items()},
        'product2id': product2id,
        'category2id': category2id,
        'brand2id': brand2id,
    }
