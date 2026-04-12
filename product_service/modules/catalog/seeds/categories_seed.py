"""
Seed command: populate Category data
Usage: python manage.py seed_categories --settings=config.settings.dev
"""
from django.core.management.base import BaseCommand
from modules.catalog.infrastructure.models import CategoryModel


class Command(BaseCommand):
    help = 'Seed initial categories'

    def handle(self, *args, **options):
        categories = [
            # (name, slug, description, parent_slug)
            ('Văn học', 'van-hoc', 'Tiểu thuyết, truyện ngắn, thơ ca', None),
            ('Kỹ năng sống', 'ky-nang-song', 'Sách phát triển bản thân', None),
            ('Khoa học', 'khoa-hoc', 'Sách khoa học, công nghệ', None),
            ('Lịch sử', 'lich-su', 'Sách lịch sử, địa lý', None),
            ('Thiếu nhi', 'thieu-nhi', 'Sách cho trẻ em', None),
            ('Ngoại ngữ', 'ngoai-ngu', 'Sách học tiếng Anh, Nhật, Hàn...', None),
            ('Kinh tế', 'kinh-te', 'Tài chính, kinh doanh, marketing', None),
            # Sub-categories
            ('Tiểu thuyết', 'tieu-thuyet', 'Tiểu thuyết trong và ngoài nước', 'van-hoc'),
            ('Truyện ngắn', 'truyen-ngan', 'Tập truyện ngắn', 'van-hoc'),
        ]

        parent_map = {}
        created = 0
        for name, slug, desc, parent_slug in categories:
            parent = parent_map.get(parent_slug) if parent_slug else None
            obj, was_created = CategoryModel.objects.get_or_create(
                slug=slug,
                defaults={'name': name, 'description': desc, 'parent': parent}
            )
            parent_map[slug] = obj
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f'✓ Đã tạo {created} categories'))
