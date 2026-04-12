"""
Unit tests for Product domain entity and application service
"""
from decimal import Decimal
from unittest.mock import MagicMock
from django.test import TestCase

from modules.catalog.domain.entities import Product, Variant
from modules.catalog.domain.value_objects import Money, SKU, Attributes
from modules.catalog.application.services.product_service import ProductApplicationService
from modules.catalog.application.commands.create_product import CreateProductCommand
from modules.catalog.application.queries.get_product import GetProductQuery, ListProductsQuery
from shared.exceptions import ProductNotFound, InsufficientStock, InvalidPrice


class TestMoneyValueObject(TestCase):
    def test_create_money(self):
        m = Money.of(80000)
        self.assertEqual(m.amount, Decimal('80000'))
        self.assertEqual(m.currency, 'VND')

    def test_money_addition(self):
        m1 = Money.of(80000)
        m2 = Money.of(20000)
        self.assertEqual((m1 + m2).amount, Decimal('100000'))

    def test_money_multiplication(self):
        m = Money.of(50000)
        self.assertEqual((m * 3).amount, Decimal('150000'))

    def test_negative_price_raises(self):
        with self.assertRaises(InvalidPrice):
            Money.of(-1000)


class TestSKUValueObject(TestCase):
    def test_valid_sku(self):
        sku = SKU('BOOK-0001')
        self.assertEqual(str(sku), 'BOOK-0001')

    def test_sku_normalizes_to_uppercase(self):
        sku = SKU('book-0001')
        self.assertEqual(sku.value, 'BOOK-0001')

    def test_invalid_sku_raises(self):
        from shared.exceptions import InvalidSKU
        with self.assertRaises(InvalidSKU):
            SKU('invalid sku!!!')


class TestProductEntity(TestCase):
    def _make_product(self) -> Product:
        return Product(
            id=1,
            name='Đắc Nhân Tâm',
            slug='dac-nhan-tam',
            description='...',
            category_id=1,
            brand_id=1,
            product_type_id=1,
            attributes=Attributes({'author': 'Dale Carnegie', 'pages': 320}),
        )

    def test_product_author_property(self):
        p = self._make_product()
        self.assertEqual(p.author, 'Dale Carnegie')

    def test_product_deactivate(self):
        p = self._make_product()
        p.deactivate()
        self.assertFalse(p.is_active)

    def test_product_empty_name_raises(self):
        with self.assertRaises(ValueError):
            Product(id=None, name='', slug='x', description='',
                    category_id=1, brand_id=1, product_type_id=1)


class TestVariantEntity(TestCase):
    def _make_variant(self, stock=10) -> Variant:
        return Variant(
            id=1,
            product_id=1,
            sku=SKU('DACN-0001'),
            price=Money.of(80000),
            stock=stock,
        )

    def test_in_stock_true(self):
        v = self._make_variant(stock=5)
        self.assertTrue(v.in_stock)

    def test_in_stock_false_when_zero(self):
        v = self._make_variant(stock=0)
        self.assertFalse(v.in_stock)

    def test_reduce_stock(self):
        v = self._make_variant(stock=10)
        v.reduce_stock(3)
        self.assertEqual(v.stock, 7)

    def test_reduce_stock_insufficient_raises(self):
        v = self._make_variant(stock=2)
        with self.assertRaises(InsufficientStock):
            v.reduce_stock(5)


class TestProductApplicationService(TestCase):
    def setUp(self):
        self.mock_repo = MagicMock()
        self.service = ProductApplicationService(self.mock_repo)

    def test_create_product_calls_save(self):
        cmd = CreateProductCommand(
            name='Test Book', slug='test-book', description='',
            category_id=1, brand_id=1, product_type_id=1
        )
        self.mock_repo.save_product.return_value = Product(
            id=99, name='Test Book', slug='test-book', description='',
            category_id=1, brand_id=1, product_type_id=1
        )
        result = self.service.create_product(cmd)
        self.mock_repo.save_product.assert_called_once()
        self.assertEqual(result.id, 99)

    def test_get_product_not_found_raises(self):
        self.mock_repo.get_product_by_id.return_value = None
        with self.assertRaises(ProductNotFound):
            self.service.get_product(GetProductQuery(product_id=999))

    def test_delete_product_not_found_raises(self):
        self.mock_repo.get_product_by_id.return_value = None
        with self.assertRaises(ProductNotFound):
            self.service.delete_product(999)
