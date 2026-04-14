#!/usr/bin/env python
"""CLI: chỉ build lại FAISS từ checkpoint + heterodata hiện có."""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

import django

django.setup()

import torch
from django.conf import settings

from recommendation.services.trainer import build_faiss_from_best_checkpoint
from recommendation.services.graph_preprocess import load_heterodata_bundle


def main() -> None:
    ml = settings.RECOMMENDATION_ML
    if not Path(ml['MODEL_PATH']).exists():
        print('Thiếu gnn_model.pt')
        sys.exit(1)
    device = torch.device('cuda' if torch.cuda.is_available() and ml['USE_CUDA'] else 'cpu')
    data, mappings = load_heterodata_bundle(Path(ml['HETERODATA_PATH']))
    build_faiss_from_best_checkpoint(data, mappings, device)
    print('OK: FAISS index')


if __name__ == '__main__':
    main()
