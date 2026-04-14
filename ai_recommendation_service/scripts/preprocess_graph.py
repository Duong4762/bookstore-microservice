#!/usr/bin/env python
"""CLI: load graph.pkl → HeteroData + mappings → heterodata.pt"""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

import django

django.setup()

from django.conf import settings

from recommendation.services.graph_builder import GraphBuilder
from recommendation.services.graph_preprocess import save_heterodata, storage_to_heterodata
from recommendation.services.graph_storage import NetworkXGraphStorage


def main() -> None:
    ml = settings.RECOMMENDATION_ML
    b = GraphBuilder(NetworkXGraphStorage())
    p = Path(ml['GRAPH_PICKLE_PATH'])
    if not p.exists():
        print('Thiếu graph pickle — chạy trước scripts/build_graph.py')
        sys.exit(1)
    b.load(str(p))
    data, mappings = storage_to_heterodata(b.storage)
    save_heterodata(data, mappings, Path(ml['HETERODATA_PATH']), Path(ml['MAPPINGS_JSON_PATH']))
    print('OK: heterodata.pt + mappings.json')


if __name__ == '__main__':
    main()
