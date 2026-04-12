"""
Brand Entity
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class Brand:
    """
    Entity đại diện cho thương hiệu / nhà xuất bản.
    Ví dụ: NXB Kim Đồng, NXB Trẻ, Penguin Books, ...
    """
    id: Optional[int]
    name: str
    slug: str
    description: str = ""
    is_active: bool = True

    def __post_init__(self):
        if not self.name or not self.name.strip():
            raise ValueError("Brand name cannot be empty")

    def __repr__(self) -> str:
        return f"Brand(id={self.id}, name={self.name!r})"
