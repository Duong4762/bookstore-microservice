"""
Giao dien nhan vien: dang nhap (khong dang ky) va quan ly san pham.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils.text import slugify

from .services import (
    SESSION_STAFF_KEY,
    ProductGatewayService,
    StaffAuthService,
)


def _staff_logged_in(request) -> bool:
    return bool(request.session.get(SESSION_STAFF_KEY))


def staff_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not _staff_logged_in(request):
            messages.warning(request, 'Vui long dang nhap nhan vien.')
            return redirect('staff_login')
        return view_func(request, *args, **kwargs)

    return _wrapped


def staff_login(request):
    if _staff_logged_in(request):
        return redirect('staff_product_list')
    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip()
        password = request.POST.get('password') or ''
        if StaffAuthService.verify(username, password):
            request.session[SESSION_STAFF_KEY] = True
            messages.success(request, 'Dang nhap nhan vien thanh cong.')
            return redirect('staff_product_list')
        messages.error(request, 'Ten dang nhap hoac mat khau khong dung.')
    return render(request, 'gateway/staff/login.html')


def staff_logout(request):
    request.session.pop(SESSION_STAFF_KEY, None)
    messages.info(request, 'Da dang xuat khu vuc nhan vien.')
    return redirect('staff_login')


@staff_required
def staff_product_list(request):
    q = (request.GET.get('q') or '').strip()
    products = ProductGatewayService.list_products_for_staff(search=q or None)
    return render(
        request,
        'gateway/staff/product_list.html',
        {'products': products, 'search_q': q},
    )


def _catalog_choices():
    return {
        'categories': ProductGatewayService.list_categories_flat(),
        'brands': ProductGatewayService.list_brands(),
        'product_types': ProductGatewayService.list_product_types(),
    }


def _parse_bool(val) -> bool:
    if val is True:
        return True
    if val is False or val is None:
        return False
    s = str(val).strip().lower()
    return s in ('1', 'true', 'yes', 'on')


@staff_required
def staff_product_create(request):
    ctx = _catalog_choices()
    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        slug = (request.POST.get('slug') or '').strip()
        if not slug and name:
            slug = slugify(name)
        description = (request.POST.get('description') or '').strip()
        try:
            category_id = int(request.POST.get('category_id') or 0)
            brand_id = int(request.POST.get('brand_id') or 0)
            product_type_id = int(request.POST.get('product_type_id') or 0)
        except ValueError:
            messages.error(request, 'Danh muc / thuong hieu / loai san pham khong hop le.')
            return render(request, 'gateway/staff/product_form.html', {**ctx, 'mode': 'create'})
        is_active = _parse_bool(request.POST.get('is_active'))
        payload = {
            'name': name,
            'slug': slug,
            'description': description,
            'category_id': category_id,
            'brand_id': brand_id,
            'product_type_id': product_type_id,
            'attributes': {},
            'is_active': is_active,
        }
        ok, product, msg = ProductGatewayService.create_product(payload)
        if not ok or not product:
            messages.error(request, msg)
            return render(request, 'gateway/staff/product_form.html', {**ctx, 'mode': 'create'})
        pid = product.get('id')
        sku = (request.POST.get('sku') or '').strip() or f'SKU-{pid}'
        try:
            price = Decimal(str(request.POST.get('price') or '0'))
        except InvalidOperation:
            price = Decimal('0')
        try:
            stock = int(request.POST.get('stock') or 0)
        except ValueError:
            stock = 0
        cover = (request.POST.get('cover_image_url') or '').strip() or None
        v_ok, _, v_msg = ProductGatewayService.create_variant(
            int(pid),
            {
                'sku': sku,
                'price': str(price),
                'stock': stock,
                'cover_image_url': cover,
                'is_active': True,
            },
        )
        if v_ok:
            messages.success(request, msg)
            return redirect('staff_product_edit', product_id=int(pid))
        messages.error(request, v_msg)
        return redirect('staff_product_edit', product_id=int(pid))
    return render(request, 'gateway/staff/product_form.html', {**ctx, 'mode': 'create'})


@staff_required
def staff_product_edit(request, product_id: int):
    ctx = _catalog_choices()
    product = ProductGatewayService.get_product_by_id(product_id)
    if not product:
        messages.error(request, 'Khong tim thay san pham.')
        return redirect('staff_product_list')
    variants = product.get('variants') or []
    primary = variants[0] if variants else None
    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        slug = (request.POST.get('slug') or '').strip()
        if not slug and name:
            slug = slugify(name)
        description = (request.POST.get('description') or '').strip()
        try:
            category_id = int(request.POST.get('category_id') or 0)
            brand_id = int(request.POST.get('brand_id') or 0)
            product_type_id = int(request.POST.get('product_type_id') or 0)
        except ValueError:
            messages.error(request, 'Danh muc / thuong hieu / loai san pham khong hop le.')
            return render(
                request,
                'gateway/staff/product_form.html',
                {**ctx, 'product': product, 'primary_variant': primary, 'mode': 'edit'},
            )
        is_active = _parse_bool(request.POST.get('is_active'))
        payload = {
            'name': name,
            'slug': slug,
            'description': description,
            'category_id': category_id,
            'brand_id': brand_id,
            'product_type_id': product_type_id,
            'is_active': is_active,
        }
        ok, product, msg = ProductGatewayService.update_product(product_id, payload)
        if not ok:
            messages.error(request, msg)
            product = ProductGatewayService.get_product_by_id(product_id)
            variants = (product or {}).get('variants') or []
            primary = variants[0] if variants else None
            return render(
                request,
                'gateway/staff/product_form.html',
                {**ctx, 'product': product, 'primary_variant': primary, 'mode': 'edit'},
            )
        sku = (request.POST.get('sku') or '').strip()
        try:
            price = Decimal(str(request.POST.get('price') or '0'))
        except InvalidOperation:
            price = Decimal('0')
        try:
            stock = int(request.POST.get('stock') or 0)
        except ValueError:
            stock = 0
        cover = (request.POST.get('cover_image_url') or '').strip() or None
        v_payload = {
            'sku': sku or None,
            'price': str(price),
            'stock': stock,
            'cover_image_url': cover,
            'is_active': _parse_bool(request.POST.get('variant_is_active')),
        }
        if primary and primary.get('id'):
            v_ok, _, v_msg = ProductGatewayService.update_variant(
                product_id, int(primary['id']), v_payload
            )
        else:
            v_payload['sku'] = sku or f'SKU-{product_id}'
            v_ok, _, v_msg = ProductGatewayService.create_variant(product_id, v_payload)
        if v_ok:
            messages.success(request, msg)
            return redirect('staff_product_edit', product_id=product_id)
        messages.error(request, v_msg)
    product = ProductGatewayService.get_product_by_id(product_id) or product
    variants = product.get('variants') or []
    primary = variants[0] if variants else None
    return render(
        request,
        'gateway/staff/product_form.html',
        {
            **ctx,
            'product': product,
            'primary_variant': primary,
            'mode': 'edit',
        },
    )


@staff_required
def staff_product_delete(request, product_id: int):
    product = ProductGatewayService.get_product_by_id(product_id)
    if not product:
        messages.error(request, 'Khong tim thay san pham.')
        return redirect('staff_product_list')
    if request.method == 'POST':
        ok, msg = ProductGatewayService.delete_product(product_id)
        if ok:
            messages.success(request, msg)
        else:
            messages.error(request, msg)
        return redirect('staff_product_list')
    return render(
        request,
        'gateway/staff/product_confirm_delete.html',
        {'product': product},
    )
