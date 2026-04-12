"""
Category Entity — self-referential tree structure
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class Category:
    """
    Entity đại diện cho danh mục sản phẩm theo cấu trúc cây.
    Một category có thể có parent (danh mục cha) và danh sách children.
    """
    id: Optional[int]
    name: str
    slug: str
    description: str = ""
    parent_id: Optional[int] = None
    is_active: bool = True

    def __post_init__(self):
        if not self.name or not self.name.strip():
            raise ValueError("Category name cannot be empty")
        if not self.slug or not self.slug.strip():
            raise ValueError("Category slug cannot be empty")

    def is_root(self) -> bool:
        """Kiểm tra đây có phải là category gốc không"""
        return self.parent_id is None

    def __repr__(self) -> str:
        parent_info = f", parent_id={self.parent_id}" if self.parent_id else ""
        return f"Category(id={self.id}, name={self.name!r}{parent_info})"
