"""Chạy toàn bộ pipeline huấn luyện (graph → preprocess → GNN → FAISS)."""
import logging

from django.core.management.base import BaseCommand

from recommendation.services.inference import RecommendEngine
from recommendation.services.trainer import run_full_training_pipeline

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Rebuild knowledge graph, train heterogeneous GraphSAGE (BPR), rebuild FAISS index'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Bắt đầu pipeline huấn luyện...'))
        try:
            result = run_full_training_pipeline()
            self.stdout.write(self.style.SUCCESS(str(result)))
            RecommendEngine.reload()
            self.stdout.write(self.style.SUCCESS('Đã reload RecommendEngine.'))
        except Exception as exc:
            logger.exception('train_recommendation failed')
            self.stderr.write(self.style.ERROR(str(exc)))
            raise
