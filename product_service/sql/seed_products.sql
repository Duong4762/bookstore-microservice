-- Seed dữ liệu catalog đa ngành cho product_service
-- Compatible: SQLite / PostgreSQL (tránh cú pháp đặc thù)
-- Chạy sau migrate.

BEGIN;

-- Xóa dữ liệu cũ theo thứ tự FK
DELETE FROM variants;
DELETE FROM products;
DELETE FROM categories;
DELETE FROM brands;
DELETE FROM product_types;

-- =========================
-- PRODUCT TYPES
-- =========================
INSERT INTO product_types (id, name, required_attributes) VALUES
(1, 'Laptop', '["cpu","ram","storage","screen_size"]'),
(2, 'Phone', '["chipset","ram","storage","screen_size"]'),
(3, 'Tablet', '["chipset","ram","storage","screen_size"]'),
(4, 'Monitor', '["panel","refresh_rate","resolution","size"]'),
(5, 'Audio', '["connectivity","battery"]'),
(6, 'Appliance', '["power","warranty"]'),
(7, 'Accessory', '["compatibility"]'),
(8, 'Gaming', '["platform"]'),
(9, 'SmartHome', '["connectivity"]'),
(10, 'Camera', '["sensor","lens"]'),
(11, 'Wearable', '["battery","connectivity"]'),
(12, 'Networking', '["speed","ports"]');

-- =========================
-- BRANDS
-- =========================
INSERT INTO brands (id, name, slug, description, is_active)
SELECT id, name, slug, description, (is_active_int <> 0)
FROM (VALUES
(1, 'Apple', 'apple', 'Apple ecosystem products', 1),
(2, 'Samsung', 'samsung', 'Samsung electronics', 1),
(3, 'Xiaomi', 'xiaomi', 'Xiaomi smart devices', 1),
(4, 'Dell', 'dell', 'Dell computers', 1),
(5, 'HP', 'hp', 'HP computers and accessories', 1),
(6, 'Lenovo', 'lenovo', 'Lenovo products', 1),
(7, 'Asus', 'asus', 'Asus products', 1),
(8, 'Acer', 'acer', 'Acer products', 1),
(9, 'Sony', 'sony', 'Sony products', 1),
(10, 'LG', 'lg', 'LG products', 1),
(11, 'JBL', 'jbl', 'JBL audio products', 1),
(12, 'Logitech', 'logitech', 'Logitech accessories', 1),
(13, 'TP-Link', 'tp-link', 'Networking products', 1),
(14, 'Philips', 'philips', 'Home appliances', 1),
(15, 'Razer', 'razer', 'Gaming products', 1),
(16, 'Canon', 'canon', 'Camera products', 1),
(17, 'Nikon', 'nikon', 'Camera products', 1),
(18, 'MSI', 'msi', 'Gaming laptops and hardware', 1),
(19, 'Anker', 'anker', 'Mobile accessories', 1),
(20, 'Garmin', 'garmin', 'Wearables and sports devices', 1)
) AS seed(id, name, slug, description, is_active_int);

-- =========================
-- CATEGORIES
-- =========================
INSERT INTO categories (id, name, slug, description, parent_id, is_active)
SELECT id, name, slug, description, parent_id, (is_active_int <> 0)
FROM (VALUES
(1, 'Electronics', 'electronics', 'Main electronics category', NULL, 1),
(2, 'Laptops', 'laptops', 'Laptop computers', 1, 1),
(3, 'Smartphones', 'smartphones', 'Mobile phones', 1, 1),
(4, 'Tablets', 'tablets', 'Tablet devices', 1, 1),
(5, 'Monitors', 'monitors', 'Displays and monitors', 1, 1),
(6, 'Audio', 'audio', 'Headphones and speakers', 1, 1),
(7, 'Accessories', 'accessories', 'Device accessories', 1, 1),
(8, 'Gaming', 'gaming', 'Gaming gear', 1, 1),
(9, 'Smart Home', 'smart-home', 'Smart home ecosystem', 1, 1),
(10, 'Cameras', 'cameras', 'Cameras and lens', 1, 1),
(11, 'Wearables', 'wearables', 'Smartwatch and bands', 1, 1),
(12, 'Networking', 'networking', 'Routers and mesh systems', 1, 1),
(13, 'Home Appliances', 'home-appliances', 'Appliances for home', 1, 1),
(14, 'Kitchen Appliances', 'kitchen-appliances', 'Kitchen devices', 13, 1),
(15, 'Cleaning Appliances', 'cleaning-appliances', 'Cleaning devices', 13, 1)
) AS seed(id, name, slug, description, parent_id, is_active_int);

-- =========================
-- PRODUCTS (300 items: 20 groups x 15)
-- Khớp dải ID với ai_recommendation_service/recommendation/services/product_groups.py
-- =========================
WITH RECURSIVE seq(n) AS (
    SELECT 1
    UNION ALL
    SELECT n + 1 FROM seq WHERE n < 15
),
groups(group_idx, group_key, category_id, brand_id, product_type_id) AS (
    VALUES
    (1,  'phone',    3, 2, 2),
    (2,  'case',     7, 19, 7),
    (3,  'charger',  7, 19, 7),
    (4,  'laptop',   2, 4, 1),
    (5,  'mouse',    7, 12, 7),
    (6,  'keyboard', 7, 12, 7),
    (7,  'headphone',6, 9, 5),
    (8,  'tablet',   4, 1, 3),
    (9,  'tshirt',   13, 14, 6),
    (10, 'shirt',    13, 14, 6),
    (11, 'jacket',   13, 14, 6),
    (12, 'jeans',    13, 14, 6),
    (13, 'shorts',   13, 14, 6),
    (14, 'shoes',    13, 14, 6),
    (15, 'sandals',  13, 14, 6),
    (16, 'bag',      7, 12, 7),
    (17, 'backpack', 7, 12, 7),
    (18, 'hat',      7, 12, 7),
    (19, 'watch',    11, 20, 11),
    (20, 'glasses',  7, 12, 7)
)
INSERT INTO products (
    id, name, slug, description, category_id, brand_id, product_type_id,
    attributes, is_active, created_at, updated_at
)
SELECT
    ((g.group_idx - 1) * 15 + s.n) AS id,
    CONCAT(UPPER(SUBSTRING(g.group_key, 1, 1)), SUBSTRING(g.group_key, 2), ' Product ', LPAD(s.n::text, 2, '0')) AS name,
    CONCAT(g.group_key, '-product-', LPAD(s.n::text, 2, '0')) AS slug,
    CONCAT('Auto generated ', g.group_key, ' item #', s.n, ' (group ', g.group_idx, ').') AS description,
    g.category_id,
    g.brand_id,
    g.product_type_id,
    jsonb_build_object(
        'group', g.group_key,
        'group_index', g.group_idx,
        'slot', s.n,
        'seed_profile', 'ai-compatible-300'
    ) AS attributes,
    TRUE AS is_active,
    NOW(),
    NOW()
FROM groups g
CROSS JOIN seq s
ORDER BY id;

-- =========================
-- VARIANTS (1 variant mỗi product)
-- =========================
INSERT INTO variants (
    id, product_id, sku, price, stock, attributes, cover_image_url, is_active
)
SELECT
    p.id AS id,
    p.id AS product_id,
    CONCAT('SKU-', LPAD(p.id::text, 4, '0')) AS sku,
    (199000 + p.id * 1000) AS price,
    20 + (p.id % 40) AS stock,
    jsonb_build_object(
        'tier', CASE WHEN (p.id % 3) = 0 THEN 'premium' WHEN (p.id % 3) = 1 THEN 'standard' ELSE 'basic' END,
        'seed_profile', 'ai-compatible-300'
    ) AS attributes,
    NULL::text AS cover_image_url,
    TRUE AS is_active
FROM products p
WHERE p.id BETWEEN 1 AND 300
ORDER BY p.id;

-- Đồng bộ sequence để insert mới không bị trùng PK
SELECT setval('products_id_seq', COALESCE((SELECT MAX(id) FROM products), 1), TRUE);
SELECT setval('variants_id_seq', COALESCE((SELECT MAX(id) FROM variants), 1), TRUE);

COMMIT;
