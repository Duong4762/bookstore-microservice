"""
ProductQuerySet — custom QuerySet with reusable filter methods
"""
from django.db import models
from django.db.models import Q


class ProductQuerySet(models.QuerySet):
    """Reusable filter methods for ProductModel queries"""

    def active(self):
        """Chỉ lấy sản phẩm đang hoạt động"""
        return self.filter(is_active=True)

    def in_stock(self):
        """Chỉ lấy sản phẩm còn ít nhất 1 variant có hàng"""
        return self.filter(
            variants__stock__gt=0,
            variants__is_active=True,
        ).distinct()

    def by_category(self, category_id: int):
        return self.filter(category_id=category_id)

    def by_brand(self, brand_id: int):
        return self.filter(brand_id=brand_id)

    def search(self, term: str):
        """Tìm kiếm theo tên, mô tả, hoặc attribute (author, isbn)"""
        return self.filter(
            Q(name__icontains=term) |
            Q(description__icontains=term) |
            Q(attributes__author__icontains=term) |
            Q(attributes__isbn__icontains=term)
        )

    def price_range(self, min_price=None, max_price=None):
        """Lọc theo khoảng giá (dựa trên giá thấp nhất của variant)"""
        qs = self
        if min_price is not None:
            qs = qs.filter(variants__price__gte=min_price)
        if max_price is not None:
            qs = qs.filter(variants__price__lte=max_price)
        return qs.distinct()

    def with_prefetch(self):
        """Prefetch related data để tránh N+1 queries"""
        return self.select_related(
            'category', 'brand', 'product_type'
        ).prefetch_related('variants')
