CREATE TABLE coupons (
    id INT NOT NULL AUTO_INCREMENT,
    create_time DATETIME NOT NULL,
    update_time DATETIME NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT NULL,
    discount_amount DECIMAL(10, 2) NOT NULL,
    minimum_order_amount DECIMAL(10, 2) NOT NULL DEFAULT 0,
    total_quantity INT NOT NULL,
    claimed_quantity INT NOT NULL DEFAULT 0,
    per_user_limit INT NOT NULL DEFAULT 1,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (id),
    KEY ix_coupons_start_time (start_time),
    KEY ix_coupons_end_time (end_time),
    CONSTRAINT ck_coupons_discount_positive CHECK (discount_amount > 0),
    CONSTRAINT ck_coupons_minimum_nonnegative CHECK (minimum_order_amount >= 0),
    CONSTRAINT ck_coupons_total_positive CHECK (total_quantity > 0),
    CONSTRAINT ck_coupons_claimed_nonnegative CHECK (claimed_quantity >= 0),
    CONSTRAINT ck_coupons_claimed_within_total CHECK (claimed_quantity <= total_quantity),
    CONSTRAINT ck_coupons_user_limit_positive CHECK (per_user_limit > 0),
    CONSTRAINT ck_coupons_time_range CHECK (end_time > start_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE user_coupons (
    id INT NOT NULL AUTO_INCREMENT,
    create_time DATETIME NOT NULL,
    update_time DATETIME NOT NULL,
    user_id INT NOT NULL,
    coupon_id INT NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'available',
    claimed_at DATETIME NOT NULL,
    redeemed_at DATETIME NULL,
    PRIMARY KEY (id),
    KEY ix_user_coupons_user_id (user_id),
    KEY ix_user_coupons_coupon_id (coupon_id),
    KEY ix_user_coupons_user_coupon (user_id, coupon_id),
    CONSTRAINT ck_user_coupons_status CHECK (status IN ('available', 'used')),
    CONSTRAINT fk_user_coupons_user_id_users
        FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE CASCADE,
    CONSTRAINT fk_user_coupons_coupon_id_coupons
        FOREIGN KEY (coupon_id) REFERENCES coupons (id)
        ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE seckill_activities (
    id INT NOT NULL AUTO_INCREMENT,
    create_time DATETIME NOT NULL,
    update_time DATETIME NOT NULL,
    name VARCHAR(100) NOT NULL,
    dish_id INT NOT NULL,
    sale_price DECIMAL(10, 2) NOT NULL,
    stock INT NOT NULL,
    sold_count INT NOT NULL DEFAULT 0,
    limit_per_user INT NOT NULL DEFAULT 1,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (id),
    KEY ix_seckill_activities_dish_id (dish_id),
    KEY ix_seckill_activities_start_time (start_time),
    KEY ix_seckill_activities_end_time (end_time),
    CONSTRAINT ck_seckill_sale_price_nonnegative CHECK (sale_price >= 0),
    CONSTRAINT ck_seckill_stock_positive CHECK (stock > 0),
    CONSTRAINT ck_seckill_sold_nonnegative CHECK (sold_count >= 0),
    CONSTRAINT ck_seckill_sold_within_stock CHECK (sold_count <= stock),
    CONSTRAINT ck_seckill_user_limit_positive CHECK (limit_per_user > 0),
    CONSTRAINT ck_seckill_time_range CHECK (end_time > start_time),
    CONSTRAINT fk_seckill_activities_dish_id_dishes
        FOREIGN KEY (dish_id) REFERENCES dishes (id)
        ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE orders
    ADD COLUMN source VARCHAR(16) NOT NULL DEFAULT 'cart',
    ADD COLUMN coupon_id INT NULL,
    ADD COLUMN user_coupon_id INT NULL,
    ADD COLUMN seckill_activity_id INT NULL,
    ADD COLUMN discount_amount DECIMAL(10, 2) NOT NULL DEFAULT 0,
    ADD KEY ix_orders_seckill_activity_id (seckill_activity_id),
    ADD KEY ix_orders_user_seckill_activity (user_id, seckill_activity_id),
    ADD CONSTRAINT ck_orders_source CHECK (source IN ('cart', 'seckill')),
    ADD CONSTRAINT ck_orders_discount_nonnegative CHECK (discount_amount >= 0),
    ADD CONSTRAINT fk_orders_coupon_id_coupons
        FOREIGN KEY (coupon_id) REFERENCES coupons (id)
        ON DELETE SET NULL,
    ADD CONSTRAINT fk_orders_user_coupon_id_user_coupons
        FOREIGN KEY (user_coupon_id) REFERENCES user_coupons (id)
        ON DELETE SET NULL,
    ADD CONSTRAINT fk_orders_seckill_activity_id_activities
        FOREIGN KEY (seckill_activity_id) REFERENCES seckill_activities (id)
        ON DELETE SET NULL;
