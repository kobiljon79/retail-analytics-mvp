-- ============================================================
-- Retail Analytics MVP — Database Schema
-- ============================================================

CREATE TABLE products (
    product_id      SERIAL PRIMARY KEY,
    product_name    VARCHAR(100) NOT NULL,
    category        VARCHAR(50),
    unit_price      NUMERIC(10, 2) NOT NULL,
    reorder_level   INTEGER NOT NULL DEFAULT 10
);

CREATE TABLE branches (
    branch_id       SERIAL PRIMARY KEY,
    branch_name     VARCHAR(100) NOT NULL,
    city            VARCHAR(100)
);

CREATE TABLE inventory (
    inventory_id    SERIAL PRIMARY KEY,
    product_id      INTEGER REFERENCES products(product_id),
    branch_id       INTEGER REFERENCES branches(branch_id),
    stock_quantity  INTEGER NOT NULL DEFAULT 0,
    last_updated    DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE TABLE sales (
    sale_id         SERIAL PRIMARY KEY,
    product_id      INTEGER REFERENCES products(product_id),
    branch_id       INTEGER REFERENCES branches(branch_id),
    quantity_sold   INTEGER NOT NULL,
    sale_date       DATE NOT NULL,
    total_amount    NUMERIC(10, 2) NOT NULL
);

CREATE TABLE shrinkage (
    shrinkage_id    SERIAL PRIMARY KEY,
    product_id      INTEGER REFERENCES products(product_id),
    branch_id       INTEGER REFERENCES branches(branch_id),
    quantity_lost   INTEGER NOT NULL,
    reason          VARCHAR(100),
    report_date     DATE NOT NULL
);

-- ============================================================
-- Sample data
-- ============================================================

INSERT INTO branches (branch_name, city) VALUES
('Downtown Store', 'New York'),
('Westside Mall', 'Los Angeles'),
('North Branch', 'Chicago');

INSERT INTO products (product_name, category, unit_price, reorder_level) VALUES
('Coca Cola 1.5L', 'Beverages', 2.50, 20),
('Pepsi 1.5L', 'Beverages', 2.40, 20),
('White Bread', 'Bakery', 1.80, 15),
('Milk 1L', 'Dairy', 1.20, 30),
('Cheddar Cheese 200g', 'Dairy', 3.50, 10),
('Bananas (kg)', 'Produce', 0.90, 25),
('Apples (kg)', 'Produce', 1.50, 25),
('Eggs (12 pack)', 'Dairy', 2.80, 15),
('Rice 5kg', 'Grains', 6.00, 10),
('Pasta 500g', 'Grains', 1.30, 20);

-- Inventory: deliberately include out-of-stock and overstocked items
INSERT INTO inventory (product_id, branch_id, stock_quantity) VALUES
(1, 1, 5),    -- Coca Cola, Downtown — below reorder level (out of stock soon)
(1, 2, 60),   -- Coca Cola, Westside — overstocked
(2, 1, 0),    -- Pepsi, Downtown — out of stock
(2, 2, 25),
(3, 1, 8),    -- White Bread, Downtown — below reorder level
(3, 3, 40),   -- White Bread, North — overstocked
(4, 1, 50),
(4, 2, 5),    -- Milk, Westside — below reorder level
(5, 1, 12),
(5, 3, 35),   -- Cheddar — overstocked
(6, 1, 30),
(6, 2, 0),    -- Bananas, Westside — out of stock
(7, 1, 28),
(8, 2, 6),    -- Eggs, Westside — below reorder level
(9, 1, 45),   -- Rice — overstocked
(10, 3, 22);

-- Sales: some for "yesterday" relative to CURRENT_DATE, some older
INSERT INTO sales (product_id, branch_id, quantity_sold, sale_date, total_amount) VALUES
(1, 1, 10, CURRENT_DATE - INTERVAL '1 day', 25.00),
(2, 1, 8,  CURRENT_DATE - INTERVAL '1 day', 19.20),
(3, 1, 12, CURRENT_DATE - INTERVAL '1 day', 21.60),
(4, 2, 20, CURRENT_DATE - INTERVAL '1 day', 24.00),
(5, 3, 6,  CURRENT_DATE - INTERVAL '1 day', 21.00),
(1, 2, 15, CURRENT_DATE - INTERVAL '2 day', 37.50),
(6, 1, 25, CURRENT_DATE - INTERVAL '1 day', 22.50),
(7, 1, 10, CURRENT_DATE - INTERVAL '3 day', 15.00),
(9, 1, 5,  CURRENT_DATE - INTERVAL '1 day', 30.00),
(10, 3, 18, CURRENT_DATE - INTERVAL '1 day', 23.40);

-- Shrinkage: North Branch has the highest shrinkage for the demo
INSERT INTO shrinkage (product_id, branch_id, quantity_lost, reason, report_date) VALUES
(3, 3, 12, 'Expired', CURRENT_DATE - INTERVAL '2 day'),
(5, 3, 8,  'Damaged', CURRENT_DATE - INTERVAL '3 day'),
(10, 3, 15, 'Theft', CURRENT_DATE - INTERVAL '1 day'),
(1, 1, 2,  'Damaged', CURRENT_DATE - INTERVAL '5 day'),
(6, 2, 3,  'Expired', CURRENT_DATE - INTERVAL '4 day');
