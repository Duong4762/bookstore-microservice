"""
PyTorch Dataset and DataLoader for next-product prediction.

Data format (CSV/Parquet from ETL):
    user_id | event_type_id | product_id | category_id | brand_id | target_product_id

Each row is one training sample:
    - event_type_id, product_id, category_id, brand_id: sequences (lists) of SEQ_LEN integers
    - target_product_id: ground-truth next product (integer)

Padding token = 0
"""
import ast
import logging
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader

logger = logging.getLogger(__name__)


class EventSequenceDataset(Dataset):
    """
    Loads pre-processed sequence data from a CSV/Parquet file.

    Expected columns:
        event_seq:    "[3,1,2,0,0]"  — list of event_type_ids (padded)
        product_seq:  "[55,89,0,0,0]"
        category_seq: "[3,3,0,0,0]"
        brand_seq:    "[7,7,0,0,0]"
        length:       5   — actual sequence length before padding
        target:       34  — target product_id (as vocab index)
    """

    def __init__(self, file_path: str | Path):
        self.path = Path(file_path)
        logger.info('Loading dataset from %s', self.path)

        if self.path.suffix == '.parquet':
            self.df = pd.read_parquet(self.path)
        else:
            self.df = pd.read_csv(self.path)

        # Parse list columns if stored as strings
        for col in ('event_seq', 'product_seq', 'category_seq', 'brand_seq'):
            if isinstance(self.df[col].iloc[0], str):
                self.df[col] = self.df[col].apply(ast.literal_eval)

        logger.info('Loaded %d samples', len(self.df))

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, ...]:
        row = self.df.iloc[idx]
        return (
            torch.tensor(row['event_seq'],    dtype=torch.long),
            torch.tensor(row['product_seq'],  dtype=torch.long),
            torch.tensor(row['category_seq'], dtype=torch.long),
            torch.tensor(row['brand_seq'],    dtype=torch.long),
            torch.tensor(row['length'],       dtype=torch.long),
            torch.tensor(row['target'],       dtype=torch.long),
        )


def collate_fn(batch):
    """
    Stack tensors in a batch. All sequences already have the same length
    (padded by ETL), so no dynamic padding needed here.
    Returns: event_t, product_t, category_t, brand_t, lengths_t, targets_t
    """
    (events, products, categories, brands, lengths, targets) = zip(*batch)
    return (
        torch.stack(events),
        torch.stack(products),
        torch.stack(categories),
        torch.stack(brands),
        torch.stack(lengths),
        torch.stack(targets),
    )


def build_dataloaders(
    train_path: str,
    val_path: str,
    test_path: str | None,
    batch_size: int = 64,
    num_workers: int = 0,
) -> tuple:
    """Build train/val(/test) DataLoaders."""
    train_ds = EventSequenceDataset(train_path)
    val_ds = EventSequenceDataset(val_path)

    train_loader = DataLoader(
        train_ds, batch_size=batch_size, shuffle=True,
        collate_fn=collate_fn, num_workers=num_workers, pin_memory=False,
    )
    val_loader = DataLoader(
        val_ds, batch_size=batch_size * 2, shuffle=False,
        collate_fn=collate_fn, num_workers=num_workers,
    )
    test_loader = None
    if test_path and Path(test_path).exists():
        test_ds = EventSequenceDataset(test_path)
        test_loader = DataLoader(
            test_ds, batch_size=batch_size * 2, shuffle=False,
            collate_fn=collate_fn, num_workers=num_workers,
        )

    logger.info(
        'DataLoaders: train=%d val=%d test=%d',
        len(train_ds), len(val_ds), len(test_ds) if test_loader else 0,
    )
    return train_loader, val_loader, test_loader
