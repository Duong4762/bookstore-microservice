# Hệ thống Bookstore Microservice

Hệ thống quản lý nhà sách được xây dựng theo kiến trúc Microservices với Django và HTML Templates.

## 🏗️ Kiến trúc hệ thống

Hệ thống bao gồm 7 microservices độc lập và 1 API Gateway:

### 1. **Customer Service** (Port 8001)
- Quản lý thông tin khách hàng
- Đăng ký tài khoản mới
- Tự động tạo giỏ hàng khi đăng ký
- **API Endpoints:**
  - `POST /api/customers/` - Tạo khách hàng mới
  - `GET /api/customers/` - Lấy danh sách khách hàng
  - `GET /api/customers/{id}/` - Chi tiết khách hàng
  - `PUT /api/customers/{id}/` - Cập nhật thông tin
  - `DELETE /api/customers/{id}/` - Xóa khách hàng

### 2. **Book Service** (Port 8002)
- Quản lý danh mục sách
- CRUD operations cho sách
- Tìm kiếm và lọc sách
- **API Endpoints:**
  - `GET /api/books/` - Danh sách sách (có pagination, search, filter)
  - `POST /api/books/` - Thêm sách mới
  - `GET /api/books/{id}/` - Chi tiết sách
  - `PUT /api/books/{id}/` - Cập nhật sách
  - `DELETE /api/books/{id}/` - Xóa sách
  - `GET /api/books/available/` - Lấy sách còn hàng

### 3. **Cart Service** (Port 8003)
- Quản lý giỏ hàng của khách hàng
- Thêm/xóa/cập nhật sản phẩm trong giỏ
- **API Endpoints:**
  - `GET /api/carts/` - Danh sách giỏ hàng
  - `GET /api/carts/{id}/` - Chi tiết giỏ hàng
  - `GET /api/carts/by_customer/?customer_id=X` - Lấy giỏ hàng theo customer
  - `POST /api/cart-items/` - Thêm sách vào giỏ
  - `PUT /api/cart-items/{id}/` - Cập nhật số lượng
  - `DELETE /api/cart-items/{id}/` - Xóa sách khỏi giỏ

### 4. **Order Service** (Port 8004)
- Quản lý đơn hàng
- Tạo đơn từ giỏ hàng
- Theo dõi trạng thái đơn hàng
- **API Endpoints:**
  - `GET /api/orders/` - Danh sách đơn hàng
  - `POST /api/orders/` - Tạo đơn hàng mới
  - `GET /api/orders/{id}/` - Chi tiết đơn hàng
  - `PUT /api/orders/{id}/` - Cập nhật trạng thái
  - `DELETE /api/orders/{id}/` - Xóa đơn hàng

### 5. **Payment Service** (Port 8005)
- Xử lý thanh toán
- Quản lý giao dịch
- Hỗ trợ nhiều phương thức thanh toán
- **API Endpoints:**
  - `GET /api/payments/` - Danh sách giao dịch
  - `POST /api/payments/` - Tạo giao dịch mới
  - `GET /api/payments/{id}/` - Chi tiết giao dịch
  - `POST /api/payments/process/` - Xử lý thanh toán
  - `POST /api/payments/{id}/refund/` - Hoàn tiền

### 6. **Shipping Service** (Port 8006)
- Quản lý vận chuyển
- Tracking đơn hàng
- Cập nhật trạng thái giao hàng
- **API Endpoints:**
  - `GET /api/shipments/` - Danh sách đơn vận chuyển
  - `POST /api/shipments/` - Tạo đơn vận chuyển
  - `GET /api/shipments/{id}/` - Chi tiết vận chuyển
  - `PUT /api/shipments/{id}/` - Cập nhật trạng thái
  - `GET /api/shipments/track/?tracking_number=XXX` - Tracking
  - `POST /api/shipments/{id}/start_shipping/` - Bắt đầu giao hàng

### 7. **Comment and Rating Service** (Port 8007)
- Đánh giá và nhận xét sách
- Thống kê rating
- **API Endpoints:**
  - `GET /api/ratings/` - Danh sách đánh giá
  - `POST /api/ratings/` - Thêm đánh giá mới
  - `GET /api/ratings/{id}/` - Chi tiết đánh giá
  - `PUT /api/ratings/{id}/` - Cập nhật đánh giá
  - `DELETE /api/ratings/{id}/` - Xóa đánh giá
  - `GET /api/ratings/book_stats/?book_id=X` - Thống kê đánh giá sách

### 8. **API Gateway** (Port 8000)
- Frontend với HTML Templates
- Routing requests đến các microservices
- Tích hợp toàn bộ chức năng

## 📋 Yêu cầu hệ thống

- Python 3.11+
- pip
- Windows (hoặc Linux/Mac với một số điều chỉnh)

## 🚀 Cài đặt và chạy

### Bước 1: Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### Bước 2: Chạy tất cả services

#### Trên Windows:
```bash
start_all_services.bat
```

#### Trên Linux/Mac:
```bash
# Customer Service
cd customer_service && python manage.py migrate && python manage.py runserver 8001 &

# Book Service
cd book_service && python manage.py migrate && python manage.py runserver 8002 &

# Cart Service
cd cart_service && python manage.py migrate && python manage.py runserver 8003 &

# Order Service
cd order_service && python manage.py migrate && python manage.py runserver 8004 &

# Payment Service
cd payment_service && python manage.py migrate && python manage.py runserver 8005 &

# Shipping Service
cd shipping_service && python manage.py migrate && python manage.py runserver 8006 &

# Rating Service
cd comment_and_rating_service && python manage.py migrate && python manage.py runserver 8007 &

# API Gateway
cd api_gateway && python manage.py migrate && python manage.py runserver 8000 &
```

### Bước 3: Truy cập ứng dụng

Mở trình duyệt và truy cập: **http://localhost:8000**

## 🔗 Ports của các services

| Service | Port | URL |
|---------|------|-----|
| API Gateway | 8000 | http://localhost:8000 |
| Customer Service | 8001 | http://localhost:8001 |
| Book Service | 8002 | http://localhost:8002 |
| Cart Service | 8003 | http://localhost:8003 |
| Order Service | 8004 | http://localhost:8004 |
| Payment Service | 8005 | http://localhost:8005 |
| Shipping Service | 8006 | http://localhost:8006 |
| Rating Service | 8007 | http://localhost:8007 |

## 📖 Hướng dẫn sử dụng

### 1. Đăng ký khách hàng
1. Vào **Khách hàng** → **Đăng ký khách hàng mới**
2. Điền thông tin và submit
3. Hệ thống tự động tạo giỏ hàng cho khách hàng

### 2. Thêm sách vào giỏ hàng
1. Vào **Trang chủ**
2. Click **Xem chi tiết** trên sách bạn muốn mua
3. Nhập ID khách hàng và số lượng
4. Click **Thêm vào giỏ**

### 3. Xem giỏ hàng
1. Vào **Khách hàng** → Click **Giỏ hàng** của khách hàng
2. Xem các sản phẩm đã thêm

### 4. Đặt hàng
1. Trong giỏ hàng, điền thông tin giao hàng
2. Click **Đặt hàng**
3. Hệ thống tự động:
   - Tạo đơn hàng
   - Tạo giao dịch thanh toán
   - Xóa giỏ hàng

### 5. Theo dõi đơn hàng
1. Vào **Đơn hàng**
2. Click **Chi tiết** để xem thông tin đầy đủ
3. Xem trạng thái thanh toán và vận chuyển

### 6. Đánh giá sách
1. Vào chi tiết sách
2. Điền đánh giá và nhận xét
3. Submit đánh giá

## 🎨 Giao diện

Hệ thống sử dụng **Bootstrap 5** với giao diện hiện đại, responsive:
- 📱 Mobile-friendly
- 🎨 UI/UX chuyên nghiệp
- 🚀 Hiệu suất cao
- ✨ Animations mượt mà

## 🔄 Workflow hệ thống

```
1. Customer đăng ký → Customer Service tạo customer → Cart Service tự động tạo giỏ hàng

2. Customer xem sách → Book Service cung cấp danh sách sách

3. Customer thêm sách vào giỏ → Cart Service lưu trữ

4. Customer đặt hàng → Order Service tạo đơn hàng
   → Payment Service tạo giao dịch thanh toán
   → Cart Service xóa giỏ hàng

5. Thanh toán thành công → Payment Service cập nhật status
   → Order Service cập nhật trạng thái "paid"
   → Shipping Service tạo đơn vận chuyển

6. Giao hàng thành công → Shipping Service cập nhật status "delivered"
   → Order Service cập nhật trạng thái "delivered"

7. Customer đánh giá sách → Rating Service lưu đánh giá
```

## 🛠️ Công nghệ sử dụng

- **Backend:** Django 5.2, Django REST Framework
- **Frontend:** HTML5, Bootstrap 5, Bootstrap Icons
- **Database:** SQLite (mỗi service có DB riêng)
- **Communication:** REST API (HTTP requests)

## 📁 Cấu trúc thư mục

```
bookstore-microservice/
├── api_gateway/          # API Gateway với HTML Templates
├── customer_service/     # Customer Service
├── book_service/         # Book Service
├── cart_service/         # Cart Service
├── order_service/        # Order Service
├── payment_service/      # Payment Service
├── shipping_service/     # Shipping Service
├── comment_and_rating_service/  # Rating Service
├── requirements.txt      # Python dependencies
├── docker-compose.yml    # Docker configuration
├── start_all_services.bat  # Script khởi động (Windows)
└── README.md            # Tài liệu này
```

## 🐳 Chạy với Docker (Optional)

```bash
docker-compose up --build
```

## 📝 Notes

- Mỗi service có database riêng (SQLite)
- Services giao tiếp với nhau qua REST API
- API Gateway đóng vai trò frontend và routing
- Dữ liệu được đồng bộ qua HTTP requests giữa các services

## 👥 Tác giả

Dự án Kiến trúc Thiết kế Phần mềm - 2026

## 📄 License

MIT License
