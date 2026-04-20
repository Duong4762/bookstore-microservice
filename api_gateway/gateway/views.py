"""
Views for API Gateway - chỉ xử lý HTTP request/response và rendering
"""
import json

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .services import (
    CustomerGatewayService,
    ProductCatalogGatewayService,
    CartGatewayService,
    OrderGatewayService,
    PaymentGatewayService,
    ShippingGatewayService,
    RatingGatewayService,
    RecommendationGatewayService,
)

SESSION_CUSTOMER_KEY = 'current_customer_id'


@csrf_exempt
@require_POST
def chat_api(request):
    """Proxy JSON tới AI recommendation — chat RAG + Gemini."""
    try:
        body = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'invalid_json'}, status=400)
    message = (body.get('message') or '').strip()
    if not message:
        return JsonResponse({'error': 'message_required'}, status=400)
    customer_id = _current_customer_id(request)
    uid = body.get('user_id')
    if uid is not None:
        try:
            user_id = int(uid)
            if user_id < 1:
                user_id = None
        except (TypeError, ValueError):
            user_id = customer_id
    else:
        user_id = customer_id
    history = body.get('history') if isinstance(body.get('history'), list) else []
    clean_history = []
    for h in history[-10:]:
        if not isinstance(h, dict):
            continue
        role = h.get('role')
        content = (h.get('content') or '').strip()
        if role in ('user', 'assistant') and content:
            clean_history.append({'role': role, 'content': content[:4000]})
    ok, data, err = RecommendationGatewayService.chat(
        message=message,
        user_id=user_id,
        history=clean_history,
        include_context=bool(body.get('include_context')),
    )
    if not ok or not data:
        return JsonResponse({'error': 'upstream_error', 'detail': err}, status=502)
    return JsonResponse(data)


def _current_customer_id(request):
    raw = request.session.get(SESSION_CUSTOMER_KEY)
    return int(raw) if isinstance(raw, int) or (isinstance(raw, str) and str(raw).isdigit()) else None


def _tracking_session_id(request, customer_id: int) -> str:
    """Lấy/khởi tạo session_id ổn định cho tracking events."""
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key or f'user-{customer_id}'


def _normalize_home_category(raw_name: str) -> str:
    name = (raw_name or '').strip().lower()
    if not name:
        return 'Khác'
    if 'laptop' in name:
        return 'Laptop'
    if 'phone' in name or 'điện thoại' in name or 'dien thoai' in name:
        return 'Điện thoại'
    if 'tablet' in name or 'ipad' in name:
        return 'Tablet / iPad'
    if 'sạc' in name or 'sac' in name or 'charger' in name:
        return 'Sạc'
    if 'phụ kiện' in name or 'phu kien' in name or 'accessor' in name:
        return 'Phụ kiện'
    return raw_name.strip().title()


def home(request):
    """Trang chủ - Hiển thị danh sách sản phẩm"""
    products = ProductCatalogGatewayService.get_all_products()
    if not products:
        messages.error(request, 'Không thể tải danh sách sản phẩm')

    customer_id = _current_customer_id(request)

    recommended_products = []
    if customer_id:
        rec_ids = RecommendationGatewayService.get_recommendations(customer_id, top_k=8)
        if rec_ids:
            by_id = {p.get('id'): p for p in products if isinstance(p, dict)}
            recommended_products = [by_id[pid] for pid in rec_ids if pid in by_id]
            if not recommended_products:
                # fallback: gọi riêng từng sản phẩm nếu id không nằm trong danh sách đã tải
                for bid in rec_ids:
                    item = ProductCatalogGatewayService.get_product_by_id(bid)
                    if item:
                        recommended_products.append(item)

    grouped_products = {}
    for product in products if isinstance(products, list) else []:
        if not isinstance(product, dict):
            continue
        cat = _normalize_home_category(product.get('category_name') or '')
        grouped_products.setdefault(cat, []).append(product)

    preferred_order = ['Laptop', 'Điện thoại', 'Tablet / iPad', 'Sạc', 'Phụ kiện']
    ordered_groups = []
    for cat in preferred_order:
        if cat in grouped_products:
            ordered_groups.append((cat, grouped_products.pop(cat)))
    ordered_groups.extend(sorted(grouped_products.items(), key=lambda x: x[0]))

    return render(request, 'gateway/home.html', {
        'products': products,
        'product_groups': ordered_groups,
        'customer_id': customer_id,
        'recommended_products': recommended_products,
    })


def product_detail(request, product_id):
    """Chi tiết sản phẩm"""
    product = ProductCatalogGatewayService.get_product_by_id(product_id)
    if not product:
        messages.error(request, 'Không tìm thấy sản phẩm')
        return redirect('home')

    # Chuẩn hóa dữ liệu hiển thị từ variants (detail API trả variants thay vì price/stock trực tiếp)
    if isinstance(product, dict):
        variants = product.get('variants') or []
        active_variants = [v for v in variants if isinstance(v, dict) and v.get('is_active', True)]
        in_stock_variants = [v for v in active_variants if v.get('in_stock') or (v.get('stock') or 0) > 0]

        if in_stock_variants:
            primary_variant = in_stock_variants[0]
        elif active_variants:
            primary_variant = active_variants[0]
        else:
            primary_variant = None

        prices = []
        for v in active_variants:
            try:
                prices.append(float(v.get('price')))
            except (TypeError, ValueError):
                continue

        if prices and not product.get('min_price'):
            product['min_price'] = min(prices)

        product['stock_quantity'] = sum(int(v.get('stock') or 0) for v in active_variants)
        product['in_stock'] = bool(in_stock_variants)

        if primary_variant:
            product.setdefault('sku', primary_variant.get('sku'))
            if not product.get('cover_image_url'):
                product['cover_image_url'] = primary_variant.get('cover_image_url')
        # Chuẩn hóa danh sách biến thể để UI chọn khi thêm giỏ hàng
        selectable_variants = []
        for v in active_variants:
            if not isinstance(v, dict):
                continue
            try:
                vid = int(v.get('id'))
            except (TypeError, ValueError):
                continue
            attrs = v.get('attributes') if isinstance(v.get('attributes'), dict) else {}
            label_parts = []
            if attrs.get('color'):
                label_parts.append(f"Màu: {attrs.get('color')}")
            if attrs.get('storage'):
                label_parts.append(f"Dung lượng: {attrs.get('storage')}")
            if not label_parts and v.get('sku'):
                label_parts.append(f"SKU: {v.get('sku')}")
            selectable_variants.append(
                {
                    'id': vid,
                    'price': v.get('price'),
                    'stock': int(v.get('stock') or 0),
                    'label': ' | '.join(label_parts) if label_parts else f'Biến thể #{vid}',
                }
            )
        product['selectable_variants'] = selectable_variants
    
    # Lấy đánh giá và thống kê
    ratings = RatingGatewayService.get_ratings_by_product(product_id)
    stats = RatingGatewayService.get_product_stats(product_id)
    
    customer_id = _current_customer_id(request)
    if customer_id:
        RecommendationGatewayService.track_event(
            user_id=customer_id,
            session_id=_tracking_session_id(request, customer_id),
            event_type='product_view',
            product_id=product_id,
            quantity=1,
            source_page=request.path,
        )

    recommended_products = []
    if customer_id:
        rec_ids = RecommendationGatewayService.get_recommendations(customer_id, top_k=6)
        for bid in rec_ids:
            if bid == product_id:
                continue
            item = ProductCatalogGatewayService.get_product_by_id(bid)
            if item:
                recommended_products.append(item)
            if len(recommended_products) >= 4:
                break

    return render(request, 'gateway/book_detail.html', {
        'product': product,
        'ratings': ratings,
        'stats': stats,
        'customer_id': customer_id,
        'recommended_products': recommended_products,
    })


def customers_list(request):
    """URL /customers/ giữ tương thích; chuyển sang trang đăng nhập."""
    return redirect('customer_account_login')


def customer_account_login(request):
    """Đăng nhập bằng email đã đăng ký (lưu session; bản demo chưa có mật khẩu)."""
    if _current_customer_id(request):
        return redirect('home')
    if request.method == 'POST':
        email = (request.POST.get('email') or '').strip()
        if not email:
            messages.error(request, 'Vui lòng nhập email.')
            return redirect('customer_account_login')
        customer = CustomerGatewayService.get_customer_by_email(email)
        cid = customer.get('id') if isinstance(customer, dict) else None
        if cid is None:
            messages.error(
                request,
                'Không tìm thấy tài khoản với email này. Bạn có thể đăng ký tài khoản mới.',
            )
            return redirect('customer_account_login')
        request.session[SESSION_CUSTOMER_KEY] = int(cid)
        messages.success(request, 'Đăng nhập thành công.')
        return redirect('home')
    return render(request, 'gateway/customer_login.html')


def customer_logout(request):
    request.session.pop(SESSION_CUSTOMER_KEY, None)
    messages.info(request, 'Đã đăng xuất khách hàng hiện tại')
    return redirect('home')


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
            cid = customer_data.get('id') if isinstance(customer_data, dict) else None
            if cid is not None:
                request.session[SESSION_CUSTOMER_KEY] = int(cid)
            messages.success(request, message)
            return redirect('home')
        else:
            messages.error(request, message)
    
    return render(request, 'gateway/customer_form.html')


def cart_view(request, customer_id):
    """Xem giỏ hàng"""
    cart = CartGatewayService.get_cart_by_customer(customer_id)
    if not cart:
        messages.error(request, 'Không tìm thấy giỏ hàng')

    # Bổ sung thông tin sản phẩm từ product-service để tránh hiển thị "Unknown".
    if isinstance(cart, dict):
        items = cart.get('items', []) if isinstance(cart.get('items'), list) else []
        product_ids = []
        for item in items:
            if not isinstance(item, dict):
                continue
            pid = item.get('product_id') or item.get('book_id')
            try:
                pid_int = int(pid)
            except (TypeError, ValueError):
                continue
            if pid_int > 0:
                product_ids.append(pid_int)

        by_id = {}
        for pid in sorted(set(product_ids)):
            p = ProductCatalogGatewayService.get_product_by_id(pid)
            if isinstance(p, dict):
                by_id[pid] = p

        for item in items:
            if not isinstance(item, dict):
                continue
            pid = item.get('product_id') or item.get('book_id')
            try:
                pid_int = int(pid)
            except (TypeError, ValueError):
                pid_int = None

            def _pick_title(*candidates):
                for raw in candidates:
                    text = (str(raw).strip() if raw is not None else '')
                    if not text:
                        continue
                    if text.lower() == 'unknown':
                        continue
                    return text
                return ''

            # Fallback an toàn để template không phụ thuộc key có thể thiếu.
            fallback_title = _pick_title(item.get('book_title'), item.get('product_title'))
            item['display_name'] = fallback_title or f'Sản phẩm #{pid_int or "N/A"}'
            item['display_product_id'] = pid_int or item.get('product_id') or item.get('book_id')
            item['product_url'] = f"/products/{pid_int}/" if pid_int else '#'
            item['cover_image_url'] = None
            item['variant_display'] = ''
            product = by_id.get(pid_int) if pid_int else None
            if not product:
                continue
            item['display_name'] = _pick_title(
                product.get('name'),
                item.get('product_title'),
                item.get('book_title'),
            ) or f'Sản phẩm #{pid_int}'
            item['display_product_id'] = pid_int
            item['product_url'] = f"/products/{pid_int}/"
            cover = product.get('cover_image_url')
            if not cover:
                variants = product.get('variants') if isinstance(product.get('variants'), list) else []
                for v in variants:
                    if isinstance(v, dict) and v.get('cover_image_url'):
                        cover = v.get('cover_image_url')
                        break
            vid = item.get('variant_id')
            if vid not in (None, '', 'null'):
                try:
                    vid_int = int(vid)
                except (TypeError, ValueError):
                    vid_int = None
                if vid_int and isinstance(product.get('variants'), list):
                    for v in product.get('variants') or []:
                        if not isinstance(v, dict):
                            continue
                        try:
                            cur_vid = int(v.get('id'))
                        except (TypeError, ValueError):
                            continue
                        if cur_vid != vid_int:
                            continue
                        attrs = v.get('attributes') if isinstance(v.get('attributes'), dict) else {}
                        parts = []
                        if attrs.get('color'):
                            parts.append(f"Màu: {attrs.get('color')}")
                        if attrs.get('storage'):
                            parts.append(f"Dung lượng: {attrs.get('storage')}")
                        if not parts and v.get('sku'):
                            parts.append(f"SKU: {v.get('sku')}")
                        item['variant_display'] = ' | '.join(parts) if parts else f'Biến thể #{vid_int}'
                        break
            item['cover_image_url'] = cover

    return render(request, 'gateway/cart.html', {
        'cart': cart,
        'customer_id': customer_id
    })


def current_cart_view(request):
    customer_id = _current_customer_id(request)
    if not customer_id:
        messages.warning(request, 'Bạn chưa đăng nhập khách hàng')
        return redirect('customer_account_login')
    return redirect('cart_view', customer_id=customer_id)


def add_to_cart(request, product_id):
    """Thêm sản phẩm vào giỏ hàng"""
    if request.method == 'POST':
        customer_id = _current_customer_id(request)
        if not customer_id:
            messages.warning(request, 'Vui lòng đăng nhập khách hàng trước khi thêm vào giỏ.')
            return redirect('customer_account_login')
        quantity = int(request.POST.get('quantity', 1))
        raw_variant = request.POST.get('variant_id')
        try:
            variant_id = int(raw_variant) if raw_variant not in (None, '', 'null') else None
        except (TypeError, ValueError):
            variant_id = None
        
        success, message = CartGatewayService.add_item_to_cart(
            customer_id, product_id, quantity, variant_id=variant_id
        )
        
        if success:
            # Track hành vi thêm vào giỏ để AI recommendation học online.
            RecommendationGatewayService.track_event(
                user_id=customer_id,
                session_id=_tracking_session_id(request, customer_id),
                event_type='add_to_cart',
                product_id=product_id,
                quantity=quantity,
                source_page=request.path,
            )
            if variant_id:
                messages.success(request, f'{message} (biến thể #{variant_id})')
            else:
                messages.success(request, message)
        else:
            messages.error(request, message)
    
    return redirect('product_detail', product_id=product_id)


def create_order(request):
    """Tạo đơn hàng từ giỏ hàng"""
    if request.method == 'POST':
        customer_id = _current_customer_id(request)
        if not customer_id:
            messages.warning(request, 'Vui lòng đăng nhập khách hàng trước khi đặt hàng.')
            return redirect('customer_account_login')
        data = {
            'customer_id': customer_id,
            'cart_id': int(request.POST.get('cart_id')),
            'shipping_address': request.POST.get('shipping_address'),
            'phone_number': request.POST.get('phone_number'),
            'notes': request.POST.get('notes', '')
        }
        cart = CartGatewayService.get_cart_by_customer(customer_id) or {}
        purchase_items = cart.get('items', []) if isinstance(cart, dict) else []
        
        success, order_data, message = OrderGatewayService.create_order(data)
        if success:
            session_id = _tracking_session_id(request, customer_id)
            for item in purchase_items:
                pid = item.get('book_id') or item.get('product_id')
                if not pid:
                    continue
                RecommendationGatewayService.track_event(
                    user_id=customer_id,
                    session_id=session_id,
                    event_type='purchase',
                    product_id=int(pid),
                    quantity=int(item.get('quantity') or 1),
                    source_page=request.path,
                )
            messages.success(request, message)
            return redirect('order_detail', order_id=order_data['id'])
        else:
            messages.error(request, message)
    
    return redirect('home')


def orders_list(request):
    """Danh sách đơn hàng"""
    customer_id = _current_customer_id(request)
    if not customer_id:
        messages.warning(request, 'Vui lòng đăng nhập khách hàng để xem đơn hàng của bạn.')
        return redirect('customer_account_login')
    
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
    customer = None
    if isinstance(order, dict) and order.get('customer_id'):
        customer = CustomerGatewayService.get_customer_by_id(int(order.get('customer_id')))
    
    return render(request, 'gateway/order_detail.html', {
        'order': order,
        'payment': payment,
        'shipment': shipment,
        'customer': customer,
    })


def add_rating(request, product_id):
    """Thêm đánh giá sản phẩm"""
    if request.method == 'POST':
        customer_id = _current_customer_id(request)
        if not customer_id:
            messages.warning(request, 'Vui lòng đăng nhập khách hàng trước khi đánh giá.')
            return redirect('customer_account_login')
        data = {
            'book_id': product_id,
            'customer_id': customer_id,
            'rating': int(request.POST.get('rating')),
            'comment': request.POST.get('comment', '')
        }
        
        success, message = RatingGatewayService.add_rating(data)
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
    
    return redirect('product_detail', product_id=product_id)


def book_detail(request, book_id):
    """Backward compatible alias."""
    return product_detail(request, book_id)
