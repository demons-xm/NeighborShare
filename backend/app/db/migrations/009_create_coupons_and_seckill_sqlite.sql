CREATE TABLE coupons (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    create_time DATETIME NOT NULL,
    update_time DATETIME NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT NULL,
    discount_amount NUMERIC(10, 2) NOT NULL,
    minimum_order_amount NUMERIC(10, 2) NOT NULL DEFAULT 0,
    total_quantity INTEGER NOT NULL,
    claimed_quantity INTEGER NOT NULL DEFAULT 0,
    per_user_limit INTEGER NOT NULL DEFAULT 1,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    CONSTRAINT ck_coupons_discount_positive CHECK (discount_amount > 0),
    CONSTRAINT ck_coupons_minimum_nonnegative CHECK (minimum_order_amount >= 0),
    CONSTRAINT ck_coupons_total_positive CHECK (total_quantity > 0),
    CONSTRAINT ck_coupons_claimed_nonnegative CHECK (claimed_quantity >= 0),
    CONSTRAINT ck_coupons_claimed_within_total CHECK (claimed_quantity <= total_quantity),
    CONSTRAINT ck_coupons_user_limit_positive CHECK (per_user_limit > 0),
    CONSTRAINT ck_coupons_time_range CHECK (end_time > start_time)
);
CREATE INDEX ix_coupons_start_time ON coupons (start_time);
CREATE INDEX ix_coupons_end_time ON coupons (end_time);

CREATE TABLE user_coupons (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    create_time DATETIME NOT NULL,
    update_time DATETIME NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    coupon_id INTEGER NOT NULL REFERENCES coupons (id) ON DELETE RESTRICT,
    status VARCHAR(16) NOT NULL DEFAULT 'available',
    claimed_at DATETIME NOT NULL,
    redeemed_at DATETIME NULL,
    CONSTRAINT ck_user_coupons_status CHECK (status IN ('available', 'used'))
);
CREATE INDEX ix_user_coupons_user_id ON user_coupons (user_id);
CREATE INDEX ix_user_coupons_coupon_id ON user_coupons (coupon_id);
CREATE INDEX ix_user_coupons_user_coupon ON user_coupons (user_id, coupon_id);

CREATE TABLE seckill_activities (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    create_time DATETIME NOT NULL,
    update_time DATETIME NOT NULL,
    name VARCHAR(100) NOT NULL,
    dish_id INTEGER NOT NULL REFERENCES dishes (id) ON DELETE RESTRICT,
    sale_price NUMERIC(10, 2) NOT NULL,
    stock INTEGER NOT NULL,
    sold_count INTEGER NOT NULL DEFAULT 0,
    limit_per_user INTEGER NOT NULL DEFAULT 1,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    CONSTRAINT ck_seckill_sale_price_nonnegative CHECK (sale_price >= 0),
    CONSTRAINT ck_seckill_stock_positive CHECK (stock > 0),
    CONSTRAINT ck_seckill_sold_nonnegative CHECK (sold_count >= 0),
    CONSTRAINT ck_seckill_sold_within_stock CHECK (sold_count <= stock),
    CONSTRAINT ck_seckill_user_limit_positive CHECK (limit_per_user > 0),
    CONSTRAINT ck_seckill_time_range CHECK (end_time > start_time)
);
CREATE INDEX ix_seckill_activities_dish_id ON seckill_activities (dish_id);
CREATE INDEX ix_seckill_activities_start_time ON seckill_activities (start_time);
CREATE INDEX ix_seckill_activities_end_time ON seckill_activities (end_time);

ALTER TABLE orders ADD COLUMN source VARCHAR(16) NOT NULL DEFAULT 'cart'
    CHECK (source IN ('cart', 'seckill'));
ALTER TABLE orders ADD COLUMN coupon_id INTEGER NULL REFERENCES coupons (id) ON DELETE SET NULL;
ALTER TABLE orders ADD COLUMN user_coupon_id INTEGER NULL REFERENCES user_coupons (id) ON DELETE SET NULL;
ALTER TABLE orders ADD COLUMN seckill_activity_id INTEGER NULL REFERENCES seckill_activities (id) ON DELETE SET NULL;
ALTER TABLE orders ADD COLUMN discount_amount NUMERIC(10, 2) NOT NULL DEFAULT 0
    CHECK (discount_amount >= 0);
CREATE INDEX ix_orders_seckill_activity_id ON orders (seckill_activity_id);
CREATE INDEX ix_orders_user_seckill_activity ON orders (user_id, seckill_activity_id);
