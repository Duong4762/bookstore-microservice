# API Documentation - Bookstore Microservice

## Overview
Tài liệu API đầy đủ cho hệ thống Bookstore Microservice.

---

## 1. Customer Service (Port 8001)

Base URL: `http://localhost:8001/api`

### 1.1. Create Customer
**Endpoint:** `POST /customers/`

**Request Body:**
```json
{
  "email": "customer@example.com",
  "full_name": "Nguyễn Văn A",
  "phone_number": "0123456789",
  "address": "123 Đường ABC, TP.HCM",
  "date_of_birth": "1990-01-01"
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "email": "customer@example.com",
  "full_name": "Nguyễn Văn A",
  "phone_number": "0123456789",
  "address": "123 Đường ABC, TP.HCM",
  "date_of_birth": "1990-01-01",
  "created_at": "2026-03-19T10:00:00Z",
  "updated_at": "2026-03-19T10:00:00Z",
  "is_active": true
}
```

### 1.2. List Customers
**Endpoint:** `GET /customers/`

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "email": "customer@example.com",
    "full_name": "Nguyễn Văn A",
    ...
  }
]
```

### 1.3. Get Customer Detail
**Endpoint:** `GET /customers/{id}/`

### 1.4. Update Customer
**Endpoint:** `PUT /customers/{id}/`

### 1.5. Delete Customer
**Endpoint:** `DELETE /customers/{id}/`

---

## 2. Book Service (Port 8002)

Base URL: `http://localhost:8002/api`

### 2.1. Create Book
**Endpoint:** `POST /books/`

**Request Body:**
```json
{
  "title": "Đắc Nhân Tâm",
  "author": "Dale Carnegie",
  "isbn": "978-1234567890",
  "publisher": "NXB Trẻ",
  "publication_year": 2020,
  "description": "Sách về kỹ năng giao tiếp",
  "price": 80000,
  "stock_quantity": 100,
  "category": "Self-help",
  "language": "Vietnamese",
  "pages": 320,
  "cover_image_url": "https://example.com/image.jpg"
}
```

**Response:** `201 Created`

### 2.2. List Books
**Endpoint:** `GET /books/`

**Query Parameters:**
- `page` - Số trang (default: 1)
- `search` - Tìm kiếm theo title, author, isbn
- `category` - Lọc theo category
- `author` - Lọc theo author
- `ordering` - Sắp xếp (price, -price, created_at, -created_at)

**Example:**
```
GET /books/?search=đắc&category=Self-help&ordering=price
```

### 2.3. Get Available Books
**Endpoint:** `GET /books/available/`

Lấy danh sách sách còn hàng (is_available=True và stock_quantity > 0)

---

## 3. Cart Service (Port 8003)

Base URL: `http://localhost:8003/api`

### 3.1. Create Cart
**Endpoint:** `POST /carts/`

**Request Body:**
```json
{
  "customer_id": 1
}
```

### 3.2. Get Cart by Customer
**Endpoint:** `GET /carts/by_customer/?customer_id={customer_id}`

**Response:** `200 OK`
```json
{
  "id": 1,
  "customer_id": 1,
  "items": [
    {
      "id": 1,
      "cart": 1,
      "book_id": 1,
      "quantity": 2,
      "price": "80000.00",
      "subtotal": 160000,
      "book_title": "Đắc Nhân Tâm",
      "created_at": "2026-03-19T10:00:00Z"
    }
  ],
  "total_items": 2,
  "total_price": 160000,
  "created_at": "2026-03-19T10:00:00Z"
}
```

### 3.3. Add Item to Cart
**Endpoint:** `POST /cart-items/`

**Request Body:**
```json
{
  "cart_id": 1,
  "book_id": 1,
  "quantity": 2
}
```

**Response:** `201 Created` hoặc `200 OK` (nếu sách đã có trong giỏ)

### 3.4. Update Cart Item
**Endpoint:** `PUT /cart-items/{id}/`

**Request Body:**
```json
{
  "quantity": 3
}
```

### 3.5. Delete Cart Item
**Endpoint:** `DELETE /cart-items/{id}/`

---

## 4. Order Service (Port 8004)

Base URL: `http://localhost:8004/api`

### 4.1. Create Order
**Endpoint:** `POST /orders/`

**Request Body:**
```json
{
  "customer_id": 1,
  "cart_id": 1,
  "shipping_address": "456 Đường XYZ, TP.HCM",
  "phone_number": "0987654321",
  "notes": "Giao hàng giờ hành chính"
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "customer_id": 1,
  "status": "pending",
  "total_amount": "160000.00",
  "shipping_address": "456 Đường XYZ, TP.HCM",
  "phone_number": "0987654321",
  "notes": "Giao hàng giờ hành chính",
  "items": [
    {
      "id": 1,
      "book_id": 1,
      "quantity": 2,
      "price": "80000.00",
      "subtotal": 160000,
      "book_title": "Đắc Nhân Tâm"
    }
  ],
  "created_at": "2026-03-19T10:00:00Z"
}
```

### 4.2. List Orders
**Endpoint:** `GET /orders/`

**Query Parameters:**
- `customer_id` - Lọc theo customer

### 4.3. Get Order Detail
**Endpoint:** `GET /orders/{id}/`

### 4.4. Update Order Status
**Endpoint:** `PUT /orders/{id}/`

**Request Body:**
```json
{
  "status": "paid"
}
```

**Available Statuses:**
- `pending` - Chờ xử lý
- `paid` - Đã thanh toán
- `shipped` - Đang giao hàng
- `delivered` - Đã giao hàng
- `cancelled` - Đã hủy

---

## 5. Payment Service (Port 8005)

Base URL: `http://localhost:8005/api`

### 5.1. Create Payment
**Endpoint:** `POST /payments/`

**Request Body:**
```json
{
  "order_id": 1,
  "amount": 160000,
  "payment_method": "COD"
}
```

**Payment Methods:**
- `COD` - Cash on Delivery
- `CARD` - Credit/Debit Card
- `BANK_TRANSFER` - Bank Transfer
- `E_WALLET` - E-Wallet

### 5.2. Process Payment
**Endpoint:** `POST /payments/process/`

**Request Body:**
```json
{
  "payment_id": 1,
  "transaction_id": "PAY-123456789",
  "notes": "Thanh toán thành công"
}
```

**Response:** `200 OK`

### 5.3. Refund Payment
**Endpoint:** `POST /payments/{id}/refund/`

### 5.4. List Payments
**Endpoint:** `GET /payments/`

**Query Parameters:**
- `order_id` - Lọc theo order

---

## 6. Shipping Service (Port 8006)

Base URL: `http://localhost:8006/api`

### 6.1. Create Shipment
**Endpoint:** `POST /shipments/`

**Request Body:**
```json
{
  "order_id": 1,
  "shipping_address": "456 Đường XYZ, TP.HCM",
  "carrier": "Giao Hàng Nhanh",
  "estimated_delivery": "2026-03-25T10:00:00Z"
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "order_id": 1,
  "tracking_number": "TRK-ABC123XYZ456",
  "carrier": "Giao Hàng Nhanh",
  "shipping_address": "456 Đường XYZ, TP.HCM",
  "status": "preparing",
  "estimated_delivery": "2026-03-25T10:00:00Z",
  "created_at": "2026-03-19T10:00:00Z"
}
```

### 6.2. Start Shipping
**Endpoint:** `POST /shipments/{id}/start_shipping/`

Cập nhật status từ "preparing" → "shipping"

### 6.3. Track Shipment
**Endpoint:** `GET /shipments/track/?tracking_number={tracking_number}`

### 6.4. Update Shipment Status
**Endpoint:** `PUT /shipments/{id}/`

**Request Body:**
```json
{
  "status": "delivered"
}
```

**Available Statuses:**
- `preparing` - Đang chuẩn bị
- `shipping` - Đang giao hàng
- `delivered` - Đã giao hàng
- `returned` - Trả hàng
- `cancelled` - Đã hủy

---

## 7. Rating Service (Port 8007)

Base URL: `http://localhost:8007/api`

### 7.1. Create Rating
**Endpoint:** `POST /ratings/`

**Request Body:**
```json
{
  "book_id": 1,
  "customer_id": 1,
  "rating": 5,
  "comment": "Sách rất hay!"
}
```

**Constraints:**
- `rating`: 1-5 (integer)
- Mỗi customer chỉ có thể đánh giá 1 sách 1 lần

### 7.2. List Ratings
**Endpoint:** `GET /ratings/`

**Query Parameters:**
- `book_id` - Lọc theo sách
- `customer_id` - Lọc theo khách hàng

### 7.3. Get Book Rating Stats
**Endpoint:** `GET /ratings/book_stats/?book_id={book_id}`

**Response:** `200 OK`
```json
{
  "book_id": 1,
  "average_rating": 4.5,
  "total_ratings": 10,
  "rating_distribution": {
    "1_star": 0,
    "2_star": 1,
    "3_star": 2,
    "4_star": 3,
    "5_star": 4
  }
}
```

### 7.4. Update Rating
**Endpoint:** `PUT /ratings/{id}/`

### 7.5. Delete Rating
**Endpoint:** `DELETE /ratings/{id}/`

---

## Error Responses

### 400 Bad Request
```json
{
  "error": "Error message here",
  "field_name": ["Validation error"]
}
```

### 404 Not Found
```json
{
  "error": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal server error message"
}
```

---

## Authentication

Hiện tại hệ thống chưa implement authentication. Tất cả endpoints đều public access.

## Rate Limiting

Không có rate limiting trong phiên bản hiện tại.

## Pagination

Các list endpoints sử dụng pagination với format:
```json
{
  "count": 100,
  "next": "http://localhost:8001/api/customers/?page=2",
  "previous": null,
  "results": [...]
}
```

- Page size mặc định: 10 items/page
- Query parameter: `?page=2`
