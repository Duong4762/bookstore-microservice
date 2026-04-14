# AI Recommendation Service (Knowledge Graph + GNN + FAISS)

## Chạy local

```bash
cd ai_recommendation_service
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install torch-scatter torch-sparse -f https://data.pyg.org/whl/torch-2.2.0+cpu.html
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8008 --settings=config.settings.dev
```

Gửi event tracking → `POST /api/tracking/event/`, sau đó (khi đã có đủ dữ liệu) huấn luyện:

```bash
python manage.py train_recommendation
```

Hoặc `POST /api/recommend/retrain` (chạy nền), theo dõi `GET /api/recommend/retrain/status`.

Auto retrain mỗi giờ đã bật mặc định trong service (không cần Celery), cấu hình qua env:

- `REC_AUTO_RETRAIN_ENABLED=1`
- `REC_AUTO_RETRAIN_INTERVAL_SECONDS=3600`

## API chính

- `GET /api/recommend?user_id=1&top_k=10` — gợi ý GNN + FAISS (fallback cold-start nếu chưa train).
- `POST /api/recommend/` — body JSON tương thích client cũ (`user_id`, `top_k`, `exclude_products`).
- `POST /api/recommend/retrain` — pipeline đầy đủ.
- `GET /health/` — trạng thái service và `ml_ready`.

## Scripts pipeline (từng bước)

```bash
python scripts/build_graph.py
python scripts/preprocess_graph.py
python scripts/train_gnn.py
python scripts/build_faiss_index.py
```

Artifact mặc định nằm trong `ml/artifacts/`.
