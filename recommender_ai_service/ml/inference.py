"""
ModelLoader — singleton that holds the trained PyTorch model in memory.

Loaded once in AppConfig.ready() when Django starts.
All recommendation requests share the same in-memory model instance.

Thread-safe for inference (PyTorch model.eval() is GIL-safe for CPU inference;
for GPU, torch.no_grad() ensures no grad accumulation).
"""
import json
import logging
import threading
from pathlib import Path
from typing import List, Optional

import torch

logger = logging.getLogger(__name__)

_PAD = 0


class ModelLoader:
    """
    Singleton model loader.

    Usage:
        loader = ModelLoader.instance()
        if loader.is_ready:
            product_ids = loader.predict(events, top_k=5)
    """

    _instance: Optional['ModelLoader'] = None
    _lock = threading.Lock()

    def __init__(self):
        self._model = None
        self._vocab: Optional[dict] = None
        self._event2id: dict = {}
        self._product2id: dict = {}
        self._category2id: dict = {}
        self._brand2id: dict = {}
        self._id2product: dict = {}
        self._device = torch.device('cpu')

    @classmethod
    def instance(cls) -> 'ModelLoader':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._instance._load()
        return cls._instance

    # ── Load ──────────────────────────────────────────────────────────────

    def _load(self) -> None:
        """Find latest checkpoint and load model + vocab into memory."""
        from django.conf import settings
        ml = settings.ML_SETTINGS

        checkpoint_dir = Path(ml['CHECKPOINT_DIR'])
        vocab_path = Path(ml['VOCAB_PATH'])

        # Vocab
        if not vocab_path.exists():
            logger.warning('Vocab not found at %s — no model loaded', vocab_path)
            return
        with open(vocab_path) as f:
            self._vocab = json.load(f)
        self._build_lookup_tables()

        # Latest checkpoint by modified time
        checkpoints = sorted(
            checkpoint_dir.glob('model_v*.pt'),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not checkpoints:
            logger.warning('No checkpoint found in %s — cold start only', checkpoint_dir)
            return

        latest = checkpoints[0]
        logger.info('Loading model checkpoint: %s', latest.name)

        try:
            from ml.model import NextProductPredictor
            ckpt = torch.load(latest, map_location='cpu')
            model_config = ckpt['model_config']
            model = NextProductPredictor(self._vocab, model_config)
            model.load_state_dict(ckpt['model_state_dict'])
            model.eval()
            self._model = model
            logger.info(
                'Model ready | recall@5=%.4f | epoch=%d',
                ckpt.get('recall_at_5', 0.0),
                ckpt.get('epoch', -1),
            )
        except Exception as exc:
            logger.error('Failed to load model: %s', exc, exc_info=True)
            self._model = None

    def _build_lookup_tables(self) -> None:
        """Pre-build encoded→decoded lookup for fast inference."""
        v = self._vocab
        self._event2id = v.get('event2id', {})
        self._product2id = v.get('product2id', {})
        self._category2id = v.get('category2id', {})
        self._brand2id = v.get('brand2id', {})
        # Decode: vocab index → original product_id
        self._id2product = {int(idx): int(pid) for pid, idx in self._product2id.items()}

    def reload(self) -> None:
        """Force-reload model after retraining (called from Celery task)."""
        with self._lock:
            logger.info('Reloading ML model...')
            self._model = None
            self._vocab = None
            self._load()

    # ── Inference ─────────────────────────────────────────────────────────

    @property
    def is_ready(self) -> bool:
        return self._model is not None and self._vocab is not None

    def predict(self, event_sequence: List[dict], top_k: int = 5) -> List[int]:
        """
        Run inference for a user's event sequence.

        Args:
            event_sequence: list of dicts, each with keys:
                event_type (str), product_id (int|None),
                category_id (int|None), brand_id (int|None)
            top_k: number of products to return

        Returns:
            List of original product_ids (decoded from vocab), length <= top_k.
            Returns [] if model not ready.
        """
        if not self.is_ready:
            return []

        from django.conf import settings
        seq_len = settings.ML_SETTINGS['SEQUENCE_LENGTH']

        # Take last seq_len events (most recent)
        seq = event_sequence[-seq_len:]
        actual_length = len(seq)

        # Left-pad with empty events (PAD = 0)
        pad_event = {'event_type': None, 'product_id': None, 'category_id': None, 'brand_id': None}
        while len(seq) < seq_len:
            seq.insert(0, pad_event)

        # Encode each step
        event_ids    = [self._event2id.get(str(e.get('event_type')), _PAD) for e in seq]
        product_ids  = [self._product2id.get(str(e.get('product_id')), _PAD) for e in seq]
        category_ids = [self._category2id.get(str(e.get('category_id')), _PAD) for e in seq]
        brand_ids    = [self._brand2id.get(str(e.get('brand_id')), _PAD) for e in seq]

        # Build tensors (batch=1)
        ev_t  = torch.tensor([event_ids],    dtype=torch.long)
        pr_t  = torch.tensor([product_ids],  dtype=torch.long)
        ca_t  = torch.tensor([category_ids], dtype=torch.long)
        br_t  = torch.tensor([brand_ids],    dtype=torch.long)
        ln_t  = torch.tensor([actual_length], dtype=torch.long)

        with torch.no_grad():
            top_indices, _ = self._model.predict_top_k(ev_t, pr_t, ca_t, br_t, ln_t, k=top_k)

        # Decode vocab indices → original product_ids
        results = []
        for vocab_idx in top_indices[0].tolist():
            if vocab_idx in self._id2product:
                results.append(self._id2product[vocab_idx])

        return results[:top_k]
