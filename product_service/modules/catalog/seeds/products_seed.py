"""
Seed command: populate sample Product & Variant data
Usage: python manage.py seed_products --settings=config.settings.dev
"""
from django.core.management.base import BaseCommand
from decimal import Decimal
from django.db import transaction
from modules.catalog.infrastructure.models import (
    ProductModel, VariantModel, CategoryModel, BrandModel, ProductTypeModel
)


class Command(BaseCommand):
    help = 'Seed sample products with variants'

    def handle(self, *args, **options):
        categories = {c.id: c for c in CategoryModel.objects.filter(id__in=[2, 3, 4, 6, 7, 11, 13])}
        brands = {b.id: b for b in BrandModel.objects.filter(id__in=[2, 4, 9, 12, 14, 19, 20])}
        product_types = {pt.id: pt for pt in ProductTypeModel.objects.filter(id__in=[1, 2, 3, 5, 6, 7, 11])}

        missing = []
        if len(categories) < 7:
            missing.append('categories id 2,3,4,6,7,11,13')
        if len(brands) < 7:
            missing.append('brands id 2,4,9,12,14,19,20')
        if len(product_types) < 7:
            missing.append('product_types id 1,2,3,5,6,7,11')
        if missing:
            self.stdout.write(self.style.ERROR(f'Thiếu dữ liệu nền: {", ".join(missing)}'))
            self.stdout.write(self.style.WARNING('Hãy chạy sql/seed_products.sql trước.'))
            return

        # (group_name, category_id, brand_id, product_type_id)
        groups = [
            ('phone', 3, 2, 2),
            ('case', 7, 19, 7),
            ('charger', 7, 19, 7),
            ('laptop', 2, 4, 1),
            ('mouse', 7, 12, 7),
            ('keyboard', 7, 12, 7),
            ('headphone', 6, 9, 5),
            ('tablet', 4, 2, 3),
            ('tshirt', 13, 14, 6),
            ('shirt', 13, 14, 6),
            ('jacket', 13, 14, 6),
            ('jeans', 13, 14, 6),
            ('shorts', 13, 14, 6),
            ('shoes', 13, 14, 6),
            ('sandals', 13, 14, 6),
            ('bag', 7, 12, 7),
            ('backpack', 7, 12, 7),
            ('hat', 7, 12, 7),
            ('watch', 11, 20, 11),
            ('glasses', 7, 12, 7),
        ]

        created_products = 0
        created_variants = 0

        with transaction.atomic():
            for group_idx, (group_name, category_id, brand_id, product_type_id) in enumerate(groups, start=1):
                category = categories[category_id]
                brand = brands[brand_id]
                product_type = product_types[product_type_id]

                for slot in range(1, 16):
                    product_id = (group_idx - 1) * 15 + slot
                    slug = f'{group_name}-product-{slot:02d}'
                    product, was_created = ProductModel.objects.get_or_create(
                        id=product_id,
                        defaults={
                            'name': f'{group_name.title()} Product {slot:02d}',
                            'slug': slug,
                            'description': f'Auto generated {group_name} item #{slot} (group {group_idx}).',
                            'category': category,
                            'brand': brand,
                            'product_type': product_type,
                            'attributes': {
                                'group': group_name,
                                'group_index': group_idx,
                                'slot': slot,
                                'seed_profile': 'ai-compatible-300',
                            },
                        },
                    )
                    if was_created:
                        created_products += 1

                    _, v_created = VariantModel.objects.get_or_create(
                        sku=f'SKU-{product_id:04d}',
                        defaults={
                            'product': product,
                            'price': Decimal(str(199000 + product_id * 1000)),
                            'stock': 20 + (product_id % 40),
                            'attributes': {
                                'seed_profile': 'ai-compatible-300',
                            },
                        },
                    )
                    if v_created:
                        created_variants += 1

        self.stdout.write(self.style.SUCCESS(
            f'✓ Đã tạo {created_products} products, {created_variants} variants'
        ))
