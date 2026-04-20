"""
Giao diện nhân viên: đăng nhập (không đăng ký) và quản lý sản phẩm.
"""
from __future__ import annotations

import json
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
            messages.warning(request, 'Vui lòng đăng nhập nhân viên.')
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
            messages.success(request, 'Đăng nhập nhân viên thành công.')
            return redirect('staff_product_list')
        messages.error(request, 'Tên đăng nhập hoặc mật khẩu không đúng.')
    return render(request, 'gateway/staff/login.html')


def staff_logout(request):
    request.session.pop(SESSION_STAFF_KEY, None)
    messages.info(request, 'Đã đăng xuất khu vực nhân viên.')
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


def _product_type_attr_map(product_types: list[dict]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for pt in product_types or []:
        pid = pt.get('id') if isinstance(pt, dict) else None
        if pid is None:
            continue
        required = pt.get('required_attributes') if isinstance(pt, dict) else None
        if not isinstance(required, list):
            required = []
        cleaned = [str(x).strip() for x in required if str(x).strip()]
        out[str(pid)] = cleaned
    return out


def _build_attribute_rows_for_type(
    *,
    type_id: int | str | None,
    attr_map: dict[str, list[str]],
    attributes: dict | None,
) -> list[dict]:
    base_attrs = attributes if isinstance(attributes, dict) else {}
    type_keys = attr_map.get(str(type_id or ''), [])
    if type_keys:
        keys = list(dict.fromkeys([str(k).strip() for k in type_keys if str(k).strip()]))
    else:
        keys = [str(k).strip() for k in base_attrs.keys() if str(k).strip()]
    lowered_remove = {k.lower() for k in (*_COLOR_KEYS, *_STORAGE_KEYS)}
    keys = [k for k in keys if k.lower() not in lowered_remove]
    rows: list[dict] = []
    for key in keys:
        rows.append({'key': key, 'value': '' if base_attrs.get(key) is None else str(base_attrs.get(key))})
    return rows


_COLOR_KEYS = ('color', 'mau_sac', 'mau')
_STORAGE_KEYS = ('storage', 'dung_luong')


def _first_attr(attrs: dict | None, candidates: tuple[str, ...]) -> str:
    if not isinstance(attrs, dict):
        return ''
    for k in candidates:
        v = attrs.get(k)
        if v not in (None, ''):
            return str(v)
    return ''


def _has_variant_dimension(attributes: dict | None) -> bool:
    if not isinstance(attributes, dict):
        return False
    return bool(_first_attr(attributes, _COLOR_KEYS) or _first_attr(attributes, _STORAGE_KEYS))


def _build_variants_for_edit(variants: list[dict]) -> list[dict]:
    out: list[dict] = []
    for v in variants or []:
        if not isinstance(v, dict):
            continue
        attrs = v.get('attributes') if isinstance(v.get('attributes'), dict) else {}
        out.append(
            {
                'id': v.get('id'),
                'sku': v.get('sku') or '',
                'price': v.get('price') or '0',
                'stock': int(v.get('stock') or 0),
                'is_active': bool(v.get('is_active', True)),
                'cover_image_url': v.get('cover_image_url') or '',
                'color': _first_attr(attrs, _COLOR_KEYS),
                'storage': _first_attr(attrs, _STORAGE_KEYS),
            }
        )
    return out


def _parse_bool(val) -> bool:
    if val is True:
        return True
    if val is False or val is None:
        return False
    s = str(val).strip().lower()
    return s in ('1', 'true', 'yes', 'on')


def _attributes_to_rows(attributes) -> list[dict]:
    if not isinstance(attributes, dict):
        return []
    rows: list[dict] = []
    for k, v in attributes.items():
        key = str(k).strip()
        if not key:
            continue
        rows.append({'key': key, 'value': '' if v is None else str(v)})
    return rows


def _parse_attributes_from_form(request) -> tuple[dict, str | None]:
    keys = request.POST.getlist('attribute_key[]')
    values = request.POST.getlist('attribute_value[]')
    if not keys and not values:
        # fallback tương thích với phiên bản cũ dùng JSON textarea
        legacy_text = (request.POST.get('attributes_json') or '').strip()
        if not legacy_text:
            return {}, None
        try:
            data = json.loads(legacy_text)
            if isinstance(data, dict):
                out: dict = {}
                for k, v in data.items():
                    kk = str(k).strip()
                    if not kk:
                        continue
                    out[kk] = '' if v is None else str(v)
                return out, None
        except json.JSONDecodeError:
            pass
        return {}, 'Thuộc tính không hợp lệ. Vui lòng nhập theo cặp key/value.'

    out: dict = {}
    max_len = max(len(keys), len(values))
    for i in range(max_len):
        k = (keys[i] if i < len(keys) else '').strip()
        v = (values[i] if i < len(values) else '').strip()
        if not k and not v:
            continue
        if not k:
            return {}, 'Thuộc tính không hợp lệ: thiếu key ở một dòng.'
        out[k] = v
    return out, None


def _strip_variant_dimensions_from_product_attributes(attributes: dict | None) -> dict:
    if not isinstance(attributes, dict):
        return {}
    lowered_remove = {k.lower() for k in (*_COLOR_KEYS, *_STORAGE_KEYS)}
    out: dict = {}
    for k, v in attributes.items():
        key = str(k).strip()
        if not key:
            continue
        if key.lower() in lowered_remove:
            continue
        out[key] = v
    return out


@staff_required
def staff_product_create(request):
    ctx = _catalog_choices()
    type_attr_map = _product_type_attr_map(ctx.get('product_types') or [])
    default_type_id = str((ctx.get('product_types') or [{}])[0].get('id') or '')
    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        slug = (request.POST.get('slug') or '').strip()
        if not slug and name:
            slug = slugify(name)
        description = (request.POST.get('description') or '').strip()
        attributes, attr_err = _parse_attributes_from_form(request)
        attributes = _strip_variant_dimensions_from_product_attributes(attributes)
        if attr_err:
            messages.error(request, attr_err)
            return render(
                request,
                'gateway/staff/product_form.html',
                {
                    **ctx,
                    'mode': 'create',
                    'selected_product_type_id': str(request.POST.get('product_type_id') or default_type_id),
                    'product_type_attr_map': type_attr_map,
                    'attribute_rows': [
                        {'key': (k or '').strip(), 'value': (v or '').strip()}
                        for k, v in zip(
                            request.POST.getlist('attribute_key[]'),
                            request.POST.getlist('attribute_value[]'),
                        )
                    ],
                },
            )
        try:
            category_id = int(request.POST.get('category_id') or 0)
            brand_id = int(request.POST.get('brand_id') or 0)
            product_type_id = int(request.POST.get('product_type_id') or 0)
        except ValueError:
            messages.error(request, 'Danh mục / thương hiệu / loại sản phẩm không hợp lệ.')
            return render(
                request,
                'gateway/staff/product_form.html',
                {
                    **ctx,
                    'mode': 'create',
                    'selected_product_type_id': str(request.POST.get('product_type_id') or default_type_id),
                    'product_type_attr_map': type_attr_map,
                    'attribute_rows': _build_attribute_rows_for_type(
                        type_id=request.POST.get('product_type_id') or default_type_id,
                        attr_map=type_attr_map,
                        attributes=attributes,
                    ),
                },
            )
        is_active = _parse_bool(request.POST.get('is_active'))
        payload = {
            'name': name,
            'slug': slug,
            'description': description,
            'category_id': category_id,
            'brand_id': brand_id,
            'product_type_id': product_type_id,
            'attributes': attributes,
            'is_active': is_active,
        }
        ok, product, msg = ProductGatewayService.create_product(payload)
        if not ok or not product:
            messages.error(request, msg)
            return render(
                request,
                'gateway/staff/product_form.html',
                {
                    **ctx,
                    'mode': 'create',
                    'selected_product_type_id': str(product_type_id),
                    'product_type_attr_map': type_attr_map,
                    'attribute_rows': _build_attribute_rows_for_type(
                        type_id=product_type_id,
                        attr_map=type_attr_map,
                        attributes=attributes,
                    ),
                },
            )
        pid = int(product.get('id'))
        messages.success(request, 'Đã tạo sản phẩm. Bạn có thể thêm các biến thể bên dưới.')
        return redirect('staff_product_edit', product_id=pid)
    return render(
        request,
        'gateway/staff/product_form.html',
        {
            **ctx,
            'mode': 'create',
            'selected_product_type_id': default_type_id,
            'product_type_attr_map': type_attr_map,
            'attribute_rows': _build_attribute_rows_for_type(
                type_id=default_type_id,
                attr_map=type_attr_map,
                attributes={},
            ),
        },
    )


@staff_required
def staff_product_edit(request, product_id: int):
    ctx = _catalog_choices()
    type_attr_map = _product_type_attr_map(ctx.get('product_types') or [])
    product = ProductGatewayService.get_product_by_id(product_id)
    if not product:
        messages.error(request, 'Không tìm thấy sản phẩm.')
        return redirect('staff_product_list')
    variants = product.get('variants') or []
    can_manage_variants = True
    variants_for_edit = _build_variants_for_edit(variants)
    if request.method == 'POST':
        action = (request.POST.get('action') or 'save_main').strip()

        if action == 'add_variant':
            if not can_manage_variants:
                messages.error(request, 'Sản phẩm chưa có thuộc tính màu sắc hoặc dung lượng để tạo biến thể.')
                return redirect('staff_product_edit', product_id=product_id)

            color = (request.POST.get('variant_color') or '').strip()
            storage = (request.POST.get('variant_storage') or '').strip()
            sku = (request.POST.get('variant_sku') or '').strip()
            cover = (request.POST.get('variant_cover_image_url') or '').strip() or None
            try:
                price = Decimal(str(request.POST.get('variant_price') or '0'))
            except InvalidOperation:
                price = Decimal('0')
            try:
                stock = int(request.POST.get('variant_stock') or 0)
            except ValueError:
                stock = 0
            if not sku:
                messages.error(request, 'Vui lòng nhập SKU cho biến thể.')
                return redirect('staff_product_edit', product_id=product_id)
            if not color and not storage:
                messages.error(request, 'Vui lòng nhập màu sắc hoặc dung lượng cho biến thể.')
                return redirect('staff_product_edit', product_id=product_id)

            variant_attrs: dict[str, str] = {}
            if color:
                variant_attrs['color'] = color
            if storage:
                variant_attrs['storage'] = storage

            v_ok, _, v_msg = ProductGatewayService.create_variant(
                product_id,
                {
                    'sku': sku,
                    'price': str(price),
                    'stock': stock,
                    'attributes': variant_attrs,
                    'cover_image_url': cover,
                    'is_active': True,
                },
            )
            if v_ok:
                messages.success(request, 'Đã thêm biến thể.')
            else:
                messages.error(request, v_msg)
            return redirect('staff_product_edit', product_id=product_id)

        if action == 'update_variant':
            if not can_manage_variants:
                messages.error(request, 'Sản phẩm không cho phép cập nhật biến thể.')
                return redirect('staff_product_edit', product_id=product_id)
            try:
                variant_id = int(request.POST.get('variant_id') or 0)
            except ValueError:
                variant_id = 0
            target = None
            for v in variants or []:
                if isinstance(v, dict) and int(v.get('id') or 0) == variant_id:
                    target = v
                    break
            if not target:
                messages.error(request, 'Không tìm thấy biến thể cần cập nhật.')
                return redirect('staff_product_edit', product_id=product_id)

            color = (request.POST.get('variant_color') or '').strip()
            storage = (request.POST.get('variant_storage') or '').strip()
            sku = (request.POST.get('variant_sku') or '').strip() or (target.get('sku') or '')
            cover = (request.POST.get('variant_cover_image_url') or '').strip() or None
            try:
                price = Decimal(str(request.POST.get('variant_price') or target.get('price') or '0'))
            except InvalidOperation:
                price = Decimal(str(target.get('price') or '0'))
            try:
                stock = int(request.POST.get('variant_stock') or target.get('stock') or 0)
            except ValueError:
                stock = int(target.get('stock') or 0)
            is_active = _parse_bool(request.POST.get('variant_is_active'))
            if not sku:
                messages.error(request, 'SKU biến thể không hợp lệ.')
                return redirect('staff_product_edit', product_id=product_id)
            attrs = target.get('attributes') if isinstance(target.get('attributes'), dict) else {}
            attrs = dict(attrs)
            attrs['color'] = color
            attrs['storage'] = storage
            v_ok, _, v_msg = ProductGatewayService.update_variant(
                product_id,
                variant_id,
                {
                    'sku': sku,
                    'price': str(price),
                    'stock': stock,
                    'attributes': attrs,
                    'cover_image_url': cover,
                    'is_active': is_active,
                },
            )
            if v_ok:
                messages.success(request, 'Đã cập nhật biến thể.')
            else:
                messages.error(request, v_msg)
            return redirect('staff_product_edit', product_id=product_id)

        name = (request.POST.get('name') or '').strip()
        slug = (request.POST.get('slug') or '').strip()
        if not slug and name:
            slug = slugify(name)
        description = (request.POST.get('description') or product.get('description') or '').strip()
        attributes, attr_err = _parse_attributes_from_form(request)
        attributes = _strip_variant_dimensions_from_product_attributes(attributes)
        if attr_err:
            messages.error(request, attr_err)
            return render(
                request,
                'gateway/staff/product_form.html',
                {
                    **ctx,
                    'product': product,
                    'mode': 'edit',
                    'selected_product_type_id': str(request.POST.get('product_type_id') or product.get('product_type_id') or ''),
                    'product_type_attr_map': type_attr_map,
                    'attribute_rows': [
                        {'key': (k or '').strip(), 'value': (v or '').strip()}
                        for k, v in zip(
                            request.POST.getlist('attribute_key[]'),
                            request.POST.getlist('attribute_value[]'),
                        )
                    ],
                },
            )
        try:
            category_id = int(request.POST.get('category_id') or 0)
            brand_id = int(request.POST.get('brand_id') or 0)
            product_type_id = int(request.POST.get('product_type_id') or 0)
        except ValueError:
            messages.error(request, 'Danh mục / thương hiệu / loại sản phẩm không hợp lệ.')
            return render(
                request,
                'gateway/staff/product_form.html',
                {
                    **ctx,
                    'product': product,
                    'mode': 'edit',
                    'selected_product_type_id': str(request.POST.get('product_type_id') or product.get('product_type_id') or ''),
                    'product_type_attr_map': type_attr_map,
                    'attribute_rows': _build_attribute_rows_for_type(
                        type_id=request.POST.get('product_type_id') or product.get('product_type_id') or '',
                        attr_map=type_attr_map,
                        attributes=attributes,
                    ),
                },
            )
        is_active = _parse_bool(request.POST.get('is_active'))
        payload = {
            'name': name,
            'slug': slug,
            'description': description,
            'category_id': category_id,
            'brand_id': brand_id,
            'product_type_id': product_type_id,
            'attributes': attributes,
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
                {
                    **ctx,
                    'product': product,
                    'mode': 'edit',
                    'selected_product_type_id': str(product_type_id),
                    'product_type_attr_map': type_attr_map,
                    'attribute_rows': _build_attribute_rows_for_type(
                        type_id=product_type_id,
                        attr_map=type_attr_map,
                        attributes=attributes,
                    ),
                },
            )
        messages.success(request, msg)
        return redirect('staff_product_edit', product_id=product_id)
    product = ProductGatewayService.get_product_by_id(product_id) or product
    variants = product.get('variants') or []
    return render(
        request,
        'gateway/staff/product_form.html',
        {
            **ctx,
            'product': product,
            'mode': 'edit',
            'selected_product_type_id': str(product.get('product_type_id') or ''),
            'product_type_attr_map': type_attr_map,
            'attribute_rows': _build_attribute_rows_for_type(
                type_id=product.get('product_type_id') or '',
                attr_map=type_attr_map,
                attributes=_strip_variant_dimensions_from_product_attributes(product.get('attributes') or {}),
            ),
            'can_manage_variants': can_manage_variants,
            'variants_for_edit': variants_for_edit,
        },
    )


@staff_required
def staff_product_delete(request, product_id: int):
    product = ProductGatewayService.get_product_by_id(product_id)
    if not product:
        messages.error(request, 'Không tìm thấy sản phẩm.')
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
