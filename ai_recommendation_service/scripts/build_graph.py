#!/usr/bin/env python
"""CLI: chỉ dựng graph từ DB và lưu pickle (NetworkX)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

import django

django.setup()

from recommendation.services.graph_builder import GraphBuilder
from recommendation.services.graph_storage import NetworkXGraphStorage


def main() -> None:
    b = GraphBuilder(NetworkXGraphStorage())
    b.build_from_database(full_rebuild=True)
    b.save()
    print('OK: graph saved')


if __name__ == '__main__':
    main()
