"""
Custom domain exceptions for product_service
"""


class ProductNotFound(Exception):
    """Raised when a product cannot be found"""
    def __init__(self, product_id: int):
        super().__init__(f"Product with id={product_id} not found")
        self.product_id = product_id


class VariantNotFound(Exception):
    """Raised when a variant cannot be found"""
    def __init__(self, variant_id: int):
        super().__init__(f"Variant with id={variant_id} not found")
        self.variant_id = variant_id


class CategoryNotFound(Exception):
    """Raised when a category cannot be found"""
    def __init__(self, category_id: int):
        super().__init__(f"Category with id={category_id} not found")
        self.category_id = category_id


class InsufficientStock(Exception):
    """Raised when stock quantity is insufficient"""
    def __init__(self, available: int, requested: int):
        super().__init__(
            f"Insufficient stock: requested {requested}, available {available}"
        )
        self.available = available
        self.requested = requested


class InvalidSKU(ValueError):
    """Raised when SKU format is invalid"""
    pass


class InvalidPrice(ValueError):
    """Raised when price is invalid (e.g. negative)"""
    pass
