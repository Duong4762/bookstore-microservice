"""
Shared utility functions for product_service
"""
import re
import unicodedata


def slugify(value: str) -> str:
    """
    Convert a string to a URL-friendly slug.
    Example: 'Đắc Nhân Tâm' -> 'dac-nhan-tam'
    """
    # Normalize unicode characters
    value = unicodedata.normalize('NFKD', value)
    value = value.encode('ascii', 'ignore').decode('ascii')
    value = value.lower()
    # Replace spaces and special chars with hyphens
    value = re.sub(r'[^\w\s-]', '', value)
    value = re.sub(r'[-\s]+', '-', value)
    return value.strip('-')


def generate_sku(product_name: str, variant_index: int = 1) -> str:
    """
    Generate a SKU from product name.
    Example: 'Harry Potter', index=1 -> 'HARP-0001'
    """
    words = product_name.upper().split()
    prefix = ''.join(w[:2] for w in words[:2])
    return f"{prefix}-{variant_index:04d}"
