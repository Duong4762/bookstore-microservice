"""
Django management command: python manage.py run_etl

Examples:
    python manage.py run_etl --days 30
    python manage.py run_etl --days 90 --output-dir ml/data
    python manage.py run_etl --start-date 2024-01-01 --end-date 2024-12-31
    python manage.py run_etl --dry-run
"""
import os
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Run ETL pipeline: extract EventLog → build sequences → export parquet for training'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days', type=int, default=None,
            help='Process events from last N days (default: all data)',
        )
        parser.add_argument(
            '--start-date', type=str, default=None,
            help='Start date in YYYY-MM-DD format',
        )
        parser.add_argument(
            '--end-date', type=str, default=None,
            help='End date in YYYY-MM-DD format (default: now)',
        )
        parser.add_argument(
            '--output-dir', type=str, default=None,
            help='Output directory for parquet files (default: ML_SETTINGS["DATA_DIR"])',
        )
        parser.add_argument(
            '--min-seq-len', type=int, default=2,
            help='Minimum number of events per user to include (default: 2)',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Run ETL without writing any files — only show statistics',
        )

    def handle(self, *args, **options):
        os.environ.setdefault('DJANGO_SKIP_ML_LOAD', '1')

        ml = settings.ML_SETTINGS
        data_dir = options['output_dir'] or str(ml['DATA_DIR'])
        vocab_path = str(ml['VOCAB_PATH'])

        start_date = None
        if options['start_date']:
            start_date = datetime.strptime(options['start_date'], '%Y-%m-%d')

        end_date = None
        if options['end_date']:
            end_date = datetime.strptime(options['end_date'], '%Y-%m-%d')

        self.stdout.write(self.style.MIGRATE_HEADING('=== ETL Pipeline ==='))
        self.stdout.write(f'  Output dir : {data_dir}')
        self.stdout.write(f'  Vocab path : {vocab_path}')
        self.stdout.write(f'  Days       : {options["days"] or "all"}')
        self.stdout.write(f'  Dry run    : {options["dry_run"]}')

        from etl.pipeline import run_etl
        stats = run_etl(
            data_dir=data_dir,
            vocab_path=vocab_path,
            start_date=start_date,
            end_date=end_date,
            days=options['days'],
            min_seq_len=options['min_seq_len'],
            dry_run=options['dry_run'],
        )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=== ETL Results ==='))
        for key, val in stats.items():
            self.stdout.write(f'  {key:<20}: {val}')

        if options['dry_run']:
            self.stdout.write(self.style.WARNING('Dry run — no files written.'))
        else:
            self.stdout.write(self.style.SUCCESS('✅ ETL complete! Run train_model next.'))
