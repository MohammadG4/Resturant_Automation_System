-- Create Menu Table
CREATE TABLE IF NOT EXISTS menu (
    id SERIAL PRIMARY KEY,
    item_name VARCHAR(255) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    available BOOLEAN DEFAULT TRUE
);

-- Create Orders Table
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    customer_name VARCHAR(255) NOT NULL,
    customer_phone VARCHAR(50) NOT NULL,
    delivery_address TEXT,
    items JSONB NOT NULL,
    total_price DECIMAL(10, 2) NOT NULL, -- Re-added total_price as your Python code relies on it
    status VARCHAR(50) DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Clear existing data if you are rebuilding (Optional but good for clean slates)
TRUNCATE TABLE menu RESTART IDENTITY CASCADE;

-- Insert the full menu
INSERT INTO menu (item_name, price, available) VALUES
('علبة التحرير', 40.00, TRUE),
('علبة توب', 55.00, TRUE),
('علبة لارج', 65.00, TRUE),
('علبة كينج', 80.00, TRUE),
('فويل ميجا لـ 3 أشخاص', 185.00, TRUE),
('فويل عائلي لـ 5 أشخاص', 300.00, TRUE),
('مهلبية', 30.00, TRUE),
('رز بلبن', 30.00, TRUE),
('كانز كولا', 30.00, TRUE),
('ميرندا برتقال', 20.00, TRUE),
('سفن أب', 20.00, TRUE),
('بيبسي', 20.00, TRUE),
('مياه معدنية', 10.00, TRUE),
('علبة التحرير (سعر معدل)', 48.00, TRUE),
('علبة توب (سعر معدل)', 65.00, TRUE),
('علبة لارج (سعر معدل)', 75.00, TRUE),
('علبة كينج (سعر معدل)', 90.00, TRUE),
('فويل ميجا لـ 3 أشخاص (سعر معدل)', 210.00, TRUE),
('فويل عائلي لـ 5 أشخاص (سعر معدل)', 340.00, TRUE),
('رز بلبن (سعر معدل)', 35.00, TRUE),
('مهلبية (سعر معدل)', 35.00, TRUE),
('كانز كولا (سعر معدل)', 35.00, TRUE),
('بيبسي (سعر معدل)', 25.00, TRUE),
('ميرندا برتقال (سعر معدل)', 25.00, TRUE),
('سفن أب (سعر معدل)', 25.00, TRUE),
('مياه معدنية صغيرة', 15.00, TRUE);