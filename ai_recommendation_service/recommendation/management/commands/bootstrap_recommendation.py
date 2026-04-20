"""Bootstrap recommender: import bundled dataset and train BiLSTM."""
from __future__ import annotations

import csv
import hashlib
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from recommendation.services.inference import RecommendEngine
from recommendation.services.trainer import run_full_training_pipeline
from tracking.models import EventLog


ACTION_TO_EVENT_TYPE = {
    'view': EventLog.EventType.PRODUCT_VIEW,
    'click': EventLog.EventType.PRODUCT_CLICK,
    'add_to_cart': EventLog.EventType.ADD_TO_CART,
}


def _event_hash(*, user_id: int, session_id: str, event_type: str, product_id: int, ts) -> str:
    ts_str = ts.replace(microsecond=0).isoformat()
    raw = f'{user_id}|{session_id}|{event_type}|{product_id}|{ts_str}'
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


class Command(BaseCommand):
    help = 'Import bundled dataset.csv (if needed) and train BiLSTM model.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force-import',
            action='store_true',
            help='Import dataset.csv even if EventLog already has data.',
        )
        parser.add_argument(
            '--skip-train',
            action='store_true',
            help='Only import dataset.csv, do not train.',
        )

    def handle(self, *args, **options):
        force_import = bool(options.get('force_import'))
        skip_train = bool(options.get('skip_train'))

        dataset_path = Path('dataset') / 'dataset.csv'
        if not dataset_path.exists():
            raise CommandError(f'Không tìm thấy dataset: {dataset_path}')

        imported_count = 0
        if EventLog.objects.exists() and not force_import:
            self.stdout.write(self.style.WARNING('EventLog đã có dữ liệu, bỏ qua bước import dataset.csv.'))
        else:
            imported_count = self._import_dataset(dataset_path=dataset_path, replace_existing=force_import)

        if skip_train:
            self.stdout.write(self.style.WARNING('Bỏ qua train do dùng --skip-train.'))
            return

        if not EventLog.objects.exists():
            raise CommandError('Không có dữ liệu EventLog để train.')

        self.stdout.write(self.style.NOTICE('Bắt đầu train BiLSTM...'))
        try:
            result = run_full_training_pipeline()
        except RuntimeError as exc:
            # Trường hợp DB có ít event thủ công nên không tạo được đủ sequence train.
            if 'Không đủ chuỗi session' not in str(exc):
                raise
            self.stdout.write(
                self.style.WARNING(
                    'Dữ liệu hiện tại không đủ để train. Sẽ nạp lại dataset.csv và train lại.'
                )
            )
            imported_count = self._import_dataset(dataset_path=dataset_path, replace_existing=True)
            self.stdout.write(self.style.SUCCESS(f'Đã nạp lại {imported_count} events từ dataset.csv'))
            result = run_full_training_pipeline()

        RecommendEngine.reload()
        self.stdout.write(self.style.SUCCESS(f'Train xong: {result}'))

    def _import_dataset(self, *, dataset_path: Path, replace_existing: bool) -> int:
        if replace_existing:
            EventLog.objects.all().delete()
            self.stdout.write(self.style.WARNING('Đã xóa EventLog hiện có trước khi import dataset.csv.'))

        with dataset_path.open('r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            rows = []
            for row in reader:
                try:
                    user_id = int(row['user_id'])
                    product_id = int(row['product_id'])
                except (KeyError, TypeError, ValueError) as exc:
                    raise CommandError(f'Dữ liệu không hợp lệ ở user_id/product_id: {exc}') from exc

                action = (row.get('action') or '').strip().lower()
                event_type = ACTION_TO_EVENT_TYPE.get(action)
                if not event_type:
                    continue

                raw_ts = (row.get('timestamp') or '').strip()
                try:
                    dt = datetime.strptime(raw_ts, '%Y-%m-%d %H:%M:%S')
                except ValueError as exc:
                    raise CommandError(f'Timestamp không hợp lệ: "{raw_ts}"') from exc
                ts = timezone.make_aware(dt, timezone.get_current_timezone())

                session_id = f'seed-{user_id}-{ts.date().isoformat()}'
                rows.append(
                    EventLog(
                        user_id=user_id,
                        session_id=session_id,
                        event_type=event_type,
                        product_id=product_id,
                        timestamp=ts,
                        device='unknown',
                        source_page='seed:dataset.csv',
                        quantity=1,
                        event_hash=_event_hash(
                            user_id=user_id,
                            session_id=session_id,
                            event_type=event_type,
                            product_id=product_id,
                            ts=ts,
                        ),
                    )
                )

        EventLog.objects.bulk_create(rows, batch_size=1000)
        return len(rows)
