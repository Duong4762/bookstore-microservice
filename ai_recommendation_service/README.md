# AI Recommendation Service (BiLSTM Sequence Recommender)

## Chạy local

```bash
cd ai_recommendation_service
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8008 --settings=config.settings.dev
```

Gửi event tracking → `POST /api/tracking/event/`, sau đó (khi đã có đủ dữ liệu) huấn luyện:

```bash
python manage.py train_recommendation
```

Hoặc `POST /api/recommend/retrain` (chạy nền), theo dõi `GET /api/recommend/retrain/status`.

Auto retrain hằng ngày đã bật mặc định trong service (không cần Celery), cấu hình qua env:

- `REC_AUTO_RETRAIN_ENABLED=1`
- `REC_AUTO_RETRAIN_INTERVAL_SECONDS=86400`

## API chính

- `GET /api/recommend?user_id=1&top_k=10` — gợi ý BiLSTM (fallback cold-start nếu chưa train).
- `POST /api/recommend/` — body JSON tương thích client cũ (`user_id`, `top_k`, `exclude_products`).
- `POST /api/recommend/retrain` — pipeline đầy đủ.
- `GET /health/` — trạng thái service và `ml_ready`.

Artifact mặc định nằm trong `ml/artifacts/`.
