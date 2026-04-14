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
-- PRODUCTS (60 items)
-- =========================
INSERT INTO products (id, name, slug, description, category_id, brand_id, product_type_id, attributes, is_active, created_at, updated_at)
SELECT id, name, slug, description, category_id, brand_id, product_type_id, attributes::jsonb, (is_active_int <> 0), NOW(), NOW()
FROM (VALUES
-- Laptops
(1, 'Dell XPS 13 2026', 'dell-xps-13-2026', 'Ultrabook premium 13 inch.', 2, 4, 1, '{"cpu":"Intel Core Ultra 7","ram":"16GB","storage":"512GB SSD","screen_size":"13.4"}', 1),
(2, 'HP Spectre x360 14', 'hp-spectre-x360-14', 'Convertible laptop for office.', 2, 5, 1, '{"cpu":"Intel Core Ultra 5","ram":"16GB","storage":"1TB SSD","screen_size":"14"}', 1),
(3, 'Lenovo ThinkPad X1 Carbon Gen 13', 'lenovo-thinkpad-x1-carbon-gen-13', 'Business laptop with durability.', 2, 6, 1, '{"cpu":"Intel Core Ultra 7","ram":"32GB","storage":"1TB SSD","screen_size":"14"}', 1),
(4, 'Asus Zenbook 14 OLED', 'asus-zenbook-14-oled', 'Portable laptop OLED display.', 2, 7, 1, '{"cpu":"AMD Ryzen 7","ram":"16GB","storage":"512GB SSD","screen_size":"14"}', 1),
(5, 'Acer Swift Go 14', 'acer-swift-go-14', 'Lightweight productivity laptop.', 2, 8, 1, '{"cpu":"Intel Core i7","ram":"16GB","storage":"512GB SSD","screen_size":"14"}', 1),
(6, 'MSI Stealth 16 AI', 'msi-stealth-16-ai', 'Gaming and creator laptop.', 2, 18, 1, '{"cpu":"Intel Core Ultra 9","ram":"32GB","storage":"1TB SSD","screen_size":"16"}', 1),

-- Smartphones
(7, 'iPhone 17 Pro', 'iphone-17-pro', 'Flagship Apple smartphone.', 3, 1, 2, '{"chipset":"A19 Pro","ram":"8GB","storage":"256GB","screen_size":"6.3"}', 1),
(8, 'iPhone 17', 'iphone-17', 'Mainstream Apple smartphone.', 3, 1, 2, '{"chipset":"A19","ram":"8GB","storage":"128GB","screen_size":"6.1"}', 1),
(9, 'Samsung Galaxy S26 Ultra', 'samsung-galaxy-s26-ultra', 'Top Samsung flagship.', 3, 2, 2, '{"chipset":"Snapdragon 8 Gen 5","ram":"12GB","storage":"256GB","screen_size":"6.8"}', 1),
(10, 'Samsung Galaxy A76', 'samsung-galaxy-a76', 'Midrange Samsung phone.', 3, 2, 2, '{"chipset":"Exynos 1680","ram":"8GB","storage":"256GB","screen_size":"6.6"}', 1),
(11, 'Xiaomi 16 Pro', 'xiaomi-16-pro', 'High performance Xiaomi phone.', 3, 3, 2, '{"chipset":"Snapdragon 8 Gen 5","ram":"12GB","storage":"512GB","screen_size":"6.7"}', 1),
(12, 'Xiaomi Redmi Note 16', 'xiaomi-redmi-note-16', 'Budget-performance smartphone.', 3, 3, 2, '{"chipset":"Dimensity 9400e","ram":"8GB","storage":"256GB","screen_size":"6.67"}', 1),

-- Tablets
(13, 'iPad Pro 13 M5', 'ipad-pro-13-m5', 'Powerful tablet for creators.', 4, 1, 3, '{"chipset":"Apple M5","ram":"16GB","storage":"512GB","screen_size":"13"}', 1),
(14, 'iPad Air 11 M4', 'ipad-air-11-m4', 'Lightweight tablet for daily use.', 4, 1, 3, '{"chipset":"Apple M4","ram":"8GB","storage":"256GB","screen_size":"11"}', 1),
(15, 'Samsung Galaxy Tab S11+', 'samsung-galaxy-tab-s11-plus', 'Android premium tablet.', 4, 2, 3, '{"chipset":"Snapdragon 8 Gen 4","ram":"12GB","storage":"256GB","screen_size":"12.4"}', 1),
(16, 'Xiaomi Pad 8 Pro', 'xiaomi-pad-8-pro', 'Performance tablet at value price.', 4, 3, 3, '{"chipset":"Snapdragon 8s Gen 4","ram":"8GB","storage":"256GB","screen_size":"12.1"}', 1),

-- Monitors
(17, 'LG UltraGear 27 2K 180Hz', 'lg-ultragear-27-2k-180hz', 'Gaming monitor smooth refresh.', 5, 10, 4, '{"panel":"IPS","refresh_rate":"180Hz","resolution":"2560x1440","size":"27"}', 1),
(18, 'Samsung Odyssey G8 32', 'samsung-odyssey-g8-32', 'Curved gaming monitor.', 5, 2, 4, '{"panel":"VA","refresh_rate":"240Hz","resolution":"3840x2160","size":"32"}', 1),
(19, 'Dell UltraSharp U2726Q', 'dell-ultrasharp-u2726q', 'Professional color monitor.', 5, 4, 4, '{"panel":"IPS","refresh_rate":"60Hz","resolution":"3840x2160","size":"27"}', 1),
(20, 'Asus ProArt PA279', 'asus-proart-pa279', 'Creator monitor with color accuracy.', 5, 7, 4, '{"panel":"IPS","refresh_rate":"75Hz","resolution":"3840x2160","size":"27"}', 1),

-- Audio
(21, 'Sony WH-1000XM7', 'sony-wh-1000xm7', 'Noise cancelling headphones.', 6, 9, 5, '{"connectivity":"Bluetooth 5.4","battery":"40h"}', 1),
(22, 'Apple AirPods Pro 3', 'apple-airpods-pro-3', 'Premium ANC earbuds.', 6, 1, 5, '{"connectivity":"Bluetooth 5.4","battery":"30h"}', 1),
(23, 'JBL Charge 7', 'jbl-charge-7', 'Portable Bluetooth speaker.', 6, 11, 5, '{"connectivity":"Bluetooth 5.3","battery":"24h"}', 1),
(24, 'Samsung Galaxy Buds 4 Pro', 'samsung-galaxy-buds-4-pro', 'Samsung flagship earbuds.', 6, 2, 5, '{"connectivity":"Bluetooth 5.4","battery":"28h"}', 1),

-- Accessories
(25, 'Logitech MX Master 4', 'logitech-mx-master-4', 'Productivity mouse.', 7, 12, 7, '{"compatibility":"Windows/macOS"}', 1),
(26, 'Logitech MX Keys S Plus', 'logitech-mx-keys-s-plus', 'Wireless keyboard.', 7, 12, 7, '{"compatibility":"Windows/macOS"}', 1),
(27, 'Anker 737 Power Bank', 'anker-737-power-bank', 'High capacity power bank.', 7, 19, 7, '{"compatibility":"USB-C PD"}', 1),
(28, 'Anker 140W USB-C Charger', 'anker-140w-usbc-charger', 'Fast charger for laptops.', 7, 19, 7, '{"compatibility":"USB-C PD 3.1"}', 1),
(29, 'Apple MagSafe Charger 2', 'apple-magsafe-charger-2', 'Wireless charger for iPhone.', 7, 1, 7, '{"compatibility":"MagSafe iPhone"}', 1),
(30, 'Samsung 45W Super Fast Charger', 'samsung-45w-super-fast-charger', 'Fast charger for Galaxy.', 7, 2, 7, '{"compatibility":"USB-C PPS"}', 1),

-- Gaming
(31, 'Razer BlackWidow V5', 'razer-blackwidow-v5', 'Mechanical gaming keyboard.', 8, 15, 8, '{"platform":"PC"}', 1),
(32, 'Razer DeathAdder V4 Pro', 'razer-deathadder-v4-pro', 'Esports gaming mouse.', 8, 15, 8, '{"platform":"PC"}', 1),
(33, 'Sony PlayStation 6', 'sony-playstation-6', 'Next-gen console.', 8, 9, 8, '{"platform":"Console"}', 1),
(34, 'Asus ROG Ally 2', 'asus-rog-ally-2', 'Portable gaming handheld.', 8, 7, 8, '{"platform":"Handheld"}', 1),

-- Smart Home
(35, 'Xiaomi Smart Cam Pro 4K', 'xiaomi-smart-cam-pro-4k', 'Indoor smart camera.', 9, 3, 9, '{"connectivity":"Wi-Fi 6"}', 1),
(36, 'Philips Hue Bridge 3', 'philips-hue-bridge-3', 'Smart lighting hub.', 9, 14, 9, '{"connectivity":"Zigbee"}', 1),
(37, 'Samsung SmartThings Hub 2026', 'samsung-smartthings-hub-2026', 'Smart home central hub.', 9, 2, 9, '{"connectivity":"Wi-Fi/Zigbee/Thread"}', 1),
(38, 'TP-Link Tapo Doorbell X', 'tp-link-tapo-doorbell-x', 'Video smart doorbell.', 9, 13, 9, '{"connectivity":"Wi-Fi"}', 1),

-- Cameras
(39, 'Canon EOS R8 Mark II', 'canon-eos-r8-mark-ii', 'Mirrorless full-frame camera.', 10, 16, 10, '{"sensor":"Full Frame","lens":"RF Mount"}', 1),
(40, 'Nikon Z6 III', 'nikon-z6-iii', 'Mirrorless hybrid camera.', 10, 17, 10, '{"sensor":"Full Frame","lens":"Z Mount"}', 1),
(41, 'Sony Alpha A7V', 'sony-alpha-a7v', 'High-end mirrorless camera.', 10, 9, 10, '{"sensor":"Full Frame","lens":"E Mount"}', 1),
(42, 'Canon RF 24-70mm F2.8L II', 'canon-rf-24-70-f28l-ii', 'Professional zoom lens.', 10, 16, 10, '{"sensor":"N/A","lens":"RF"}', 1),

-- Wearables
(43, 'Apple Watch Series 12', 'apple-watch-series-12', 'Smartwatch for iOS.', 11, 1, 11, '{"battery":"36h","connectivity":"Bluetooth/Wi-Fi/LTE"}', 1),
(44, 'Samsung Galaxy Watch 9', 'samsung-galaxy-watch-9', 'Smartwatch for Android.', 11, 2, 11, '{"battery":"48h","connectivity":"Bluetooth/Wi-Fi/LTE"}', 1),
(45, 'Garmin Forerunner 975', 'garmin-forerunner-975', 'Running and fitness smartwatch.', 11, 20, 11, '{"battery":"14d","connectivity":"Bluetooth/GPS"}', 1),
(46, 'Xiaomi Smart Band 10', 'xiaomi-smart-band-10', 'Fitness smart band.', 11, 3, 11, '{"battery":"21d","connectivity":"Bluetooth"}', 1),

-- Networking
(47, 'TP-Link Archer AXE5400', 'tp-link-archer-axe5400', 'Wi-Fi 6E router.', 12, 13, 12, '{"speed":"5400Mbps","ports":"4xLAN+1xWAN"}', 1),
(48, 'TP-Link Deco BE65 (2-pack)', 'tp-link-deco-be65-2pack', 'Wi-Fi 7 mesh system.', 12, 13, 12, '{"speed":"6500Mbps","ports":"2x2.5G"}', 1),
(49, 'Asus RT-BE88U', 'asus-rt-be88u', 'High performance Wi-Fi 7 router.', 12, 7, 12, '{"speed":"8800Mbps","ports":"8xLAN"}', 1),
(50, 'Xiaomi Router BE7000', 'xiaomi-router-be7000', 'Home Wi-Fi 7 router.', 12, 3, 12, '{"speed":"7000Mbps","ports":"4xLAN"}', 1),

-- Home Appliances / Kitchen
(51, 'Philips Air Fryer XXL 5000', 'philips-air-fryer-xxl-5000', 'Large capacity air fryer.', 14, 14, 6, '{"power":"2200W","warranty":"24m"}', 1),
(52, 'Xiaomi Smart Air Purifier 6', 'xiaomi-smart-air-purifier-6', 'Smart home air purifier.', 13, 3, 6, '{"power":"60W","warranty":"12m"}', 1),
(53, 'LG CordZero A12', 'lg-cordzero-a12', 'Cordless vacuum cleaner.', 15, 10, 6, '{"power":"450W","warranty":"24m"}', 1),
(54, 'Samsung Bespoke Microwave 30L', 'samsung-bespoke-microwave-30l', 'Smart microwave oven.', 14, 2, 6, '{"power":"1400W","warranty":"24m"}', 1),
(55, 'Philips Robot Vacuum R700', 'philips-robot-vacuum-r700', 'Robot vacuum cleaner.', 15, 14, 6, '{"power":"70W","warranty":"24m"}', 1),

-- More products for volume
(56, 'Lenovo Legion 7i Pro 2026', 'lenovo-legion-7i-pro-2026', 'High-end gaming laptop.', 2, 6, 1, '{"cpu":"Intel Core Ultra 9","ram":"32GB","storage":"2TB SSD","screen_size":"16"}', 1),
(57, 'Asus ROG Phone 10', 'asus-rog-phone-10', 'Gaming smartphone.', 3, 7, 2, '{"chipset":"Snapdragon 8 Gen 5","ram":"16GB","storage":"512GB","screen_size":"6.78"}', 1),
(58, 'Dell P2426H', 'dell-p2426h', 'Office productivity monitor.', 5, 4, 4, '{"panel":"IPS","refresh_rate":"75Hz","resolution":"1920x1080","size":"24"}', 1),
(59, 'JBL Tune Beam 3', 'jbl-tune-beam-3', 'True wireless earbuds.', 6, 11, 5, '{"connectivity":"Bluetooth 5.3","battery":"32h"}', 1),
(60, 'Anker 100W USB-C Cable', 'anker-100w-usbc-cable', 'Durable charging cable.', 7, 19, 7, '{"compatibility":"USB-C 100W"}', 1)
) AS seed(id, name, slug, description, category_id, brand_id, product_type_id, attributes, is_active_int);

-- =========================
-- VARIANTS (1-2 mỗi sản phẩm)
-- =========================
INSERT INTO variants (id, product_id, sku, price, stock, attributes, cover_image_url, is_active)
SELECT id, product_id, sku, price, stock, attributes::jsonb, cover_image_url, (is_active_int <> 0)
FROM (VALUES
(1, 1, 'DL-XPS13-16-512-SLV', 38990000, 30, '{"color":"Silver"}', NULL, 1),
(2, 1, 'DL-XPS13-32-1T-BLK', 45990000, 18, '{"color":"Black"}', NULL, 1),
(3, 2, 'HP-SPX14-16-1T-BLU', 42990000, 20, '{"color":"Blue"}', NULL, 1),
(4, 3, 'LN-X1C13-32-1T-BLK', 49990000, 15, '{"color":"Black"}', NULL, 1),
(5, 4, 'AS-ZB14-16-512-GRY', 29990000, 40, '{"color":"Grey"}', NULL, 1),
(6, 5, 'AC-SWG14-16-512-GRN', 23990000, 35, '{"color":"Green"}', NULL, 1),
(7, 6, 'MS-ST16-32-1T-BLK', 58990000, 10, '{"color":"Black"}', NULL, 1),
(8, 7, 'AP-IP17P-256-TIT', 36990000, 50, '{"color":"Titanium"}', NULL, 1),
(9, 7, 'AP-IP17P-512-BLK', 41990000, 35, '{"color":"Black"}', NULL, 1),
(10, 8, 'AP-IP17-128-BLU', 23990000, 60, '{"color":"Blue"}', NULL, 1),
(11, 9, 'SS-S26U-256-TIT', 33990000, 40, '{"color":"Titanium"}', NULL, 1),
(12, 10, 'SS-A76-256-WHT', 10990000, 80, '{"color":"White"}', NULL, 1),
(13, 11, 'XM-16P-512-BLK', 18990000, 70, '{"color":"Black"}', NULL, 1),
(14, 12, 'XM-RN16-256-GRN', 7990000, 120, '{"color":"Green"}', NULL, 1),
(15, 13, 'AP-IPD13M5-512-SLV', 37990000, 25, '{"color":"Silver"}', NULL, 1),
(16, 14, 'AP-IPA11M4-256-BLU', 19990000, 40, '{"color":"Blue"}', NULL, 1),
(17, 15, 'SS-TS11P-256-GRY', 22990000, 30, '{"color":"Grey"}', NULL, 1),
(18, 16, 'XM-PAD8P-256-BLK', 12990000, 45, '{"color":"Black"}', NULL, 1),
(19, 17, 'LG-UG27-2K-180', 7490000, 55, '{"color":"Black"}', NULL, 1),
(20, 18, 'SS-ODG8-32-4K', 19990000, 20, '{"color":"Black"}', NULL, 1),
(21, 19, 'DL-U2726Q-4K', 12990000, 25, '{"color":"Black"}', NULL, 1),
(22, 20, 'AS-PA279-4K', 14990000, 22, '{"color":"Black"}', NULL, 1),
(23, 21, 'SY-XM7-BLK', 9990000, 65, '{"color":"Black"}', NULL, 1),
(24, 22, 'AP-APP3-WHT', 6490000, 85, '{"color":"White"}', NULL, 1),
(25, 23, 'JBL-CH7-BLK', 4290000, 90, '{"color":"Black"}', NULL, 1),
(26, 24, 'SS-GBP4P-WHT', 4990000, 70, '{"color":"White"}', NULL, 1),
(27, 25, 'LG-MXM4-BLK', 2990000, 120, '{"color":"Black"}', NULL, 1),
(28, 26, 'LG-MXKS-BLK', 3490000, 100, '{"color":"Black"}', NULL, 1),
(29, 27, 'AK-737-24K-BLK', 2890000, 110, '{"capacity":"24000mAh"}', NULL, 1),
(30, 28, 'AK-140W-CHG-BLK', 1790000, 130, '{"color":"Black"}', NULL, 1),
(31, 29, 'AP-MGS2-WHT', 1290000, 150, '{"color":"White"}', NULL, 1),
(32, 30, 'SS-45W-PPS-BLK', 990000, 200, '{"color":"Black"}', NULL, 1),
(33, 31, 'RZ-BWV5-BLK', 4590000, 40, '{"switch":"Green"}', NULL, 1),
(34, 32, 'RZ-DAV4P-BLK', 3290000, 50, '{"dpi":"30000"}', NULL, 1),
(35, 33, 'SY-PS6-1TB-WHT', 16990000, 18, '{"storage":"1TB"}', NULL, 1),
(36, 34, 'AS-ROGA2-1TB-BLK', 22990000, 16, '{"storage":"1TB"}', NULL, 1),
(37, 35, 'XM-CAM4K-WHT', 1990000, 95, '{"resolution":"4K"}', NULL, 1),
(38, 36, 'PH-HUEB3-WHT', 1790000, 80, '{"connectivity":"Zigbee"}', NULL, 1),
(39, 37, 'SS-STH26-BLK', 2490000, 70, '{"connectivity":"Thread"}', NULL, 1),
(40, 38, 'TP-TDBX-BLK', 2190000, 85, '{"resolution":"2K"}', NULL, 1),
(41, 39, 'CN-R8M2-BODY', 42990000, 12, '{"kit":"Body"}', NULL, 1),
(42, 40, 'NK-Z63-BODY', 51990000, 10, '{"kit":"Body"}', NULL, 1),
(43, 41, 'SY-A7V-BODY', 56990000, 8, '{"kit":"Body"}', NULL, 1),
(44, 42, 'CN-RF2470-F28', 52990000, 14, '{"mount":"RF"}', NULL, 1),
(45, 43, 'AP-AW12-45-BLK', 12990000, 40, '{"size":"45mm"}', NULL, 1),
(46, 44, 'SS-GW9-46-SLV', 8990000, 55, '{"size":"46mm"}', NULL, 1),
(47, 45, 'GR-FR975-BLK', 14990000, 28, '{"size":"47mm"}', NULL, 1),
(48, 46, 'XM-SB10-BLK', 1190000, 160, '{"size":"Standard"}', NULL, 1),
(49, 47, 'TP-AXE5400-BLK', 3890000, 60, '{"wifi":"6E"}', NULL, 1),
(50, 48, 'TP-BE65-2PK-WHT', 7990000, 42, '{"pack":"2"}', NULL, 1),
(51, 49, 'AS-BE88U-BLK', 9990000, 25, '{"wifi":"7"}', NULL, 1),
(52, 50, 'XM-BE7000-WHT', 3590000, 58, '{"wifi":"7"}', NULL, 1),
(53, 51, 'PH-AFXL-5000-BLK', 4990000, 75, '{"capacity":"7.3L"}', NULL, 1),
(54, 52, 'XM-AP6-WHT', 3990000, 68, '{"coverage":"60m2"}', NULL, 1),
(55, 53, 'LG-CZA12-GRY', 7990000, 35, '{"battery":"60min"}', NULL, 1),
(56, 54, 'SS-MW30L-BLK', 4590000, 40, '{"capacity":"30L"}', NULL, 1),
(57, 55, 'PH-RVR700-BLK', 8990000, 22, '{"battery":"180min"}', NULL, 1),
(58, 56, 'LN-LG7IP-32-2T', 65990000, 9, '{"gpu":"RTX 5090"}', NULL, 1),
(59, 57, 'AS-RP10-512-BLK', 27990000, 18, '{"color":"Black"}', NULL, 1),
(60, 58, 'DL-P2426H-FHD', 3990000, 85, '{"resolution":"1920x1080"}', NULL, 1),
(61, 59, 'JBL-TB3-WHT', 1290000, 140, '{"color":"White"}', NULL, 1),
(62, 60, 'AK-CBL100W-2M', 390000, 300, '{"length":"2m"}', NULL, 1)
) AS seed(id, product_id, sku, price, stock, attributes, cover_image_url, is_active_int);

COMMIT;
