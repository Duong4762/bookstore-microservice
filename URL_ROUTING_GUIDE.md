# URL Routing Configuration - Book Service

## 📍 Tổng quan: Từ URL đến Service Function

```
URL Path
   ↓
Django URLs (urls.py)
   ↓
DRF Router
   ↓
ViewSet Method
   ↓
Service Function
```

---

## 🔧 1. Main URL Configuration

**File: `book_service/book_service/urls.py`** (ROOT URLConf)

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('books.urls')),  # ← Tất cả /api/* được forward đến books.urls
]
```

### Ý nghĩa:
- `http://localhost:8002/admin/` → Django Admin
- `http://localhost:8002/api/` → Forward đến `books/urls.py`

---

## 🔧 2. App URL Configuration + Router

**File: `book_service/books/urls.py`**

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookViewSet

# Tạo router
router = DefaultRouter()

# Register ViewSet với router
router.register(r'books', BookViewSet, basename='book')
# ↑ prefix    ↑ ViewSet       ↑ basename cho reverse URL

urlpatterns = [
    path('', include(router.urls)),
]
```

### Router tự động tạo các URLs:

| URL Pattern | HTTP Method | ViewSet Method | Action |
|------------|-------------|----------------|---------|
| `/api/books/` | GET | `list()` | Lấy danh sách |
| `/api/books/` | POST | `create()` | Tạo mới |
| `/api/books/{id}/` | GET | `retrieve()` | Lấy chi tiết |
| `/api/books/{id}/` | PUT | `update()` | Cập nhật toàn bộ |
| `/api/books/{id}/` | PATCH | `partial_update()` | Cập nhật một phần |
| `/api/books/{id}/` | DELETE | `destroy()` | Xóa |
| `/api/books/available/` | GET | `available()` | Custom action |

---

## 🔧 3. ViewSet Configuration

**File: `book_service/books/views.py`**

```python
from rest_framework import viewsets
from .services import BookService

class BookViewSet(viewsets.ModelViewSet):
    """
    ModelViewSet tự động cung cấp các actions:
    - list, create, retrieve, update, partial_update, destroy
    """
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    
    # ============ STANDARD CRUD METHODS ============
    
    def list(self, request, *args, **kwargs):
        """
        GET /api/books/
        Gọi: BookService.get_all_books()
        """
        queryset = self.filter_queryset(self.get_queryset())
        # ... pagination logic
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """
        POST /api/books/
        Gọi: BookService.create_book()
        """
        book = BookService.create_book(request.data)
        return Response(serializer.data, status=201)
    
    def retrieve(self, request, *args, **kwargs):
        """
        GET /api/books/{id}/
        Gọi: BookService.get_book_by_id()
        """
        book = BookService.get_book_by_id(kwargs.get('pk'))
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        """
        PUT /api/books/{id}/
        Gọi: BookService.update_book()
        """
        book = BookService.update_book(kwargs.get('pk'), request.data)
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """
        DELETE /api/books/{id}/
        Gọi: BookService.delete_book()
        """
        success = BookService.delete_book(kwargs.get('pk'))
        return Response(status=204)
    
    # ============ CUSTOM ACTION ============
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        """
        GET /api/books/available/
        Gọi: BookService.get_available_books()
        
        @action parameters:
        - detail=False: URL không cần {id} (/books/available/)
        - methods=['get']: Chỉ accept GET request
        """
        books = BookService.get_available_books()
        return Response(serializer.data)
```

---

## 🎯 Mapping chi tiết: URL → Service

### **Ví dụ 1: Lấy danh sách sách**

```
Request: GET http://localhost:8002/api/books/
         │
         ├─ book_service/urls.py: path('api/', include('books.urls'))
         │
         ├─ books/urls.py: router.register(r'books', BookViewSet)
         │
         ├─ Router map: GET /books/ → BookViewSet.list()
         │
         ├─ books/views.py: BookViewSet.list()
         │   └─ Gọi BookService.get_all_books()
         │
         └─ books/services.py: BookService.get_all_books()
             └─ Book.objects.all()
```

### **Ví dụ 2: Lấy chi tiết sách ID=1**

```
Request: GET http://localhost:8002/api/books/1/
         │
         ├─ Router map: GET /books/{pk}/ → BookViewSet.retrieve(pk=1)
         │
         ├─ books/views.py: BookViewSet.retrieve(pk=1)
         │   └─ Gọi BookService.get_book_by_id(1)
         │
         └─ books/services.py: BookService.get_book_by_id(1)
             └─ Book.objects.get(id=1)
```

### **Ví dụ 3: Tạo sách mới**

```
Request: POST http://localhost:8002/api/books/
Body: {"title": "New Book", "author": "Author", ...}
         │
         ├─ Router map: POST /books/ → BookViewSet.create()
         │
         ├─ books/views.py: BookViewSet.create()
         │   └─ Gọi BookService.create_book(request.data)
         │
         └─ books/services.py: BookService.create_book(data)
             └─ Book.objects.create(...)
```

### **Ví dụ 4: Custom action - Lấy sách còn hàng**

```
Request: GET http://localhost:8002/api/books/available/
         │
         ├─ Router map: GET /books/available/ → BookViewSet.available()
         │   (Nhờ decorator @action)
         │
         ├─ books/views.py: BookViewSet.available()
         │   └─ Gọi BookService.get_available_books()
         │
         └─ books/services.py: BookService.get_available_books()
             └─ Book.objects.filter(is_available=True, stock_quantity__gt=0)
```

---

## 🔍 Django REST Framework Router - Chi tiết

### **DefaultRouter tự động tạo URLs:**

```python
router = DefaultRouter()
router.register(r'books', BookViewSet, basename='book')
```

**Tương đương với:**

```python
urlpatterns = [
    path('books/', BookViewSet.as_view({
        'get': 'list',
        'post': 'create'
    })),
    path('books/<int:pk>/', BookViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    })),
    # Custom actions
    path('books/available/', BookViewSet.as_view({
        'get': 'available'
    })),
]
```

### **HTTP Method → ViewSet Method Mapping:**

```python
{
    'GET': {
        '/books/': 'list',              # Danh sách
        '/books/{pk}/': 'retrieve',     # Chi tiết
        '/books/available/': 'available' # Custom action
    },
    'POST': {
        '/books/': 'create'             # Tạo mới
    },
    'PUT': {
        '/books/{pk}/': 'update'        # Cập nhật toàn bộ
    },
    'PATCH': {
        '/books/{pk}/': 'partial_update' # Cập nhật một phần
    },
    'DELETE': {
        '/books/{pk}/': 'destroy'       # Xóa
    }
}
```

---

## 📝 Settings.py - URL Configuration

**File: `book_service/book_service/settings.py`**

```python
# Root URL configuration
ROOT_URLCONF = 'book_service.urls'  # ← Chỉ định file urls.py chính

# INSTALLED_APPS phải có:
INSTALLED_APPS = [
    ...
    'rest_framework',  # Để sử dụng DRF Router
    'books',           # App của chúng ta
]
```

---

## 🎯 Flow hoàn chỉnh với Query Parameters

### **Request: GET /api/books/?search=đắc&category=Self-help**

```
1. Django nhận request
   URL: /api/books/?search=đắc&category=Self-help
   
2. book_service/urls.py
   Match: path('api/', include('books.urls'))
   Forward: /books/?search=đắc&category=Self-help
   
3. books/urls.py
   Router match: GET /books/ → BookViewSet.list()
   
4. BookViewSet.list()
   - request.query_params.get('search') → 'đắc'
   - request.query_params.get('category') → 'Self-help'
   - self.filter_queryset() áp dụng filters
   
5. DjangoFilterBackend & SearchFilter
   - SearchFilter: WHERE (title LIKE '%đắc%' OR author LIKE '%đắc%')
   - FilterSet: WHERE category = 'Self-help'
   
6. BookService.get_all_books(filters={'category': 'Self-help'})
   
7. Book.objects.filter(category='Self-help')
                .filter(Q(title__icontains='đắc') | Q(author__icontains='đắc'))
```

---

## 🛠️ Debugging URLs

### **Xem tất cả URLs được đăng ký:**

```bash
cd book_service
python manage.py show_urls
```

**Output:**
```
/api/books/                     books.views.BookViewSet     book-list
/api/books/{pk}/               books.views.BookViewSet     book-detail
/api/books/available/          books.views.BookViewSet     book-available
```

### **Test URLs bằng curl:**

```bash
# List books
curl http://localhost:8002/api/books/

# Get book detail
curl http://localhost:8002/api/books/1/

# Create book
curl -X POST http://localhost:8002/api/books/ \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","author":"Author","price":100,"stock_quantity":10}'

# Get available books
curl http://localhost:8002/api/books/available/

# Search books
curl "http://localhost:8002/api/books/?search=đắc"

# Filter by category
curl "http://localhost:8002/api/books/?category=Self-help"
```

---

## 📚 Tóm tắt: Config ở đâu?

| File | Chức năng | Config gì? |
|------|-----------|------------|
| **book_service/urls.py** | Main URLConf | Định nghĩa `/api/` prefix |
| **books/urls.py** | App URLs | Register ViewSet với Router |
| **books/views.py** | ViewSet | Map HTTP methods → Service functions |
| **books/services.py** | Business Logic | Các functions xử lý logic |
| **settings.py** | Django config | `ROOT_URLCONF`, `INSTALLED_APPS` |

---

## 🎯 Key Points

1. **Django URLs** (`urls.py`) → Định nghĩa URL patterns
2. **DRF Router** → Tự động tạo RESTful URLs từ ViewSet
3. **ViewSet** → Map HTTP methods đến Python methods
4. **Services** → Được gọi bởi ViewSet methods

### **Luồng đầy đủ:**
```
URL Request
  → Django URLs (urls.py) - Routing
    → DRF Router - Map HTTP method
      → ViewSet Method (views.py) - HTTP handling
        → Service Function (services.py) - Business logic
          → Model (models.py) - Database query
```

**Điểm quan trọng:** Router của DRF tự động config mapping dựa trên convention (GET /books/ → list(), POST /books/ → create(), etc.). Bạn chỉ cần register ViewSet là đủ! 🎉
