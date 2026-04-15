"""
RAG: truy xuất ngữ cảnh từ knowledge graph (NetworkX) + enrich catalog,
    sinh câu trả lời qua Google Gemini (REST) hoặc tóm tắt khi chưa cấu hình API key.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

import requests
from django.conf import settings

from catalog_proxy.client import get_product, get_products_bulk, search_products

from .graph_storage import NodeType
from .inference import RecommendEngine
from .realtime_graph import get_graph_builder

logger = logging.getLogger(__name__)

_GEMINI_API_BASE = 'https://generativelanguage.googleapis.com/v1beta'

_QA_INTENT = re.compile(
    r'(giới\s*thiệu|mô\s*tả|thông\s*tin|là\s*gì|đặc\s*điểm|kể\s*về|cho\s*biết|review|ra\s*sao|có\s*gì|nói\s*về)',
    re.IGNORECASE,
)
_REC_INTENT = re.compile(
    r'(gợi\s*ý|đề\s*xuất|nên\s*mua|recommend|sản\s*phẩm\s*nào|mua\s*gì|phù\s*hợp\s*với)',
    re.IGNORECASE,
)


def _tokens(message: str) -> List[str]:
    parts = [t.lower() for t in re.split(r'[^\w\u00C0-\u024f]+', message, flags=re.UNICODE) if len(t) >= 2]
    seen: Set[str] = set()
    out: List[str] = []
    for p in parts:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out[:40]


def _normalize_for_match(s: str) -> str:
    return re.sub(r'\s+', ' ', (s or '').lower().strip())


def _is_qa_intent(message: str) -> bool:
    return bool(_QA_INTENT.search(message or ''))


def _is_recommend_intent(message: str) -> bool:
    return bool(_REC_INTENT.search(message or ''))


def _is_brief_greeting(message: str) -> bool:
    m = (message or '').strip().lower()
    if len(m) <= 1:
        return True
    return m in {
        'hi', 'hello', 'test', 'chào', 'xin chào', 'hey', 'help', 'cảm ơn', 'thanks', 'thank you',
    }


def _name_matches_message(name: str, message_norm: str) -> bool:
    n = _normalize_for_match(name)
    if len(n) < 3:
        return False
    if n in message_norm:
        return True
    parts = [t for t in n.split() if len(t) > 1]
    if not parts:
        return False
    hits = sum(1 for t in parts if t in message_norm)
    if len(parts) >= 3:
        return hits >= 2
    if len(parts) == 2:
        return hits >= 2
    return hits >= 1


def _extract_search_query(message: str) -> str:
    s = message or ''
    for pat in (
        r'giới\s*thiệu\s*về',
        r'cho\s*tôi\s*biết\s*về',
        r'mô\s*tả',
        r'thông\s*tin\s*về',
        r'sản\s*phẩm',
        r'sản\s*phầm',
        r'về\s*sản\s*phẩm',
    ):
        s = re.sub(pat, ' ', s, flags=re.IGNORECASE)
    s = re.sub(r'[^\w\s\u00C0-\u024f]', ' ', s, flags=re.UNICODE)
    s = ' '.join(s.split()).strip()
    return (s[:120] if s else (message or '').strip()[:120])


def _match_pids_from_message(message: str, pid_to_meta: Dict[int, Dict]) -> List[int]:
    msg_n = _normalize_for_match(message)
    scored: List[Tuple[int, int]] = []
    for pid, p in pid_to_meta.items():
        name = (p.get('name') or '').strip()
        if _name_matches_message(name, msg_n):
            scored.append((pid, len(_normalize_for_match(name))))
    scored.sort(key=lambda x: -x[1])
    return [pid for pid, _ in scored[:5]]


def _resolve_focus_product_ids(message: str, graph_pids: List[int]) -> Tuple[List[int], str]:
    """Sản phẩm người dùng đang nhắc tới — ưu tiên khớp tên trong tập đồ thị, sau đó search catalog."""
    bulk = get_products_bulk(graph_pids) if graph_pids else {}
    matched = _match_pids_from_message(message, bulk)
    if matched:
        return matched[:3], 'graph_name_match'

    q = _extract_search_query(message)
    want_lookup = _is_qa_intent(message) or (
        len(q) >= 5 and not _is_recommend_intent(message)
    )
    if not want_lookup:
        return [], 'none'

    if len(q) < 2:
        return [], 'none'

    rows = search_products(q, limit=8)
    msg_n = _normalize_for_match(message)
    picked: List[int] = []
    for r in rows:
        rid = r.get('id')
        if rid is None:
            continue
        pid = int(rid)
        name = (r.get('name') or '').strip()
        if _name_matches_message(name, msg_n):
            picked.append(pid)
    if not picked:
        picked = [int(r['id']) for r in rows if r.get('id') is not None][:3]

    return picked[:3], 'catalog_search'


def _strip_html(text: str) -> str:
    t = re.sub(r'<[^>]+>', ' ', text or '')
    return re.sub(r'\s+', ' ', t).strip()


def _build_catalog_detail_block(product_ids: List[int]) -> str:
    if not product_ids:
        return ''
    lines: List[str] = [
        '## Chi tiết sản phẩm (catalog — dùng để giới thiệu / trả lời chi tiết, không bịa thêm)',
    ]
    for pid in product_ids[:2]:
        p = get_product(pid) or {}
        name = (p.get('name') or '').strip() or f'Sản phẩm #{pid}'
        desc = _strip_html(p.get('description') or '')[:2000]
        brand_name = ''
        br = p.get('brand')
        if isinstance(br, dict):
            brand_name = (br.get('name') or '').strip()
        lines.append(f'### [{pid}] {name}' + (f' — Thương hiệu: {brand_name}' if brand_name else ''))
        lines.append(desc if desc else '(Chưa có mô tả dài trong catalog.)')
    return '\n'.join(lines)


def _template_qa_answer(focus_pids: List[int]) -> str:
    parts: List[str] = []
    for pid in focus_pids[:2]:
        p = get_product(pid) or {}
        name = (p.get('name') or '').strip() or f'Sản phẩm #{pid}'
        desc = _strip_html(p.get('description') or '')[:1500]
        brand_name = ''
        br = p.get('brand')
        if isinstance(br, dict):
            brand_name = (br.get('name') or '').strip()
        head = f'{name}' + (f' ({brand_name})' if brand_name else '')
        body = desc if desc else 'Hiện chưa có đoạn mô tả chi tiết trong hệ thống.'
        parts.append(f'{head}\n\n{body}')
    parts.append('Tham khảo & đặt mua trên cửa hàng:\n' + format_product_links_block(focus_pids[:2], 2))
    return '\n\n'.join(parts)


def _user_product_edges(storage, user_id: int) -> List[Tuple[int, float]]:
    ukey = (NodeType.USER, user_id)
    if ukey not in storage.raw_graph:
        return []
    rows: List[Tuple[int, float]] = []
    for nb, w, et in storage.neighbors(ukey):
        if et != 'interacts':
            continue
        if nb[0] != NodeType.PRODUCT:
            continue
        rows.append((int(nb[1]), float(w)))
    rows.sort(key=lambda x: -x[1])
    return rows


def _products_from_query_nodes(storage, tokens: List[str], limit: int = 12) -> List[int]:
    g = storage.raw_graph
    out: List[int] = []
    seen: Set[int] = set()
    if not tokens:
        return out
    for node in g.nodes():
        if not isinstance(node, tuple) or len(node) != 2:
            continue
        nt, qk = node
        if nt != NodeType.QUERY:
            continue
        qs = str(qk).lower()
        if not any(t in qs for t in tokens):
            continue
        for pred in g.predecessors(node):
            if pred[0] != NodeType.USER:
                continue
            for _, dst, k, data in g.out_edges(pred, keys=True, data=True):
                if dst[0] != NodeType.PRODUCT:
                    continue
                et = data.get('edge_type', k)
                if et != 'interacts':
                    continue
                pid = int(dst[1])
                if pid not in seen:
                    seen.add(pid)
                    out.append(pid)
                if len(out) >= limit:
                    return out
    return out


def _co_click_related(storage, seed_pids: List[int], limit: int = 10) -> List[int]:
    g = storage.raw_graph
    out: List[int] = []
    seen = set(seed_pids)
    for pid in seed_pids[:5]:
        pkey = (NodeType.PRODUCT, pid)
        if pkey not in g:
            continue
        for nb, _w, et in storage.neighbors(pkey):
            if et != 'co_click':
                continue
            if nb[0] != NodeType.PRODUCT:
                continue
            nid = int(nb[1])
            if nid in seen:
                continue
            seen.add(nid)
            out.append(nid)
            if len(out) >= limit:
                return out
    return out


def build_graph_context(
    message: str,
    user_id: Optional[int] = None,
    *,
    max_products: int = 32,
) -> Tuple[str, List[int], Dict[str, Any]]:
    meta: Dict[str, Any] = {'user_id': user_id, 'from_graph': True}
    try:
        storage = get_graph_builder().storage
    except Exception as exc:
        logger.warning('graph_rag: no graph builder: %s', exc)
        return (
            '(Chưa có đồ thị gợi ý — chạy pipeline /api/recommend/retrain hoặc ghi sự kiện tracking.)',
            [],
            {**meta, 'error': str(exc)},
        )

    tokens = _tokens(message)
    scored: Dict[int, float] = {}

    if user_id:
        for pid, w in _user_product_edges(storage, user_id):
            scored[pid] = scored.get(pid, 0.0) + w + 10.0

        if RecommendEngine.instance().is_ready:
            try:
                pids, src, _ = RecommendEngine.instance().recommend(user_id, top_k=12)
                for i, pid in enumerate(pids):
                    bonus = 5.0 - i * 0.2
                    scored[pid] = scored.get(pid, 0.0) + max(bonus, 0.5)
                meta['recommend_source'] = src
            except Exception as exc:
                logger.debug('recommend in RAG skipped: %s', exc)

    for pid in _products_from_query_nodes(storage, tokens):
        scored[pid] = scored.get(pid, 0.0) + 3.0

    ordered = sorted(scored.keys(), key=lambda p: -scored[p])
    seed = ordered[:8]
    for pid in _co_click_related(storage, seed):
        if pid not in scored:
            scored[pid] = 1.0
    ordered = sorted(scored.keys(), key=lambda p: -scored[p])
    final_ids = ordered[:max_products]

    products = get_products_bulk(final_ids)
    lines: List[str] = []
    lines.append('## Ngữ cảnh trích từ đồ thị người dùng–sản phẩm (RAG)')
    if user_id:
        ups = _user_product_edges(storage, user_id)[:8]
        if ups:
            parts = [f"product {pid} (trọng số tương tác ~{w:.2f})" for pid, w in ups]
            lines.append(f'- Người dùng #{user_id}: ' + '; '.join(parts))
        else:
            lines.append(f'- Người dùng #{user_id}: chưa có cạnh tương tác rõ trong đồ thị.')

    if tokens:
        lines.append(f'- Từ khóa truy vấn trích được: {", ".join(tokens[:12])}')

    for pid in final_ids:
        p = products.get(pid) or {}
        name = p.get('name') or f'sản phẩm #{pid}'
        brand = p.get('brand_name') or ''
        price = p.get('min_price')
        extra = f'; thương hiệu: {brand}' if brand else ''
        if price is not None:
            extra += f'; giá tham khảo: {price}'
        lines.append(f'- [{pid}] {name}{extra}')

    if not final_ids:
        lines.append(
            '- (Không tìm thấy nút sản phẩm phù hợp trong đồ thị — thử mô tả chi tiết hơn hoặc dùng tài khoản đã tương tác.)'
        )

    meta['product_count'] = len(final_ids)
    return '\n'.join(lines), final_ids, meta


def _gemini_api_key() -> str:
    return (
        (getattr(settings, 'GEMINI_API_KEY', None) or '')
        or os.environ.get('GEMINI_API_KEY', '')
        or os.environ.get('GOOGLE_API_KEY', '')
    ).strip()


def _product_detail_path(product_id: int) -> str:
    return f'/products/{product_id}/'


def _product_detail_url(product_id: int) -> str:
    base = (getattr(settings, 'CHAT_STORE_BASE_URL', None) or '').strip().rstrip('/')
    path = _product_detail_path(product_id)
    return f'{base}{path}' if base else path


def format_product_links_block(product_ids: List[int], limit: int = 10) -> str:
    """Khối văn bản: mỗi sản phẩm 2 dòng — tên, rồi URL (cho template + Gemini + UI linkify)."""
    if not product_ids:
        return ''
    bulk = get_products_bulk(product_ids[:limit])
    lines: List[str] = []
    for pid in product_ids[:limit]:
        p = bulk.get(pid) or {}
        name = (p.get('name') or '').strip() or f'Sản phẩm #{pid}'
        url = _product_detail_url(pid)
        lines.append(f'• {name}\n  {url}')
    return '\n'.join(lines)


def _gemini_generate(system_prompt: str, user_payload: str, history: List[Dict[str, str]]) -> Optional[str]:
    key = _gemini_api_key()
    if not key:
        return None

    model = (getattr(settings, 'GEMINI_MODEL', None) or os.environ.get('GEMINI_MODEL', 'gemini-1.5-flash')).strip()
    timeout = int(getattr(settings, 'GEMINI_TIMEOUT', 60) or 60)

    url = f'{_GEMINI_API_BASE}/models/{model}:generateContent'
    params = {'key': key}

    contents: List[Dict[str, Any]] = []
    for h in history[-10:]:
        role = h.get('role')
        content = (h.get('content') or '').strip()
        if not content:
            continue
        if role == 'user':
            contents.append({'role': 'user', 'parts': [{'text': content}]})
        elif role == 'assistant':
            contents.append({'role': 'model', 'parts': [{'text': content}]})

    contents.append({'role': 'user', 'parts': [{'text': user_payload}]})

    body: Dict[str, Any] = {
        'systemInstruction': {'parts': [{'text': system_prompt}]},
        'contents': contents,
        'generationConfig': {
            'temperature': 0.3,
            'maxOutputTokens': 1024,
        },
    }

    try:
        resp = requests.post(url, params=params, json=body, timeout=timeout)
        if resp.status_code >= 400:
            logger.warning('Gemini HTTP %s: %s', resp.status_code, resp.text[:800])
            return None
        data = resp.json()
        cands = data.get('candidates') or []
        if not cands:
            logger.warning('Gemini no candidates: %s', json.dumps(data)[:500])
            return None
        parts = (cands[0].get('content') or {}).get('parts') or []
        texts = [p.get('text', '') for p in parts if isinstance(p, dict)]
        text = ''.join(texts).strip()
        return text or None
    except Exception as exc:
        logger.warning('Gemini request failed: %s', exc)
        return None


def synthesize_reply(
    user_message: str,
    context: str,
    product_ids: List[int],
    history: Optional[List[Dict[str, str]]] = None,
    *,
    focus_pids: Optional[List[int]] = None,
) -> Tuple[str, str]:
    hist = history or []
    focus_pids = list(focus_pids or [])
    is_qa = _is_qa_intent(user_message)
    is_rec = _is_recommend_intent(user_message)
    brief = _is_brief_greeting(user_message)

    link_graph = format_product_links_block(product_ids, limit=10) if product_ids else ''
    link_focus = format_product_links_block(focus_pids, limit=3) if focus_pids else ''

    tip = ''
    if not _gemini_api_key():
        tip = '\n\n(Bạn có thể đặt GEMINI_API_KEY hoặc GOOGLE_API_KEY để trò chuyện tự nhiên hơn với Gemini.)'

    if brief:
        return (
            'Chào bạn! Bạn có thể hỏi mình giới thiệu hoặc mô tả một sản phẩm (ghi rõ tên, ví dụ Xiaomi 16 Pro), '
            'hoặc nhờ gợi ý vài mặt hàng phù hợp với đồ thị sở thích.'
            + tip
        ), 'template'

    system = (
        'Bạn là trợ lý cửa hàng. Chỉ dựa trên phần Ngữ cảnh và phần Liên kết (nếu có). Trả lời tiếng Việt, rõ ràng.\n'
        '- Nếu ngữ cảnh có mục “Chi tiết sản phẩm (catalog)” và người dùng hỏi giới thiệu/mô tả/thông tin về sản phẩm: '
        'trả lời chủ yếu từ mô tả catalog, tóm tắt súc tích, không liệt kê dài cả danh sách gợi ý đồ thị trừ khi họ hỏi gợi ý chung. '
        'Cuối câu có thể thêm một dòng URL từ “Liên kết sản phẩm trọng tâm”. Không bịa thông tin ngoài ngữ cảnh.\n'
        '- Nếu người dùng muốn gợi ý chung (nên mua gì, gợi ý sản phẩm…): có thể dùng danh sách từ đồ thị và “Liên kết gợi ý”, mỗi sản phẩm tên + URL.\n'
        '- Nếu thiếu dữ liệu, nói thẳng và gợi ý xem trang chủ hoặc đăng nhập.'
    )

    payload = f"Câu hỏi người dùng:\n{user_message}\n\nNgữ cảnh:\n{context}"
    if link_focus:
        payload += f"\n\nLiên kết sản phẩm trọng tâm (tên + URL):\n{link_focus}\n"
    if link_graph and (is_rec or not focus_pids):
        payload += f"\n\nLiên kết gợi ý từ đồ thị (khi cần):\n{link_graph}\n"

    text = _gemini_generate(system, payload, hist)
    if text:
        append_links = ''
        if focus_pids and not is_rec and link_focus and 'products/' not in text:
            append_links = '\n\n— Xem chi tiết —\n' + link_focus
        elif (not focus_pids or is_rec) and link_graph and 'products/' not in text:
            append_links = '\n\n— Xem nhanh —\n' + link_graph
        if append_links:
            text = text.rstrip() + append_links
        return text, 'gemini'

    if focus_pids and not is_rec:
        return _template_qa_answer(focus_pids) + tip, 'template'

    if is_qa and not focus_pids:
        return (
            'Mình chưa tìm thấy sản phẩm trùng với câu hỏi trong catalog. '
            'Bạn thử ghi đúng tên sản phẩm (ví dụ đầy đủ tên model) hoặc tìm trên trang chủ.'
            + tip
        ), 'template'

    if product_ids and (is_rec or not is_qa):
        intro = (
            'Dựa trên đồ thị gợi ý, bạn có thể quan tâm các sản phẩm sau (bấm link trên cửa hàng để xem chi tiết):\n'
            + link_graph
        )
        return intro + tip, 'template'

    if product_ids:
        return (
            'Bạn muốn mình giới thiệu một sản phẩm (hãy ghi rõ tên) hay gợi ý vài mặt hàng?\n\n'
            'Một số sản phẩm liên quan đồ thị:\n'
            + link_graph
            + tip
        ), 'template'

    return (
        'Hiện chưa có đủ dữ liệu đồ thị hoặc catalog để trả lời. '
        'Xem danh sách trên trang chủ hoặc đăng nhập để cá nhân hóa.'
        + tip
    ), 'template'


def generate_rag_reply(
    message: str,
    user_id: Optional[int] = None,
    history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    ctx, pids, meta = build_graph_context(message, user_id=user_id)
    focus_pids, focus_source = _resolve_focus_product_ids(message, pids)
    meta['focus_product_ids'] = focus_pids
    meta['focus_source'] = focus_source

    detail_block = _build_catalog_detail_block(focus_pids) if focus_pids else ''
    full_ctx = ctx + ('\n\n' + detail_block if detail_block else '')

    reply, mode = synthesize_reply(
        message,
        full_ctx,
        pids,
        history=history,
        focus_pids=focus_pids,
    )
    return {
        'reply': reply,
        'mode': mode,
        'context': full_ctx,
        'product_ids': pids,
        'meta': meta,
    }
