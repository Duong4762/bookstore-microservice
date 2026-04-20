"""
Views for Cart API - chỉ xử lý HTTP request/response
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer
from .services import CartService, CartItemService


class CartViewSet(viewsets.ModelViewSet):
    """
    ViewSet cho Cart API
    Views chỉ xử lý HTTP layer, business logic nằm trong CartService
    """
    queryset = Cart.objects.all()
    serializer_class = CartSerializer
    
    def list(self, request, *args, **kwargs):
        """GET /carts/ - Lấy danh sách giỏ hàng"""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """POST /carts/ - Tạo giỏ hàng mới"""
        customer_id = request.data.get('customer_id')
        if not customer_id:
            return Response(
                {'error': 'customer_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cart = CartService.create_cart(customer_id)
        serializer = self.get_serializer(cart)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def retrieve(self, request, *args, **kwargs):
        """GET /carts/{id}/ - Lấy thông tin chi tiết giỏ hàng"""
        cart = CartService.get_cart_by_id(kwargs.get('pk'))
        if not cart:
            return Response(
                {'error': 'Cart not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(cart)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_customer(self, request):
        """GET /carts/by_customer/?customer_id=X - Lấy giỏ hàng theo customer_id"""
        customer_id = request.query_params.get('customer_id')
        if not customer_id:
            return Response(
                {'error': 'customer_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cart = CartService.get_cart_by_customer(int(customer_id))
        if not cart:
            return Response(
                {'error': 'Cart not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(cart)
        return Response(serializer.data)


class CartItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet cho CartItem API
    Views chỉ xử lý HTTP layer, business logic nằm trong CartItemService
    """
    queryset = CartItem.objects.all()
    serializer_class = CartItemSerializer
    
    def create(self, request, *args, **kwargs):
        """POST /cart-items/ - Thêm sách vào giỏ hàng"""
        cart_id = request.data.get('cart_id')
        book_id = request.data.get('book_id')
        variant_id = request.data.get('variant_id')
        quantity = request.data.get('quantity', 1)
        
        if not cart_id or not book_id:
            return Response(
                {'error': 'cart_id and book_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            cart_item = CartItemService.add_item_to_cart(
                cart_id=cart_id,
                book_id=book_id,
                variant_id=int(variant_id) if variant_id not in (None, '', 'null') else None,
                quantity=int(quantity)
            )
            serializer = self.get_serializer(cart_item)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to add item to cart: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        """PUT /cart-items/{id}/ - Cập nhật số lượng sách trong giỏ hàng"""
        quantity = request.data.get('quantity')
        if not quantity:
            return Response(
                {'error': 'quantity is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cart_item = CartItemService.update_cart_item_quantity(
            kwargs.get('pk'),
            int(quantity)
        )
        
        if not cart_item:
            return Response(
                {'error': 'Cart item not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(cart_item)
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """DELETE /cart-items/{id}/ - Xóa sách khỏi giỏ hàng"""
        success = CartItemService.remove_item_from_cart(kwargs.get('pk'))
        if not success:
            return Response(
                {'error': 'Cart item not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(status=status.HTTP_204_NO_CONTENT)
