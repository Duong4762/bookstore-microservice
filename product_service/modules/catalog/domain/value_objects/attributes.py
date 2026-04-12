"""
Attributes Value Object — flexible JSON attributes for a product or variant.
Example: {"author": "Dale Carnegie", "pages": 320, "language": "vi", "color": "red"}
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Attributes:
    """
    Value Object lưu trữ các thuộc tính linh hoạt (dạng JSON) của sản phẩm/variant.
    Frozen = immutable — để thay đổi phải tạo instance mới.
    """
    data: dict = field(default_factory=dict)

    def __post_init__(self):
        # Ensure data is always a plain dict copy (not mutable external reference)
        object.__setattr__(self, 'data', dict(self.data))

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def with_attribute(self, key: str, value: Any) -> Attributes:
        """Return a new Attributes instance with the added/updated key."""
        new_data = {**self.data, key: value}
        return Attributes(new_data)

    def without_attribute(self, key: str) -> Attributes:
        """Return a new Attributes instance without the given key."""
        new_data = {k: v for k, v in self.data.items() if k != key}
        return Attributes(new_data)

    def __repr__(self) -> str:
        return f"Attributes({self.data})"

    @classmethod
    def empty(cls) -> Attributes:
        return cls({})

    @classmethod
    def of(cls, **kwargs) -> Attributes:
        return cls(kwargs)
