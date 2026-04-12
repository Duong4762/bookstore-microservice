"""
Unit tests for Category domain entity
"""
from django.test import TestCase
from modules.catalog.domain.entities.category import Category


class TestCategoryEntity(TestCase):
    def test_root_category(self):
        cat = Category(id=1, name='Văn học', slug='van-hoc')
        self.assertTrue(cat.is_root())

    def test_child_category(self):
        child = Category(id=2, name='Tiểu thuyết', slug='tieu-thuyet', parent_id=1)
        self.assertFalse(child.is_root())
        self.assertEqual(child.parent_id, 1)

    def test_empty_name_raises(self):
        with self.assertRaises(ValueError):
            Category(id=None, name='', slug='van-hoc')

    def test_empty_slug_raises(self):
        with self.assertRaises(ValueError):
            Category(id=None, name='Văn học', slug='')
