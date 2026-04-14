# SQL Seed Catalog

File: `product_service/sql/seed_products.sql`

Seed này tạo:
- 15 categories
- 20 brands
- 12 product types
- 60 products
- 62 variants

## Chạy trong Docker (khuyến nghị)

```bash
docker compose exec product-service python manage.py dbshell --settings=config.settings.dev < sql/seed_products.sql
```

Neu container không có `dbshell`, dùng sqlite trực tiếp:

```bash
docker compose exec product-service sh -lc "python - <<'PY'
import sqlite3
from pathlib import Path
db = Path('db_dev.sqlite3')
sql = Path('sql/seed_products.sql').read_text(encoding='utf-8')
con = sqlite3.connect(db)
con.executescript(sql)
con.commit()
con.close()
print('Seed done')
PY"
```

## Lưu ý

- Seed script sẽ `DELETE` dữ liệu catalog cũ trước khi insert.
- Nên chạy sau migrate.
