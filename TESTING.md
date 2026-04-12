# Hướng dẫn Test Hệ thống Bookstore Microservice

## 🧪 Kịch bản test đầy đủ

### 1. Setup môi trường test

```bash
# Cài đặt dependencies
pip install -r requirements.txt

# Khởi động tất cả services
start_all_services.bat
```

Đợi khoảng 10-15 giây để tất cả services khởi động hoàn tất.

### 2. Test Customer Service

#### 2.1. Tạo khách hàng mới qua UI
1. Truy cập: http://localhost:8000/customers/create/
2. Điền thông tin:
   - Họ tên: Nguyễn Văn A
   - Email: nguyenvana@example.com
   - Số điện thoại: 0123456789
   - Địa chỉ: 123 Đường ABC, Quận 1, TP.HCM
3. Click **Đăng ký**
4. ✅ Kiểm tra: Chuyển đến trang danh sách khách hàng, thấy khách hàng vừa tạo

#### 2.2. Test API trực tiếp
```bash
# Tạo customer
curl -X POST http://localhost:8001/api/customers/ \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"test@example.com\",\"full_name\":\"Test User\",\"phone_number\":\"0987654321\"}"

# Lấy danh sách customers
curl http://localhost:8001/api/customers/

# Lấy chi tiết customer ID=1
curl http://localhost:8001/api/customers/1/
```

### 3. Test Book Service

#### 3.1. Thêm sách qua API
```bash
# Thêm sách 1
curl -X POST http://localhost:8002/api/books/ \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"Đắc Nhân Tâm\",\"author\":\"Dale Carnegie\",\"price\":80000,\"stock_quantity\":100,\"description\":\"Sách về kỹ năng giao tiếp\",\"category\":\"Self-help\"}"

# Thêm sách 2
curl -X POST http://localhost:8002/api/books/ \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"Tuổi Trẻ Đáng Giá Bao Nhiêu\",\"author\":\"Rosie Nguyễn\",\"price\":60000,\"stock_quantity\":50,\"description\":\"Sách về phát triển bản thân\",\"category\":\"Self-help\"}"

# Thêm sách 3
curl -X POST http://localhost:8002/api/books/ \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"Nhà Giả Kim\",\"author\":\"Paulo Coelho\",\"price\":70000,\"stock_quantity\":75,\"description\":\"Tiểu thuyết triết lý\",\"category\":\"Novel\"}"
```

#### 3.2. Xem sách qua UI
1. Truy cập: http://localhost:8000
2. ✅ Kiểm tra: Thấy danh sách sách hiển thị đẹp với Bootstrap cards

### 4. Test Cart Service

#### 4.1. Kiểm tra giỏ hàng tự động tạo
1. Truy cập: http://localhost:8000/customers/
2. Click **Giỏ hàng** của customer vừa tạo
3. ✅ Kiểm tra: Giỏ hàng đã được tự động tạo khi đăng ký

#### 4.2. Thêm sách vào giỏ hàng
1. Vào trang chủ: http://localhost:8000
2. Click **Xem chi tiết** trên sách "Đắc Nhân Tâm"
3. Nhập:
   - ID Khách hàng: 1
   - Số lượng: 2
4. Click **Thêm vào giỏ**
5. ✅ Kiểm tra: Thông báo thành công hiển thị

6. Làm tương tự với sách "Nhà Giả Kim", số lượng: 1

#### 4.3. Xem giỏ hàng
1. Truy cập: http://localhost:8000/cart/1/
2. ✅ Kiểm tra:
   - Có 2 sách trong giỏ
   - Tổng tiền = 80000*2 + 70000*1 = 230000 VNĐ
   - Tổng số sản phẩm = 3

### 5. Test Order Service

#### 5.1. Tạo đơn hàng
1. Trong trang giỏ hàng (http://localhost:8000/cart/1/)
2. Điền thông tin:
   - Địa chỉ giao hàng: 456 Đường XYZ, Quận 3, TP.HCM
   - Số điện thoại: 0123456789
   - Ghi chú: Giao hàng giờ hành chính
3. Click **Đặt hàng**
4. ✅ Kiểm tra:
   - Chuyển đến trang chi tiết đơn hàng
   - Đơn hàng có status "pending"
   - Giỏ hàng đã được xóa

#### 5.2. Xem danh sách đơn hàng
1. Truy cập: http://localhost:8000/orders/
2. ✅ Kiểm tra: Thấy đơn hàng vừa tạo

#### 5.3. Xem chi tiết đơn hàng
1. Click **Chi tiết** trên đơn hàng
2. ✅ Kiểm tra:
   - Thông tin đơn hàng đầy đủ
   - Danh sách sản phẩm chính xác
   - Có thông tin thanh toán (status: pending)
   - Chưa có thông tin vận chuyển

### 6. Test Payment Service

#### 6.1. Xử lý thanh toán qua API
```bash
# Lấy payment_id của đơn hàng 1
curl http://localhost:8005/api/payments/?order_id=1

# Giả sử payment_id = 1, xử lý thanh toán
curl -X POST http://localhost:8005/api/payments/process/ \
  -H "Content-Type: application/json" \
  -d "{\"payment_id\":1,\"transaction_id\":\"PAY-123456789\",\"notes\":\"Thanh toán thành công qua COD\"}"
```

#### 6.2. Kiểm tra trạng thái thanh toán
1. Refresh trang chi tiết đơn hàng: http://localhost:8000/orders/1/
2. ✅ Kiểm tra:
   - Payment status: "Đã thanh toán"
   - Order status: "Đã thanh toán"
   - Có thông tin vận chuyển (tự động tạo)

### 7. Test Shipping Service

#### 7.1. Bắt đầu vận chuyển qua API
```bash
# Lấy shipment_id
curl http://localhost:8006/api/shipments/?order_id=1

# Giả sử shipment_id = 1, bắt đầu vận chuyển
curl -X POST http://localhost:8006/api/shipments/1/start_shipping/ \
  -H "Content-Type: application/json"
```

#### 7.2. Kiểm tra trạng thái vận chuyển
1. Refresh trang chi tiết đơn hàng
2. ✅ Kiểm tra:
   - Shipment status: "Đang giao"
   - Order status: "Đang giao hàng"
   - Có tracking number

#### 7.3. Hoàn tất giao hàng
```bash
# Cập nhật trạng thái delivered
curl -X PUT http://localhost:8006/api/shipments/1/ \
  -H "Content-Type: application/json" \
  -d "{\"status\":\"delivered\"}"
```

#### 7.4. Kiểm tra đơn hàng hoàn tất
1. Refresh trang chi tiết đơn hàng
2. ✅ Kiểm tra:
   - Shipment status: "Đã giao"
   - Order status: "Đã giao hàng"
   - Có ngày giờ giao hàng

### 8. Test Rating Service

#### 8.1. Thêm đánh giá qua UI
1. Vào chi tiết sách "Đắc Nhân Tâm": http://localhost:8000/books/1/
2. Cuộn xuống phần "Đánh giá và nhận xét"
3. Điền form:
   - ID Khách hàng: 1
   - Đánh giá: 5 sao
   - Nhận xét: "Sách rất hay, nội dung bổ ích!"
4. Click **Gửi đánh giá**
5. ✅ Kiểm tra: Đánh giá hiển thị ở phần bình luận

#### 8.2. Thêm nhiều đánh giá
Tạo thêm 2-3 khách hàng và đánh giá khác nhau (3 sao, 4 sao) để test chức năng thống kê.

#### 8.3. Kiểm tra thống kê đánh giá
1. Refresh trang chi tiết sách
2. ✅ Kiểm tra:
   - Hiển thị điểm trung bình
   - Hiển thị tổng số đánh giá
   - Rating stars hiển thị chính xác

### 9. Test End-to-End Workflow

Thực hiện toàn bộ quy trình từ đầu đến cuối:

1. ✅ Đăng ký customer mới → Kiểm tra giỏ hàng tự động tạo
2. ✅ Thêm 3 sách khác nhau vào giỏ hàng
3. ✅ Xem giỏ hàng → Kiểm tra tổng tiền chính xác
4. ✅ Đặt hàng → Kiểm tra đơn hàng tạo thành công
5. ✅ Xử lý thanh toán → Kiểm tra payment & order status cập nhật
6. ✅ Bắt đầu vận chuyển → Kiểm tra shipment tạo và order status cập nhật
7. ✅ Hoàn tất giao hàng → Kiểm tra toàn bộ quy trình hoàn tất
8. ✅ Đánh giá sách → Kiểm tra rating hiển thị

### 10. Test Error Handling

#### 10.1. Test validation
```bash
# Tạo customer với email không hợp lệ
curl -X POST http://localhost:8001/api/customers/ \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"invalid-email\",\"full_name\":\"Test\"}"
# ✅ Kiểm tra: Trả về lỗi validation

# Thêm sách với giá âm
curl -X POST http://localhost:8002/api/books/ \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"Test\",\"author\":\"Test\",\"price\":-100,\"stock_quantity\":10}"
# ✅ Kiểm tra: Trả về lỗi validation
```

#### 10.2. Test duplicate rating
1. Thử thêm đánh giá cho cùng 1 sách với cùng customer_id
2. ✅ Kiểm tra: Hiển thị lỗi "Bạn đã đánh giá sách này rồi"

#### 10.3. Test empty cart checkout
1. Thử đặt hàng với giỏ hàng rỗng
2. ✅ Kiểm tra: Hiển thị lỗi "Cart is empty"

## 📊 Test Report Template

| Test Case | Expected Result | Actual Result | Status |
|-----------|----------------|---------------|--------|
| Customer Registration | Customer created + Cart auto-created | ✅ | Pass |
| Add Book to Cart | Book added to cart | ✅ | Pass |
| Create Order | Order created + Payment created | ✅ | Pass |
| Process Payment | Payment completed + Order status updated | ✅ | Pass |
| Start Shipping | Shipment created + Order status updated | ✅ | Pass |
| Complete Delivery | Order status = delivered | ✅ | Pass |
| Add Rating | Rating saved and displayed | ✅ | Pass |

## 🐛 Troubleshooting

### Lỗi: Connection refused
- **Nguyên nhân:** Service chưa khởi động hoàn tất
- **Giải pháp:** Đợi thêm 5-10 giây hoặc kiểm tra log của service

### Lỗi: Cart not found
- **Nguyên nhân:** Giỏ hàng chưa được tạo
- **Giải pháp:** Tạo giỏ hàng thủ công qua API:
```bash
curl -X POST http://localhost:8003/api/carts/ \
  -H "Content-Type: application/json" \
  -d "{\"customer_id\":1}"
```

### Lỗi: Book not found khi add to cart
- **Nguyên nhân:** Book Service không phản hồi
- **Giải pháp:** Kiểm tra Book Service có đang chạy không

## 📝 Notes

- Tất cả services sử dụng SQLite database riêng biệt
- Data sẽ bị mất khi restart services (có thể backup file .sqlite3)
- Services giao tiếp qua REST API (không sử dụng message queue)
