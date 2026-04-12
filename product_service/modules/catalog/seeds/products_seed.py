"""
Seed command: populate sample Product & Variant data
Usage: python manage.py seed_products --settings=config.settings.dev
"""
from django.core.management.base import BaseCommand
from decimal import Decimal
from modules.catalog.infrastructure.models import (
    ProductModel, VariantModel, CategoryModel, BrandModel, ProductTypeModel
)


class Command(BaseCommand):
    help = 'Seed sample products with variants'

    def handle(self, *args, **options):
        # Ensure prerequisites exist
        kn_cat, _ = CategoryModel.objects.get_or_create(
            slug='ky-nang-song', defaults={'name': 'Kỹ năng sống'}
        )
        van_cat, _ = CategoryModel.objects.get_or_create(
            slug='van-hoc', defaults={'name': 'Văn học'}
        )
        nxb_tre, _ = BrandModel.objects.get_or_create(
            slug='nxb-tre', defaults={'name': 'NXB Trẻ'}
        )
        nxb_kim_dong, _ = BrandModel.objects.get_or_create(
            slug='nxb-kim-dong', defaults={'name': 'NXB Kim Đồng'}
        )
        book_type, _ = ProductTypeModel.objects.get_or_create(
            name='Sách bìa mềm',
            defaults={'required_attributes': ['author', 'isbn', 'pages', 'language']}
        )

        products = [
            {
                'name': 'Đắc Nhân Tâm',
                'slug': 'dac-nhan-tam',
                'description': 'Cuốn sách kỹ năng sống bán chạy nhất mọi thời đại.',
                'category': kn_cat,
                'brand': nxb_tre,
                'product_type': book_type,
                'attributes': {
                    'author': 'Dale Carnegie',
                    'isbn': '978-604-1-24321-0',
                    'pages': 320,
                    'language': 'Vietnamese',
                    'publication_year': 2023,
                },
                'variants': [
                    {'sku': 'DACN-0001', 'price': Decimal('80000'), 'stock': 50},
                ],
            },
            {
                'name': 'Nhà Giả Kim',
                'slug': 'nha-gia-kim',
                'description': 'Tiểu thuyết triết học về hành trình khám phá bản thân.',
                'category': van_cat,
                'brand': nxb_tre,
                'product_type': book_type,
                'attributes': {
                    'author': 'Paulo Coelho',
                    'isbn': '978-604-1-24322-7',
                    'pages': 228,
                    'language': 'Vietnamese',
                    'publication_year': 2022,
                },
                'variants': [
                    {'sku': 'NHAG-0001', 'price': Decimal('75000'), 'stock': 30},
                ],
            },
            {
                'name': 'Tư Duy Nhanh Và Chậm',
                'slug': 'tu-duy-nhanh-va-cham',
                'description': 'Khám phá hai hệ thống tư duy điều khiển cách chúng ta nghĩ.',
                'category': kn_cat,
                'brand': nxb_tre,
                'product_type': book_type,
                'attributes': {
                    'author': 'Daniel Kahneman',
                    'isbn': '978-604-1-24323-4',
                    'pages': 512,
                    'language': 'Vietnamese',
                    'publication_year': 2023,
                },
                'variants': [
                    {'sku': 'TUDU-0001', 'price': Decimal('120000'), 'stock': 20},
                    {'sku': 'TUDU-0002-HB', 'price': Decimal('150000'), 'stock': 10,
                     'attributes': {'edition': 'hardcover'}},
                ],
            },
            {
                'name': 'Sapiens: Lược Sử Loài Người',
                'slug': 'sapiens-luoc-su-loai-nguoi',
                'description': 'Hành trình 70.000 năm của con người từ thời tiền sử đến hiện đại.',
                'category': kn_cat,
                'brand': nxb_tre,
                'product_type': book_type,
                'attributes': {
                    'author': 'Yuval Noah Harari',
                    'isbn': '978-604-1-24324-1',
                    'pages': 575,
                    'language': 'Vietnamese',
                    'publication_year': 2023,
                },
                'variants': [
                    {'sku': 'SAPI-0001', 'price': Decimal('135000'), 'stock': 15},
                ],
            },
            {
                'name': 'Doraemon Tập 1',
                'slug': 'doraemon-tap-1',
                'description': 'Bộ truyện tranh Doraemon nổi tiếng.',
                'category': van_cat,
                'brand': nxb_kim_dong,
                'product_type': book_type,
                'attributes': {
                    'author': 'Fujiko F. Fujio',
                    'isbn': '978-604-9-53001-5',
                    'pages': 192,
                    'language': 'Vietnamese',
                    'publication_year': 2021,
                },
                'variants': [
                    {'sku': 'DORA-0001', 'price': Decimal('25000'), 'stock': 100},
                ],
            },
        ]

        created_products = 0
        created_variants = 0

        for p_data in products:
            variants_data = p_data.pop('variants')
            product, was_created = ProductModel.objects.get_or_create(
                slug=p_data['slug'], defaults=p_data
            )
            if was_created:
                created_products += 1

            for v_data in variants_data:
                v_attrs = v_data.pop('attributes', {})
                variant, v_created = VariantModel.objects.get_or_create(
                    sku=v_data['sku'],
                    defaults={**v_data, 'product': product, 'attributes': v_attrs}
                )
                if v_created:
                    created_variants += 1

        self.stdout.write(self.style.SUCCESS(
            f'✓ Đã tạo {created_products} products, {created_variants} variants'
        ))
