#!/usr/bin/env python
"""CLI: huấn luyện GNN từ heterodata.pt (không rebuild graph)."""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

import django

django.setup()

import torch
from django.conf import settings

from recommendation.services.trainer import build_faiss_from_best_checkpoint, train_gnn
from recommendation.services.graph_preprocess import load_heterodata_bundle


def main() -> None:
    ml = settings.RECOMMENDATION_ML
    bundle = Path(ml['HETERODATA_PATH'])
    if not bundle.exists():
        print('Thiếu heterodata.pt — chạy preprocess_graph.py')
        sys.exit(1)
    device = torch.device('cuda' if torch.cuda.is_available() and ml['USE_CUDA'] else 'cpu')
    data, mappings = load_heterodata_bundle(bundle)
    data = data.to(device)
    train_gnn(
        data,
        mappings,
        epochs=int(ml['TRAIN_EPOCHS']),
        lr=float(ml['LEARNING_RATE']),
        device=device,
        val_ratio=float(ml['VAL_RATIO']),
    )
    data_cpu, mappings = load_heterodata_bundle(bundle)
    build_faiss_from_best_checkpoint(data_cpu, mappings, device)
    print('OK: model + FAISS')


if __name__ == '__main__':
    main()
