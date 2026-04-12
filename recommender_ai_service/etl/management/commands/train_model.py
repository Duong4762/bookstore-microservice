"""
Django management command: python manage.py train_model

Examples:
    python manage.py train_model
    python manage.py train_model --epochs 30 --batch-size 128
    python manage.py train_model --resume ml/checkpoints/model_v123.pt
    python manage.py train_model --device cpu
"""
import os

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Train the LSTM recommendation model from ETL-prepared data'

    def add_arguments(self, parser):
        parser.add_argument('--data-dir', type=str, default=None,
                            help='Directory with train/val/test.parquet')
        parser.add_argument('--epochs', type=int, default=None,
                            help='Number of training epochs')
        parser.add_argument('--batch-size', type=int, default=None,
                            help='Training batch size')
        parser.add_argument('--lr', type=float, default=None,
                            help='Adam learning rate')
        parser.add_argument('--patience', type=int, default=None,
                            help='Early stopping patience')
        parser.add_argument('--device', type=str, default='auto',
                            choices=['auto', 'cpu', 'cuda', 'mps'],
                            help='Training device')
        parser.add_argument('--resume', type=str, default=None,
                            help='Path to checkpoint .pt to resume training')
        parser.add_argument('--max-keep', type=int, default=None,
                            help='Max number of checkpoints to retain')

    def handle(self, *args, **options):
        # Skip ML loading when this command is discovered
        os.environ.setdefault('DJANGO_SKIP_ML_LOAD', '1')

        ml = settings.ML_SETTINGS

        data_dir = options['data_dir'] or str(ml['DATA_DIR'])
        checkpoint_dir = str(ml['CHECKPOINT_DIR'])
        vocab_path = str(ml['VOCAB_PATH'])

        epochs = options['epochs'] or ml['TRAIN_EPOCHS']
        batch_size = options['batch_size'] or ml['BATCH_SIZE']
        lr = options['lr'] or ml['LEARNING_RATE']
        patience = options['patience'] or ml['EARLY_STOPPING_PATIENCE']
        max_keep = options['max_keep'] or ml['MAX_CHECKPOINTS_TO_KEEP']

        self.stdout.write(self.style.MIGRATE_HEADING('=== Training LSTM Recommender ==='))
        self.stdout.write(f'  Data dir      : {data_dir}')
        self.stdout.write(f'  Checkpoint dir: {checkpoint_dir}')
        self.stdout.write(f'  Epochs        : {epochs}')
        self.stdout.write(f'  Batch size    : {batch_size}')
        self.stdout.write(f'  LR            : {lr}')
        self.stdout.write(f'  Patience      : {patience}')
        self.stdout.write(f'  Device        : {options["device"]}')

        from ml.train import train
        final_metrics = train(
            data_dir=data_dir,
            checkpoint_dir=checkpoint_dir,
            vocab_path=vocab_path,
            epochs=epochs,
            batch_size=batch_size,
            lr=lr,
            weight_decay=ml['WEIGHT_DECAY'],
            patience=patience,
            device_str=options['device'],
            resume_checkpoint=options['resume'],
            max_keep=max_keep,
        )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=== Training Complete ==='))
        self.stdout.write(f'  recall@5  : {final_metrics.get("recall@5", 0):.4f}')
        self.stdout.write(f'  recall@10 : {final_metrics.get("recall@10", 0):.4f}')
        self.stdout.write(f'  mrr@5     : {final_metrics.get("mrr@5", 0):.4f}')
        self.stdout.write(f'  ndcg@5    : {final_metrics.get("ndcg@5", 0):.4f}')
        self.stdout.write(f'  val_loss  : {final_metrics.get("val_loss", 0):.4f}')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✅ Model saved. Restart the Django server to load the new checkpoint.'))
