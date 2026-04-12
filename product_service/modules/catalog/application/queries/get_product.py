"""
Query objects for read-side operations
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GetProductQuery:
    product_id: int


@dataclass
class ListProductsQuery:
    search: Optional[str] = None
    category_id: Optional[int] = None
    brand_id: Optional[int] = None
    product_type_id: Optional[int] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    in_stock_only: bool = False
    is_active_only: bool = True
    ordering: str = '-created_at'


@dataclass
class FilterProductsQuery:
    """Advanced filter query"""
    filters: dict = field(default_factory=dict)
