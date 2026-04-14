"""
Product API views — DRF ViewSet injecting ProductApplicationService
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from modules.catalog.application.services.product_service import ProductApplicationService
from modules.catalog.application.commands.create_product import CreateProductCommand
from modules.catalog.application.commands.update_product import UpdateProductCommand
from modules.catalog.application.commands.create_variant import CreateVariantCommand
from modules.catalog.application.commands.update_variant import UpdateVariantCommand
from modules.catalog.application.queries.get_product import GetProductQuery, ListProductsQuery
from modules.catalog.infrastructure.repositories.product_repository_impl import ProductRepositoryImpl
from modules.catalog.infrastructure.models import ProductModel, VariantModel
from modules.catalog.presentation.api.serializers.product_serializer import (
    ProductSerializer, ProductListSerializer, VariantSerializer
)
from shared.exceptions import ProductNotFound, VariantNotFound, InsufficientStock


def get_product_service() -> ProductApplicationService:
    """Factory function: wire repository implementation into application service"""
    repository = ProductRepositoryImpl()
    return ProductApplicationService(repository)


class ProductViewSet(viewsets.ViewSet):
    """
    Product endpoints:
    GET    /api/products/              — list all products
    POST   /api/products/              — create product
    GET    /api/products/{id}/         — detail
    PUT    /api/products/{id}/         — update
    DELETE /api/products/{id}/         — delete
    GET    /api/products/available/    — products with stock > 0
    GET    /api/products/{id}/check_stock/?qty=N — stock check
    POST   /api/products/{id}/variants/ — add variant
    """

    def list(self, request):
        """GET /api/products/"""
        service = get_product_service()
        include_inactive = request.query_params.get('include_inactive') == 'true'
        query = ListProductsQuery(
            search=request.query_params.get('search'),
            category_id=request.query_params.get('category_id'),
            brand_id=request.query_params.get('brand_id'),
            in_stock_only=request.query_params.get('in_stock') == 'true',
            is_active_only=not include_inactive,
        )
        products = service.list_products(query)
        # Use ORM model for serializer compatibility
        product_models = ProductModel.objects.select_related(
            'category', 'brand', 'product_type'
        ).prefetch_related('variants').filter(
            id__in=[p.id for p in products]
        )
        serializer = ProductListSerializer(product_models, many=True)
        return Response({'count': len(products), 'results': serializer.data})

    def retrieve(self, request, pk=None):
        """GET /api/products/{id}/"""
        service = get_product_service()
        try:
            service.get_product(GetProductQuery(product_id=int(pk)))
            model = ProductModel.objects.select_related(
                'category', 'brand', 'product_type'
            ).prefetch_related('variants').get(id=pk)
            return Response(ProductSerializer(model).data)
        except ProductNotFound:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

    def create(self, request):
        """POST /api/products/"""
        service = get_product_service()
        data = request.data
        try:
            cmd = CreateProductCommand(
                name=data.get('name', ''),
                slug=data.get('slug', ''),
                description=data.get('description', ''),
                category_id=int(data.get('category_id', 0)),
                brand_id=int(data.get('brand_id', 0)),
                product_type_id=int(data.get('product_type_id', 0)),
                attributes=data.get('attributes', {}),
                is_active=data.get('is_active', True),
            )
            product = service.create_product(cmd)
            model = ProductModel.objects.select_related(
                'category', 'brand', 'product_type'
            ).prefetch_related('variants').get(id=product.id)
            return Response(ProductSerializer(model).data, status=status.HTTP_201_CREATED)
        except (ValueError, Exception) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        """PUT /api/products/{id}/"""
        service = get_product_service()
        data = request.data
        try:
            cmd = UpdateProductCommand(
                product_id=int(pk),
                name=data.get('name'),
                slug=data.get('slug'),
                description=data.get('description'),
                category_id=data.get('category_id'),
                brand_id=data.get('brand_id'),
                product_type_id=data.get('product_type_id'),
                attributes=data.get('attributes'),
                is_active=data.get('is_active'),
            )
            product = service.update_product(cmd)
            model = ProductModel.objects.select_related(
                'category', 'brand', 'product_type'
            ).prefetch_related('variants').get(id=product.id)
            return Response(ProductSerializer(model).data)
        except ProductNotFound:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        """DELETE /api/products/{id}/"""
        service = get_product_service()
        try:
            service.delete_product(int(pk))
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProductNotFound:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def available(self, request):
        """GET /api/products/available/ — sản phẩm còn hàng"""
        service = get_product_service()
        products = service.get_available_products()
        product_models = ProductModel.objects.select_related(
            'category', 'brand', 'product_type'
        ).prefetch_related('variants').filter(
            id__in=[p.id for p in products]
        )
        serializer = ProductListSerializer(product_models, many=True)
        return Response({'count': len(products), 'results': serializer.data})

    @action(detail=True, methods=['get'])
    def check_stock(self, request, pk=None):
        """GET /api/products/{id}/check_stock/?variant_id=X&qty=N"""
        service = get_product_service()
        variant_id = request.query_params.get('variant_id')
        qty = int(request.query_params.get('qty', 1))
        if not variant_id:
            # Get first active variant if no variant_id specified
            try:
                model = VariantModel.objects.filter(
                    product_id=pk, is_active=True
                ).first()
                if not model:
                    return Response({'available': False, 'message': 'No variants available'})
                variant_id = model.id
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            available, message = service.check_stock(int(variant_id), qty)
            return Response({'available': available, 'message': message})
        except VariantNotFound:
            return Response({'error': 'Variant not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def variants(self, request, pk=None):
        """POST /api/products/{id}/variants/ — thêm variant mới cho sản phẩm"""
        service = get_product_service()
        data = request.data
        try:
            cmd = CreateVariantCommand(
                product_id=int(pk),
                sku=data.get('sku', ''),
                price=data.get('price', 0),
                stock=int(data.get('stock', 0)),
                attributes=data.get('attributes', {}),
                cover_image_url=data.get('cover_image_url'),
                is_active=data.get('is_active', True),
            )
            variant = service.create_variant(cmd)
            model = VariantModel.objects.get(id=variant.id)
            return Response(VariantSerializer(model).data, status=status.HTTP_201_CREATED)
        except ProductNotFound:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['put', 'patch'], url_path=r'variants/(?P<variant_id>[0-9]+)')
    def variant_update(self, request, pk=None, variant_id=None):
        """PUT/PATCH /api/products/{id}/variants/{variant_id}/ — cập nhật biến thể."""
        service = get_product_service()
        data = request.data
        try:
            cmd = UpdateVariantCommand(
                variant_id=int(variant_id),
                product_id=int(pk),
                sku=data.get('sku'),
                price=data.get('price'),
                stock=data.get('stock'),
                cover_image_url=data.get('cover_image_url'),
                is_active=data.get('is_active'),
            )
            variant = service.update_variant(cmd)
            model = VariantModel.objects.get(id=variant.id)
            return Response(VariantSerializer(model).data)
        except VariantNotFound:
            return Response({'error': 'Variant not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
