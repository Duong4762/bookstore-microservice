"""
Views for API Gateway - chỉ xử lý HTTP request/response và rendering
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from .services import (
    CustomerGatewayService,
    BookGatewayService,
    CartGatewayService,
    OrderGatewayService,
    PaymentGatewayService,
    ShippingGatewayService,
    RatingGatewayService
)


def home(request):
    """Trang chủ - Hiển thị danh sách sách"""
    books = BookGatewayService.get_all_books()
    if not books:
        messages.error(request, 'Không thể tải danh sách sách')
    
    return render(request, 'gateway/home.html', {'books': books})


def book_detail(request, book_id):
    """Chi tiết sách"""
    book = BookGatewayService.get_book_by_id(book_id)
    if not book:
        messages.error(request, 'Không tìm thấy sách')
        return redirect('home')
    
    # Lấy đánh giá và thống kê
    ratings = RatingGatewayService.get_ratings_by_book(book_id)
    stats = RatingGatewayService.get_book_stats(book_id)
    
    return render(request, 'gateway/book_detail.html', {
        'book': book,
        'ratings': ratings,
        'stats': stats
    })


def customers_list(request):
    """Danh sách khách hàng"""
    customers = CustomerGatewayService.get_all_customers()
    if not customers:
        messages.info(request, 'Chưa có khách hàng nào trong hệ thống')
    
    return render(request, 'gateway/customers_list.html', {'customers': customers})


def customer_create(request):
    """Tạo khách hàng mới"""
    if request.method == 'POST':
        data = {
            'email': request.POST.get('email'),
            'full_name': request.POST.get('full_name'),
            'phone_number': request.POST.get('phone_number'),
            'address': request.POST.get('address'),
        }
        
        success, customer_data, message = CustomerGatewayService.create_customer(data)
        if success:
            messages.success(request, message)
            return redirect('customers_list')
        else:
            messages.error(request, message)
    
    return render(request, 'gateway/customer_form.html')


def cart_view(request, customer_id):
    """Xem giỏ hàng"""
    cart = CartGatewayService.get_cart_by_customer(customer_id)
    if not cart:
        messages.error(request, 'Không tìm thấy giỏ hàng')
    
    return render(request, 'gateway/cart.html', {
        'cart': cart,
        'customer_id': customer_id
    })


def add_to_cart(request, book_id):
    """Thêm sách vào giỏ hàng"""
    if request.method == 'POST':
        customer_id = int(request.POST.get('customer_id'))
        quantity = int(request.POST.get('quantity', 1))
        
        success, message = CartGatewayService.add_item_to_cart(
            customer_id, book_id, quantity
        )
        
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
    
    return redirect('book_detail', book_id=book_id)


def create_order(request):
    """Tạo đơn hàng từ giỏ hàng"""
    if request.method == 'POST':
        data = {
            'customer_id': int(request.POST.get('customer_id')),
            'cart_id': int(request.POST.get('cart_id')),
            'shipping_address': request.POST.get('shipping_address'),
            'phone_number': request.POST.get('phone_number'),
            'notes': request.POST.get('notes', '')
        }
        
        success, order_data, message = OrderGatewayService.create_order(data)
        if success:
            messages.success(request, message)
            return redirect('order_detail', order_id=order_data['id'])
        else:
            messages.error(request, message)
    
    return redirect('home')


def orders_list(request):
    """Danh sách đơn hàng"""
    customer_id = request.GET.get('customer_id')
    customer_id = int(customer_id) if customer_id else None
    
    orders = OrderGatewayService.get_all_orders(customer_id=customer_id)
    if not orders:
        messages.info(request, 'Chưa có đơn hàng nào')
    
    return render(request, 'gateway/orders_list.html', {'orders': orders})


def order_detail(request, order_id):
    """Chi tiết đơn hàng"""
    order = OrderGatewayService.get_order_by_id(order_id)
    if not order:
        messages.error(request, 'Không tìm thấy đơn hàng')
        return redirect('orders_list')
    
    # Lấy thông tin payment và shipping
    payment = PaymentGatewayService.get_payment_by_order(order_id)
    shipment = ShippingGatewayService.get_shipment_by_order(order_id)
    
    return render(request, 'gateway/order_detail.html', {
        'order': order,
        'payment': payment,
        'shipment': shipment
    })


def add_rating(request, book_id):
    """Thêm đánh giá sách"""
    if request.method == 'POST':
        data = {
            'book_id': book_id,
            'customer_id': int(request.POST.get('customer_id')),
            'rating': int(request.POST.get('rating')),
            'comment': request.POST.get('comment', '')
        }
        
        success, message = RatingGatewayService.add_rating(data)
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
    
    return redirect('book_detail', book_id=book_id)
