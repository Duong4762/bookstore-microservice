# Refactoring Notes - Service Layer Pattern

## 📐 Kiến trúc sau khi refactor

Hệ thống đã được refactor theo **Service Layer Pattern** với các tầng rõ ràng:

```
┌─────────────────────────────────────┐
│       HTTP Request/Response         │
│         (Views Layer)               │
├─────────────────────────────────────┤
│       Business Logic                │
│        (Service Layer)              │
├─────────────────────────────────────┤
│     Data Access & Validation        │
│    (Models & Serializers)           │
└─────────────────────────────────────┘
```

## ✅ Cải tiến đã thực hiện

### 1. **Tách biệt trách nhiệm (Separation of Concerns)**

#### Trước khi refactor:
```python
# views.py - Business logic lẫn lộn với HTTP handling
class CustomerViewSet(viewsets.ModelViewSet):
    def create(self, request):
        serializer = CustomerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        customer = serializer.save()
        
        # Business logic: Tạo cart
        response = requests.post(CART_SERVICE_URL, ...)
        
        return Response(...)
```

#### Sau khi refactor:
```python
# services.py - Business logic tách riêng
class CustomerService:
    @staticmethod
    def create_customer(data: dict) -> Customer:
        serializer = CustomerSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        customer = serializer.save()
        CustomerService._create_cart_for_customer(customer.id)
        return customer

# views.py - Chỉ xử lý HTTP
class CustomerViewSet(viewsets.ModelViewSet):
    def create(self, request):
        customer = CustomerService.create_customer(request.data)
        serializer = self.get_serializer(customer)
        return Response(serializer.data, status=201)
```

### 2. **Tăng khả năng tái sử dụng (Reusability)**

Service layer có thể được gọi từ:
- REST API endpoints
- Django management commands
- Celery tasks
- Scripts/migrations
- Tests

Ví dụ:
```python
# Trong test
def test_create_customer():
    customer = CustomerService.create_customer({
        'email': 'test@example.com',
        'full_name': 'Test User'
    })
    assert customer.id is not None

# Trong management command
class Command(BaseCommand):
    def handle(self, *args, **options):
        CustomerService.create_customer(...)
```

### 3. **Dễ dàng test (Testability)**

```python
# Test service layer (không cần HTTP request)
def test_customer_creation():
    customer = CustomerService.create_customer(test_data)
    assert customer.email == test_data['email']

# Mock external services dễ dàng hơn
@patch('customers.services.requests.post')
def test_cart_creation(mock_post):
    mock_post.return_value.status_code = 201
    customer = CustomerService.create_customer(test_data)
    mock_post.assert_called_once()
```

### 4. **Type hints và Documentation**

Tất cả service methods đều có:
- Type hints rõ ràng
- Docstrings đầy đủ
- Return types cụ thể

```python
@staticmethod
def get_customer_by_id(customer_id: int) -> Optional[Customer]:
    """
    Lấy customer theo ID
    
    Args:
        customer_id: ID của customer
        
    Returns:
        Customer object hoặc None nếu không tìm thấy
    """
    ...
```

## 📂 Cấu trúc file mới

Mỗi service đều có:

```
service_name/
├── app_name/
│   ├── models.py         # Data models
│   ├── serializers.py    # Data validation & serialization
│   ├── services.py       # ⭐ Business logic (MỚI)
│   ├── views.py          # HTTP handling only
│   └── urls.py           # URL routing
```

## 🎯 Các Service Classes đã tạo

### 1. Customer Service
- `CustomerService`: Business logic cho Customer
  - `create_customer()` - Tạo customer + auto tạo cart
  - `get_all_customers()` - Lấy danh sách
  - `get_customer_by_id()` - Lấy theo ID
  - `update_customer()` - Cập nhật thông tin
  - `delete_customer()` - Xóa customer

### 2. Book Service
- `BookService`: Business logic cho Book
  - `create_book()` - Tạo sách mới
  - `get_all_books()` - Lấy danh sách (có filters)
  - `get_available_books()` - Lấy sách còn hàng
  - `check_stock_availability()` - Kiểm tra tồn kho
  - `update_stock()` - Cập nhật tồn kho

### 3. Cart Service
- `CartService`: Logic cho Cart
  - `create_cart()` - Tạo giỏ hàng
  - `get_cart_by_customer()` - Lấy theo customer
  
- `CartItemService`: Logic cho CartItem
  - `add_item_to_cart()` - Thêm sách vào giỏ
  - `update_cart_item_quantity()` - Cập nhật số lượng
  - `remove_item_from_cart()` - Xóa khỏi giỏ
  - `clear_cart()` - Xóa toàn bộ giỏ

### 4. Order Service
- `OrderService`: Business logic cho Order
  - `create_order()` - Tạo đơn từ cart (transaction)
  - `get_all_orders()` - Lấy danh sách
  - `update_order_status()` - Cập nhật trạng thái
  - `_create_payment()` - Private method tạo payment
  - `_create_shipment()` - Private method tạo shipment
  - `_clear_cart()` - Private method xóa cart

### 5. Payment Service
- `PaymentService`: Business logic cho Payment
  - `create_payment()` - Tạo payment
  - `process_payment()` - Xử lý thanh toán
  - `refund_payment()` - Hoàn tiền
  - `_update_order_status()` - Private method

### 6. Shipping Service
- `ShipmentService`: Business logic cho Shipment
  - `create_shipment()` - Tạo đơn vận chuyển
  - `update_shipment_status()` - Cập nhật trạng thái
  - `start_shipping()` - Bắt đầu giao hàng
  - `get_shipment_by_tracking()` - Track theo số

### 7. Rating Service
- `RatingService`: Business logic cho Rating
  - `create_rating()` - Tạo đánh giá
  - `get_ratings()` - Lấy danh sách (có filters)
  - `get_book_rating_stats()` - Thống kê đánh giá
  - `update_rating()` - Cập nhật đánh giá

### 8. API Gateway
- `CustomerGatewayService` - Gọi Customer Service
- `BookGatewayService` - Gọi Book Service
- `CartGatewayService` - Gọi Cart Service
- `OrderGatewayService` - Gọi Order Service
- `PaymentGatewayService` - Gọi Payment Service
- `ShippingGatewayService` - Gọi Shipping Service
- `RatingGatewayService` - Gọi Rating Service

## 🔄 Workflow ví dụ

### Tạo đơn hàng (Order Service):

```python
# views.py - HTTP layer
def create(self, request):
    order = OrderService.create_order(
        customer_id=...,
        cart_id=...,
        ...
    )
    return Response(serializer.data, status=201)

# services.py - Business logic
@transaction.atomic
def create_order(...) -> Order:
    # 1. Validate cart
    cart_data = OrderService._get_cart_data(cart_id)
    
    # 2. Create order
    order = Order.objects.create(...)
    
    # 3. Create order items
    for item in cart_data['items']:
        OrderItem.objects.create(...)
    
    # 4. Create payment
    OrderService._create_payment(order.id, amount)
    
    # 5. Clear cart
    OrderService._clear_cart(cart_data['items'])
    
    return order
```

## ✨ Lợi ích

### 1. **Clean Code**
- Views ngắn gọn, dễ đọc
- Business logic tập trung ở một nơi
- Dễ maintain và debug

### 2. **Scalability**
- Dễ thêm business rules mới
- Có thể chuyển sang async/celery tasks
- Có thể tách thành microservices nhỏ hơn

### 3. **Testing**
- Unit test service layer độc lập
- Integration test views với mock services
- Dễ dàng test edge cases

### 4. **Documentation**
- Type hints tự động gợi ý trong IDE
- Docstrings rõ ràng
- Code tự document

## 🚀 Best Practices được áp dụng

1. ✅ **Single Responsibility Principle** - Mỗi class có một trách nhiệm duy nhất
2. ✅ **DRY (Don't Repeat Yourself)** - Logic chung được tái sử dụng
3. ✅ **Explicit is better than implicit** - Type hints rõ ràng
4. ✅ **Fail fast** - Validate sớm, raise exception rõ ràng
5. ✅ **Transaction management** - Sử dụng @transaction.atomic khi cần
6. ✅ **Error handling** - Try-catch ở đúng nơi, log errors
7. ✅ **Private methods** - Sử dụng `_method_name` cho internal logic

## 📝 Migration Guide

Nếu cần thêm feature mới:

1. **Thêm model** (nếu cần) - `models.py`
2. **Thêm serializer** (nếu cần) - `serializers.py`
3. **Thêm business logic** - `services.py` ⭐
4. **Thêm HTTP endpoint** - `views.py` (gọi service)
5. **Thêm tests** - `tests.py` (test service layer)

Ví dụ: Thêm tính năng "add to wishlist"

```python
# services.py
class BookService:
    @staticmethod
    def add_to_wishlist(customer_id: int, book_id: int) -> Wishlist:
        """Business logic để thêm vào wishlist"""
        # Validate customer exists
        # Validate book exists
        # Create wishlist entry
        # Return wishlist object
        ...

# views.py
class BookViewSet:
    @action(detail=True, methods=['post'])
    def add_to_wishlist(self, request, pk=None):
        """HTTP endpoint"""
        customer_id = request.data.get('customer_id')
        wishlist = BookService.add_to_wishlist(customer_id, pk)
        return Response({'status': 'added'})
```

## 🎓 Kết luận

Refactoring này giúp:
- ✅ Code sạch, dễ hiểu
- ✅ Tách biệt concerns rõ ràng
- ✅ Dễ test và maintain
- ✅ Follow best practices
- ✅ Scalable và extensible

Hệ thống giờ đây tuân theo kiến trúc tốt hơn và sẵn sàng cho việc mở rộng!
