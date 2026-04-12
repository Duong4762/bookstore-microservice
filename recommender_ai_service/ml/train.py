"""
Production training pipeline for NextProductPredictor.

Features:
- CrossEntropyLoss + Adam + LR scheduler (ReduceLROnPlateau)
- Early stopping (patience configurable)
- Checkpoint save with full metadata (epoch, loss, recall@5, config)
- Resume training from checkpoint
- Automatic model versioning (keep N latest checkpoints)
- Evaluation with Recall@5, Recall@10, MRR, NDCG metrics

Usage (via Django management command):
    python manage.py train_model --epochs 50 --batch-size 64
    python manage.py train_model --resume ml/checkpoints/model_v3.pt

Or directly:
    python -m ml.train --data-dir ml/data --epochs 50
"""
import json
import logging
import time
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
from torch.optim import Adam
from torch.optim.lr_scheduler import ReduceLROnPlateau
from torch.utils.data import DataLoader

from .dataset import build_dataloaders
from .metrics import compute_all_metrics
from .model import NextProductPredictor, build_model_config

logger = logging.getLogger(__name__)


# ── Early Stopping ─────────────────────────────────────────────────────────────

class EarlyStopping:
    """Tracks val loss and signals when to stop training."""

    def __init__(self, patience: int = 5, min_delta: float = 1e-4):
        self.patience = patience
        self.min_delta = min_delta
        self.best_loss = float('inf')
        self.counter = 0
        self.should_stop = False

    def __call__(self, val_loss: float) -> bool:
        if val_loss < self.best_loss - self.min_delta:
            self.best_loss = val_loss
            self.counter = 0
        else:
            self.counter += 1
            logger.info('EarlyStopping: %d/%d', self.counter, self.patience)
            if self.counter >= self.patience:
                self.should_stop = True
        return self.should_stop


# ── Checkpoint helpers ─────────────────────────────────────────────────────────

def save_checkpoint(
    model: NextProductPredictor,
    optimizer: Adam,
    epoch: int,
    metrics: dict,
    vocab: dict,
    checkpoint_dir: Path,
    max_keep: int = 3,
) -> Path:
    """
    Save model checkpoint.
    Filename: model_v{n}_epoch{e}_r5_{recall5:.4f}.pt
    Keeps only the last `max_keep` checkpoints to avoid disk bloat.
    """
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    r5 = metrics.get('recall@5', 0.0)
    version = int(time.time())
    filename = f"model_v{version}_epoch{epoch}_r5_{r5:.4f}.pt"
    path = checkpoint_dir / filename

    torch.save({
        'epoch': epoch,
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'model_config': model.config,
        'vocab': vocab,
        'metrics': metrics,
        'recall_at_5': r5,
    }, path)

    logger.info('Checkpoint saved: %s', path.name)

    # Prune old checkpoints
    checkpoints = sorted(checkpoint_dir.glob('model_v*.pt'), key=lambda p: p.stat().st_mtime)
    while len(checkpoints) > max_keep:
        old = checkpoints.pop(0)
        old.unlink()
        logger.info('Removed old checkpoint: %s', old.name)

    return path


def load_checkpoint(path: str | Path, device: str = 'cpu') -> dict:
    """Load a saved checkpoint dict."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f'Checkpoint not found: {path}')
    return torch.load(path, map_location=device)


# ── Training loop ──────────────────────────────────────────────────────────────

def train_one_epoch(
    model: NextProductPredictor,
    loader: DataLoader,
    optimizer: Adam,
    criterion: nn.CrossEntropyLoss,
    device: torch.device,
) -> float:
    """Run one epoch, return average training loss."""
    model.train()
    total_loss = 0.0
    n_batches = 0

    for events, products, categories, brands, lengths, targets in loader:
        events     = events.to(device)
        products   = products.to(device)
        categories = categories.to(device)
        brands     = brands.to(device)
        lengths    = lengths.to(device)
        targets    = targets.to(device)

        optimizer.zero_grad()
        logits = model(events, products, categories, brands, lengths)
        loss = criterion(logits, targets)
        loss.backward()

        # Gradient clipping to prevent exploding gradients in LSTM
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()

        total_loss += loss.item()
        n_batches += 1

    return total_loss / max(n_batches, 1)


@torch.no_grad()
def evaluate(
    model: NextProductPredictor,
    loader: DataLoader,
    criterion: nn.CrossEntropyLoss,
    device: torch.device,
    k: int = 10,
) -> dict:
    """Evaluate on a DataLoader; return loss + ranking metrics."""
    model.eval()
    total_loss = 0.0
    n_batches = 0
    all_preds = []
    all_targets = []

    for events, products, categories, brands, lengths, targets in loader:
        events     = events.to(device)
        products   = products.to(device)
        categories = categories.to(device)
        brands     = brands.to(device)
        lengths    = lengths.to(device)
        targets_d  = targets.to(device)

        logits = model(events, products, categories, brands, lengths)
        loss = criterion(logits, targets_d)
        total_loss += loss.item()
        n_batches += 1

        # Mask PAD
        logits[:, 0] = float('-inf')
        _, top_k_indices = torch.topk(logits, k=k, dim=-1)
        all_preds.append(top_k_indices.cpu().numpy())
        all_targets.append(targets.numpy())

    all_preds = np.concatenate(all_preds, axis=0)
    all_targets = np.concatenate(all_targets, axis=0)

    metrics = compute_all_metrics(all_preds, all_targets)
    metrics['val_loss'] = total_loss / max(n_batches, 1)
    return metrics


# ── Main training function ─────────────────────────────────────────────────────

def train(
    data_dir: str | Path,
    checkpoint_dir: str | Path,
    vocab_path: str | Path,
    epochs: int = 50,
    batch_size: int = 64,
    lr: float = 1e-3,
    weight_decay: float = 1e-5,
    patience: int = 5,
    device_str: str = 'auto',
    resume_checkpoint: Optional[str] = None,
    max_keep: int = 3,
) -> dict:
    """
    Full training pipeline.

    Args:
        data_dir:            Directory with train.parquet, val.parquet, test.parquet
        checkpoint_dir:      Where to save model .pt files
        vocab_path:          Path to vocab.json (created by ETL)
        epochs:              Max training epochs
        batch_size:          Training batch size
        lr:                  Adam learning rate
        weight_decay:        L2 regularisation
        patience:            Early stopping patience
        device_str:          'auto' | 'cpu' | 'cuda' | 'mps'
        resume_checkpoint:   Path to checkpoint .pt to resume from
        max_keep:            Number of checkpoints to retain

    Returns:
        dict of final metrics on validation set
    """
    data_dir = Path(data_dir)
    checkpoint_dir = Path(checkpoint_dir)
    vocab_path = Path(vocab_path)

    # ── Device ────────────────────────────────────────────────────────────
    if device_str == 'auto':
        if torch.cuda.is_available():
            device = torch.device('cuda')
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            device = torch.device('mps')
        else:
            device = torch.device('cpu')
    else:
        device = torch.device(device_str)
    logger.info('Training on device: %s', device)

    # ── Vocab ─────────────────────────────────────────────────────────────
    if not vocab_path.exists():
        raise FileNotFoundError(f'Vocab not found: {vocab_path}. Run ETL first.')
    with open(vocab_path) as f:
        vocab = json.load(f)
    logger.info(
        'Vocab: %d products, %d categories, %d brands, %d event types',
        vocab['num_products'], vocab['num_categories'], vocab['num_brands'], vocab['num_events'],
    )

    # ── Data ──────────────────────────────────────────────────────────────
    train_loader, val_loader, test_loader = build_dataloaders(
        data_dir / 'train.parquet',
        data_dir / 'val.parquet',
        data_dir / 'test.parquet',
        batch_size=batch_size,
    )

    # ── Model ─────────────────────────────────────────────────────────────
    from django.conf import settings as django_settings
    config = build_model_config(django_settings.ML_SETTINGS)
    model = NextProductPredictor(vocab, config).to(device)
    logger.info('Model parameters: %s', f'{sum(p.numel() for p in model.parameters()):,}')

    optimizer = Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    scheduler = ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=2, verbose=True)
    criterion = nn.CrossEntropyLoss(ignore_index=0)  # ignore PAD target
    early_stopping = EarlyStopping(patience=patience)

    start_epoch = 0

    # ── Resume ────────────────────────────────────────────────────────────
    if resume_checkpoint:
        ckpt = load_checkpoint(resume_checkpoint, device=str(device))
        model.load_state_dict(ckpt['model_state_dict'])
        optimizer.load_state_dict(ckpt['optimizer_state_dict'])
        start_epoch = ckpt['epoch'] + 1
        logger.info('Resumed from epoch %d', start_epoch)

    best_metrics = {}

    # ── Training loop ─────────────────────────────────────────────────────
    for epoch in range(start_epoch, epochs):
        t0 = time.perf_counter()
        train_loss = train_one_epoch(model, train_loader, optimizer, criterion, device)
        val_metrics = evaluate(model, val_loader, criterion, device)
        elapsed = time.perf_counter() - t0

        logger.info(
            'Epoch %03d/%d | train_loss=%.4f | val_loss=%.4f | '
            'recall@5=%.4f | recall@10=%.4f | mrr@5=%.4f | %.1fs',
            epoch + 1, epochs,
            train_loss, val_metrics['val_loss'],
            val_metrics['recall@5'], val_metrics['recall@10'], val_metrics['mrr@5'],
            elapsed,
        )

        scheduler.step(val_metrics['val_loss'])

        # Save best checkpoint
        if not best_metrics or val_metrics['recall@5'] > best_metrics.get('recall@5', 0):
            best_metrics = val_metrics.copy()
            save_checkpoint(model, optimizer, epoch, val_metrics, vocab, checkpoint_dir, max_keep)

        if early_stopping(val_metrics['val_loss']):
            logger.info('Early stopping at epoch %d', epoch + 1)
            break

    # ── Final test evaluation ──────────────────────────────────────────────
    if test_loader:
        test_metrics = evaluate(model, test_loader, criterion, device)
        logger.info('Test metrics: %s', test_metrics)
        best_metrics['test'] = test_metrics

    return best_metrics
