"""RAG chat service for product recommendation and lookup."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional

import requests
from django.conf import settings

from catalog_proxy.client import get_products_bulk, list_products

from .cold_start import popular_product_ids
from .inference import RecommendEngine

logger = logging.getLogger(__name__)

GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
_PRICE_RE = re.compile(r'(\d[\d\.,]*)\s*(k|nghìn|ngan|triệu|trieu|m|đ|vnd)?', re.IGNORECASE)
_DETAIL_HINT_RE = re.compile(r'(gioi thieu|giới thiệu|chi tiet|chi tiết|thong tin|thông tin|mo ta|mô tả)', re.IGNORECASE)


@dataclass
class ChatRetrieval:
    products: List[Dict[str, Any]]
    product_ids: List[int]
    source: str
    cf_reason_lines: List[str]


def _detect_intent(message: str) -> str:
    text = (message or '').strip().lower()
    if _DETAIL_HINT_RE.search(text):
        return 'product_detail'
    if any(k in text for k in ['goi y', 'gợi ý', 'de xuat', 'đề xuất', 'recommend']):
        return 'recommendation'
    if any(k in text for k in ['loc', 'lọc', 'duoi', 'dưới', 'tren', 'trên', 'gia', 'giá']):
        return 'filter'
    return 'general'


def _to_number(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(Decimal(str(value)))
    except Exception:
        return None


def _extract_price_bounds(message: str) -> tuple[Optional[int], Optional[int]]:
    matches = _PRICE_RE.findall(message or '')
    if not matches:
        return None, None

    values: List[int] = []
    for raw, unit in matches:
        cleaned = raw.replace('.', '').replace(',', '')
        if not cleaned.isdigit():
            continue
        val = int(cleaned)
        u = (unit or '').lower()
        if u in ('k', 'nghìn', 'ngan'):
            val *= 1_000
        elif u in ('triệu', 'trieu', 'm'):
            val *= 1_000_000
        values.append(val)
    if not values:
        return None, None
    if len(values) == 1:
        return None, values[0]
    return min(values), max(values)


def _variant_prices(product: Dict[str, Any]) -> List[int]:
    out: List[int] = []
    for v in (product.get('variants') or []):
        if not isinstance(v, dict):
            continue
        price = _to_number(v.get('price'))
        if price is not None:
            out.append(price)
    min_price = _to_number(product.get('min_price'))
    if min_price is not None:
        out.append(min_price)
    return out


def _is_in_price_range(product: Dict[str, Any], lo: Optional[int], hi: Optional[int]) -> bool:
    if lo is None and hi is None:
        return True
    prices = _variant_prices(product)
    if not prices:
        return True
    pmin = min(prices)
    pmax = max(prices)
    if lo is not None and pmax < lo:
        return False
    if hi is not None and pmin > hi:
        return False
    return True


def _neo4j_query(cypher: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    url = f"{settings.NEO4J_HTTP_URL.rstrip('/')}/db/neo4j/tx/commit"
    payload = {
        'statements': [
            {
                'statement': cypher,
                'parameters': params,
            }
        ]
    }
    try:
        resp = requests.post(
            url,
            json=payload,
            auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
            timeout=2.0,
        )
        resp.raise_for_status()
        body = resp.json()
        if body.get('errors'):
            logger.debug('Neo4j query errors: %s', body.get('errors'))
            return []
        results = body.get('results') or []
        if not results:
            return []
        cols = results[0].get('columns') or []
        rows = results[0].get('data') or []
        out: List[Dict[str, Any]] = []
        for row in rows:
            vals = row.get('row') or []
            out.append({cols[i]: vals[i] for i in range(min(len(cols), len(vals)))})
        return out
    except Exception as exc:
        logger.debug('Neo4j query failed: %s', exc)
        return []


def _neo4j_related_product_ids(message: str, user_id: Optional[int], limit: int = 15) -> List[int]:
    query = (message or '').strip().lower()
    if user_id:
        rows = _neo4j_query(
            """
            MATCH (u:User {user_id: $user_id})-[r:INTERACTED]->(p:Product)
            WITH p, SUM(coalesce(r.count, 1)) AS score
            ORDER BY score DESC
            LIMIT $limit
            RETURN p.product_id AS product_id
            """,
            {'user_id': int(user_id), 'limit': int(limit)},
        )
        ids = [int(r['product_id']) for r in rows if r.get('product_id') is not None]
        if ids:
            return ids

    kw = [tok for tok in re.split(r'[^a-zA-Z0-9]+', query) if len(tok) >= 2][:8]
    if not kw:
        return []
    rows = _neo4j_query(
        """
        MATCH (u:User)-[r:INTERACTED]->(p:Product)
        WHERE r.action IN ['view', 'click', 'add_to_cart']
        WITH p, collect(toLower(r.action)) AS acts, SUM(coalesce(r.count, 1)) AS score
        WHERE ANY(a IN acts WHERE ANY(k IN $kw WHERE a CONTAINS k))
        RETURN p.product_id AS product_id
        ORDER BY score DESC
        LIMIT $limit
        """,
        {'kw': kw, 'limit': int(limit)},
    )
    return [int(r['product_id']) for r in rows if r.get('product_id') is not None]


def _neo4j_user_based_recommendations(user_id: Optional[int], limit: int = 10) -> tuple[List[int], List[str]]:
    """Collaborative filtering from Neo4j:
    users with overlapping interactions -> products they interacted that current user has not.
    """
    if not user_id:
        return [], []
    rows = _neo4j_query(
        """
        MATCH (u:User {user_id: $user_id})-[:INTERACTED]->(p:Product)
        WITH u, collect(DISTINCT p) AS my_products
        MATCH (other:User)-[r:INTERACTED]->(p2:Product)
        WHERE other <> u
          AND ANY(mp IN my_products WHERE mp = p2)
        WITH u, other, my_products, SUM(coalesce(r.count, 1)) AS overlap_score
        ORDER BY overlap_score DESC
        LIMIT 30
        MATCH (other)-[r2:INTERACTED]->(cand:Product)
        WHERE NOT cand IN my_products
        WITH cand, collect(DISTINCT other.user_id)[0..3] AS by_users, SUM(coalesce(r2.count, 1)) AS score
        ORDER BY score DESC
        LIMIT $limit
        RETURN cand.product_id AS product_id, by_users
        """,
        {'user_id': int(user_id), 'limit': int(limit)},
    )
    ids: List[int] = []
    reasons: List[str] = []
    for row in rows:
        pid = row.get('product_id')
        if pid is None:
            continue
        pid_int = int(pid)
        ids.append(pid_int)
        users = row.get('by_users') or []
        if isinstance(users, list) and users:
            users_text = ', '.join([f'#{int(u)}' for u in users[:3]])
            reasons.append(
                f'Người dùng tương tự ({users_text}) từng tương tác thêm sản phẩm #{pid_int}.'
            )
    return ids, reasons


def _retrieve_products(message: str, user_id: Optional[int], top_k: int = 8) -> ChatRetrieval:
    query = (message or '').strip()
    keyword_candidates = list_products(search=query, in_stock=True, limit=25)
    kg_ids = _neo4j_related_product_ids(message=query, user_id=user_id, limit=20)
    cf_ids, cf_reason_lines = _neo4j_user_based_recommendations(user_id=user_id, limit=12)

    rec_ids: List[int] = []
    source_parts = ['search']
    if user_id:
        try:
            rec_ids, rec_source, _ = RecommendEngine.instance().recommend(user_id, top_k=top_k)
            source_parts.append(rec_source)
        except Exception:
            logger.exception('chat retrieval recommend() failed')
    if not rec_ids:
        rec_ids = popular_product_ids(top_k * 2)
        source_parts.append('popular_fallback')

    kg_map = get_products_bulk(kg_ids)
    kg_products = [kg_map[pid] for pid in kg_ids if pid in kg_map]
    cf_map = get_products_bulk(cf_ids)
    cf_products = [cf_map[pid] for pid in cf_ids if pid in cf_map]

    rec_map = get_products_bulk(rec_ids)
    rec_products = [rec_map[pid] for pid in rec_ids if pid in rec_map]

    merged: List[Dict[str, Any]] = []
    seen: set[int] = set()
    for item in keyword_candidates + cf_products + kg_products + rec_products:
        if not isinstance(item, dict):
            continue
        pid = _to_number(item.get('id'))
        if not pid or pid in seen:
            continue
        seen.add(pid)
        merged.append(item)
        if len(merged) >= 30:
            break

    lo, hi = _extract_price_bounds(query)
    filtered = [p for p in merged if _is_in_price_range(p, lo, hi)]
    if filtered:
        merged = filtered

    out_ids = [_to_number(p.get('id')) for p in merged]
    out_ids = [pid for pid in out_ids if pid is not None][:20]
    if kg_products:
        source_parts.append('neo4j')
    if cf_products:
        source_parts.append('collab_users')
    return ChatRetrieval(
        products=merged[:20],
        product_ids=out_ids,
        source='+'.join(source_parts),
        cf_reason_lines=cf_reason_lines[:5],
    )


def _retrieve_detail_product(message: str, user_id: Optional[int]) -> ChatRetrieval:
    query = (message or '').strip()
    # Ưu tiên kết quả search theo tên cụ thể user hỏi.
    rows = list_products(search=query, in_stock=None, limit=10)
    chosen: List[Dict[str, Any]] = []
    if rows:
        chosen = [rows[0]]
    else:
        # fallback: lấy từ recommend để vẫn có câu trả lời.
        rec_ids, _, _ = RecommendEngine.instance().recommend(user_id, top_k=5) if user_id else ([], '', 0.0)
        rec_map = get_products_bulk(rec_ids)
        chosen = [rec_map[pid] for pid in rec_ids if pid in rec_map][:1]
    ids = [_to_number(p.get('id')) for p in chosen if isinstance(p, dict)]
    ids = [x for x in ids if x is not None]
    return ChatRetrieval(products=chosen[:1], product_ids=ids[:1], source='detail_lookup', cf_reason_lines=[])


def _build_context(products: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for idx, p in enumerate(products, start=1):
        pid = p.get('id')
        name = p.get('name') or 'N/A'
        cat = p.get('category_name') or ''
        brand = p.get('brand_name') or ''
        desc = (p.get('description') or '').strip()
        if len(desc) > 260:
            desc = desc[:260] + '...'
        prices = _variant_prices(p)
        price_text = ''
        if prices:
            price_text = f", gia={min(prices)}-{max(prices)}"
        attrs = p.get('attributes') if isinstance(p.get('attributes'), dict) else {}
        attrs_text = ', '.join([f'{k}:{v}' for k, v in list(attrs.items())[:6]])
        lines.append(
            f"{idx}. id={pid}, ten={name}, danh_muc={cat}, hang={brand}{price_text}, attrs=[{attrs_text}], mo_ta={desc}"
        )
    return '\n'.join(lines)


def _product_url(pid: int) -> str:
    base = (settings.CHAT_STORE_BASE_URL or '').strip()
    if base:
        return f'{base}/products/{pid}/'
    return f'/products/{pid}/'


def _call_gemini(prompt: str) -> str:
    api_key = (settings.GEMINI_API_KEY or '').strip()
    model = (settings.GEMINI_MODEL or 'gemini-2.5-flash').strip()
    if not api_key:
        raise RuntimeError('GEMINI_API_KEY is empty')
    url = GEMINI_API_URL.format(model=model)
    resp = requests.post(
        f'{url}?key={api_key}',
        json={
            'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
            'generationConfig': {'temperature': 0.3, 'maxOutputTokens': 900},
        },
        timeout=20,
    )
    resp.raise_for_status()
    body = resp.json()
    candidates = body.get('candidates') or []
    if not candidates:
        raise RuntimeError('Gemini returned no candidates')
    parts = ((candidates[0].get('content') or {}).get('parts') or [])
    text = ''.join(str(p.get('text') or '') for p in parts).strip()
    if not text:
        raise RuntimeError('Gemini returned empty text')
    return text


def _fallback_reply(message: str, retrieval: ChatRetrieval) -> str:
    if not retrieval.products:
        return 'Mình chưa tìm thấy sản phẩm phù hợp. Bạn thử nêu rõ hơn về nhu cầu, mức giá hoặc danh mục nhé.'
    lines = ['Mình gợi ý một số sản phẩm phù hợp:']
    for p in retrieval.products[:5]:
        pid = int(p['id'])
        lines.append(f"- #{pid} {p.get('name')} ({_product_url(pid)})")
    if retrieval.cf_reason_lines:
        lines.append('')
        lines.append('Ly do goi y tu hanh vi user tuong tu:')
        lines.extend([f'- {line}' for line in retrieval.cf_reason_lines[:3]])
    return '\n'.join(lines)


def chat_with_rag(
    *,
    message: str,
    user_id: Optional[int],
    history: Optional[List[Dict[str, str]]] = None,
    include_context: bool = False,
) -> Dict[str, Any]:
    intent = _detect_intent(message)
    if intent == 'product_detail':
        retrieval = _retrieve_detail_product(message=message, user_id=user_id)
    else:
        retrieval = _retrieve_products(message=message, user_id=user_id, top_k=10)
    history = history or []
    history_text = '\n'.join(
        [f"{h.get('role', 'user')}: {(h.get('content') or '')[:300]}" for h in history[-8:]]
    )
    context_text = _build_context(retrieval.products)
    if intent == 'product_detail':
        prompt = (
            'Ban la tro ly tu van san pham cho cua hang.\n'
            'Nguoi dung dang can gioi thieu CHI TIET mot san pham cu the.\n'
            'Tra loi bang tieng Viet, ngan gon, tap trung: mo ta, thong so, gia, tinh trang hang, va link.\n'
            'Khong liet ke danh sach goi y nhieu san pham tru khi user yeu cau them.\n\n'
            f'LICH SU:\n{history_text}\n\n'
            f'CAU HOI:\n{message}\n\n'
            f'NGU CANH SAN PHAM:\n{context_text}\n'
        )
    else:
        prompt = (
            'Ban la tro ly tu van san pham cho cua hang.\n'
            'Tra loi bang tieng Viet, ngan gon, dung thong tin trong ngu canh.\n'
            'Neu co goi y, uu tien liet ke 3-6 san pham voi dinh dang: "- #ID Ten (URL)".\n'
            'Neu nguoi dung hoi loc theo thuoc tinh/gia, chi tra cac san pham phu hop.\n'
            'Neu khong du thong tin thi noi ro va de xuat cach hoi tiep.\n\n'
            f'LICH SU:\n{history_text}\n\n'
            f'CAU HOI:\n{message}\n\n'
            f'NGU CANH SAN PHAM:\n{context_text}\n'
        )
    try:
        reply = _call_gemini(prompt)
    except Exception as exc:
        logger.warning('Gemini call failed, fallback reply used: %s', exc)
        reply = _fallback_reply(message, retrieval)

    if retrieval.cf_reason_lines:
        cf_lines = '\n'.join([f'- {line}' for line in retrieval.cf_reason_lines[:3]])
        reply = (
            f"{reply.strip()}\n\n"
            "Ly do tu hanh vi user tuong tu:\n"
            f"{cf_lines}"
        )

    # Với intent chi tiết, chỉ gắn link của đúng sản phẩm đó.
    lines = [reply.strip(), '', 'Tham khao nhanh:']
    link_ids = retrieval.product_ids[:1] if intent == 'product_detail' else retrieval.product_ids[:6]
    for pid in link_ids:
        lines.append(f'{_product_url(int(pid))}')
    final_reply = '\n'.join([ln for ln in lines if ln is not None]).strip()
    payload: Dict[str, Any] = {
        'reply': final_reply,
        'recommended_products': retrieval.product_ids[:10],
        'source': f'rag_gemini:{retrieval.source}',
    }
    if include_context:
        payload['context_products'] = retrieval.products[:10]
    return payload
