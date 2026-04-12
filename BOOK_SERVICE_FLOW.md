# Luồng gọi đến Book Service

## 📊 Sơ đồ tổng quan

```
┌──────────────┐
│   Browser    │  User truy cập http://localhost:8000
│   (Client)   │
└──────┬───────┘
       │ HTTP Request
       ▼
┌─────────────────────────────────────────────────────────┐
│              API Gateway (Port 8000)                     │
│  ┌──────────────┐          ┌──────────────────────┐    │
│  │  views.py    │   gọi    │   services.py        │    │
│  │  home()      │  ────▶   │ BookGatewayService   │    │
│  │              │          │ .get_all_books()     │    │
│  └──────────────┘          └──────────┬───────────┘    │
└────────────────────────────────────────┼────────────────┘
                                         │ HTTP Request
                                         │ GET http://localhost:8002/api/books/
                                         ▼
┌─────────────────────────────────────────────────────────┐
│              Book Service (Port 8002)                    │
│  ┌──────────────┐          ┌──────────────────────┐    │
│  │  views.py    │   gọi    │   services.py        │    │
│  │ BookViewSet  │  ────▶   │   BookService        │    │
│  │  .list()     │          │ .get_all_books()     │    │
│  └──────┬───────┘          └──────────┬───────────┘    │
│         │                              │                 │
│         │ serialize                    │ query DB        │
│         ▼                              ▼                 │
│  ┌──────────────┐          ┌──────────────────────┐    │
│  │serializers.py│          │     models.py        │    │
│  │BookSerializer│          │   Book.objects.all() │    │
│  └──────────────┘          └──────────────────────┘    │
│         │                              │                 │
│         └──────────┬───────────────────┘                │
│                    │ QuerySet                            │
│                    ▼                                     │
│            ┌──────────────┐                             │
│            │  Database    │                             │
│            │ (SQLite)     │                             │
│            └──────────────┘                             │
└─────────────────────────────────────────────────────────┘
                    │ JSON Response
                    │ [{"id": 1, "title": "..."}, ...]
                    ▼
┌─────────────────────────────────────────────────────────┐
│              API Gateway (Port 8000)                     │
│  Nhận response, render HTML template                    │
└──────────────────────────────────────────────────────────┘
                    │ HTML Response
                    ▼
┌──────────────┐
│   Browser    │  Hiển thị danh sách sách
│   (Client)   │
└──────────────┘
```

## 🔍 Chi tiết từng bước

### **Bước 1: User truy cập trang chủ**
```
URL: http://localhost:8000/
```

### **Bước 2: API Gateway nhận request**

**File: `api_gateway/gateway/views.py`**
```python
def home(request):
    """Trang chủ - Hiển thị danh sách sách"""
    books = BookGatewayService.get_all_books()  # Gọi service
    return render(request, 'gateway/home.html', {'books': books})
```

### **Bước 3: Gateway Service gọi Book Service**

**File: `api_gateway/gateway/services.py`**
```python
class BookGatewayService:
    @staticmethod
    def get_all_books() -> List[Dict]:
        """Lấy danh sách sách"""
        try:
            # Gọi HTTP Request đến Book Service
            response = requests.get(
                'http://localhost:8002/api/books/',  # Book Service URL
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('results', data)
            return []
        except Exception as e:
            print(f"Error fetching books: {str(e)}")
            return []
```

**HTTP Request gửi đi:**
```http
GET http://localhost:8002/api/books/ HTTP/1.1
Host: localhost:8002
Accept: application/json
```

### **Bước 4: Book Service nhận request**

**File: `book_service/books/urls.py`**
```python
router = DefaultRouter()
router.register(r'books', BookViewSet, basename='book')
# Route: /api/books/ -> BookViewSet.list()
```

**File: `book_service/books/views.py`**
```python
class BookViewSet(viewsets.ModelViewSet):
    def list(self, request, *args, **kwargs):
        """GET /books/ - Lấy danh sách sách"""
        # Apply filters từ query params (search, category, etc.)
        queryset = self.filter_queryset(self.get_queryset())
        
        # Phân trang
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
```

**Thực tế Views gọi:**
```python
# self.get_queryset() -> Book.objects.all()
# self.filter_queryset() -> apply search, filters
# self.get_serializer() -> BookSerializer
```

### **Bước 5: Service Layer xử lý business logic**

**File: `book_service/books/services.py`**
```python
class BookService:
    @staticmethod
    def get_all_books(filters: dict = None) -> QuerySet:
        """Lấy danh sách sách với filters"""
        queryset = Book.objects.all()  # Query database
        
        if filters:
            if 'category' in filters:
                queryset = queryset.filter(category=filters['category'])
            if 'author' in filters:
                queryset = queryset.filter(author=filters['author'])
        
        return queryset
```

### **Bước 6: Models truy vấn Database**

**File: `book_service/books/models.py`**
```python
class Book(models.Model):
    title = models.CharField(max_length=500)
    author = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.IntegerField(default=0)
    # ... các fields khác
```

**SQL Query thực thi:**
```sql
SELECT * FROM books 
WHERE is_available = 1 
ORDER BY created_at DESC;
```

### **Bước 7: Serializer chuyển đổi dữ liệu**

**File: `book_service/books/serializers.py`**
```python
class BookSerializer(serializers.ModelSerializer):
    in_stock = serializers.ReadOnlyField()
    
    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'price', 
                  'stock_quantity', 'in_stock', ...]
```

**Output:**
```python
QuerySet[Book(id=1, title="Đắc Nhân Tâm"...)] 
    ↓ serialize
[
    {
        "id": 1,
        "title": "Đắc Nhân Tâm",
        "author": "Dale Carnegie",
        "price": "80000.00",
        "stock_quantity": 100,
        "in_stock": true,
        ...
    },
    {...}
]
```

### **Bước 8: Response trả về API Gateway**

**HTTP Response từ Book Service:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
    "count": 3,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 1,
            "title": "Đắc Nhân Tâm",
            "author": "Dale Carnegie",
            "price": "80000.00",
            "stock_quantity": 100,
            "in_stock": true
        },
        {...},
        {...}
    ]
}
```

### **Bước 9: API Gateway render HTML**

**File: `api_gateway/gateway/views.py`**
```python
def home(request):
    books = BookGatewayService.get_all_books()  # Nhận JSON data
    return render(request, 'gateway/home.html', {'books': books})  # Render template
```

**File: `api_gateway/gateway/templates/gateway/home.html`**
```html
{% for book in books %}
    <div class="card book-card">
        <h5>{{ book.title }}</h5>
        <p>{{ book.author }}</p>
        <p><strong>{{ book.price }} VNĐ</strong></p>
        <span class="badge">Còn hàng: {{ book.stock_quantity }}</span>
        <a href="/books/{{ book.id }}/">Xem chi tiết</a>
    </div>
{% endfor %}
```

### **Bước 10: Browser nhận HTML và hiển thị**

Browser render HTML với CSS (Bootstrap) và hiển thị danh sách sách cho user.

---

## 🎯 Các luồng khác với Book Service

### **1. Xem chi tiết sách**

```
Browser: GET /books/1/
    ↓
API Gateway views.book_detail(book_id=1)
    ↓
BookGatewayService.get_book_by_id(1)
    ↓
HTTP: GET http://localhost:8002/api/books/1/
    ↓
BookViewSet.retrieve(pk=1)
    ↓
BookService.get_book_by_id(1)
    ↓
Book.objects.get(id=1)
    ↓
BookSerializer(book)
    ↓
JSON Response
    ↓
Render book_detail.html
```

### **2. Thêm sách vào giỏ hàng (Cart Service gọi Book Service)**

```
User: Click "Thêm vào giỏ"
    ↓
API Gateway: add_to_cart(book_id=1)
    ↓
CartGatewayService.add_item_to_cart(customer_id, book_id)
    ↓
HTTP: POST http://localhost:8003/api/cart-items/
    ↓
CartViewSet.create()
    ↓
CartItemService.add_item_to_cart()
    ↓
HTTP: GET http://localhost:8002/api/books/1/  ← Cart Service gọi Book Service
    ↓
BookViewSet.retrieve()
    ↓
BookService.get_book_by_id()
    ↓
Book.objects.get(id=1)
    ↓
Lấy giá sách để lưu vào CartItem
```

---

## 📝 Request/Response Examples

### **Request từ Gateway đến Book Service:**
```http
GET /api/books/ HTTP/1.1
Host: localhost:8002
Accept: application/json
User-Agent: python-requests/2.32.3
```

### **Response từ Book Service:**
```json
{
    "count": 3,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 1,
            "title": "Đắc Nhân Tâm",
            "author": "Dale Carnegie",
            "isbn": "978-1234567890",
            "price": "80000.00",
            "stock_quantity": 100,
            "category": "Self-help",
            "is_available": true,
            "in_stock": true,
            "created_at": "2026-03-19T10:00:00Z"
        }
    ]
}
```

---

## 🔄 Luồng với Filters/Search

```
Browser: GET /?search=đắc&category=Self-help
    ↓
API Gateway (không thay đổi, vẫn gọi get_all_books())
    ↓
HTTP: GET http://localhost:8002/api/books/?search=đắc&category=Self-help
    ↓
BookViewSet.list()
    ↓
self.filter_queryset() áp dụng:
    - SearchFilter: title, author LIKE '%đắc%'
    - FilterSet: category = 'Self-help'
    ↓
SQL: SELECT * FROM books 
     WHERE (title LIKE '%đắc%' OR author LIKE '%đắc%')
     AND category = 'Self-help'
    ↓
Response: Only matching books
```

---

## 🎯 Tổng kết

### **Các layers trong Book Service:**

1. **HTTP Layer** (`views.py`) - Nhận request, validate, trả response
2. **Business Logic Layer** (`services.py`) - Xử lý logic nghiệp vụ
3. **Data Layer** (`models.py`) - Tương tác với database
4. **Serialization Layer** (`serializers.py`) - Chuyển đổi data format

### **Điểm mạnh của kiến trúc này:**

✅ **Tách biệt concerns** - Mỗi layer có trách nhiệm riêng  
✅ **Dễ test** - Có thể test từng layer độc lập  
✅ **Dễ maintain** - Thay đổi ở một layer không ảnh hưởng layer khác  
✅ **Scalable** - Có thể scale từng service độc lập  
✅ **Reusable** - Service layer có thể được gọi từ nhiều nơi  

### **Communication giữa services:**

- API Gateway ↔ Book Service: **HTTP REST API**
- Cart Service ↔ Book Service: **HTTP REST API**
- Order Service ↔ Book Service: **HTTP REST API** (qua Cart Service)

Tất cả đều là **synchronous HTTP calls** với JSON format.
