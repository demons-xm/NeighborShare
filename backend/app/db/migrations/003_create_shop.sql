CREATE TABLE shop (
    id INT NOT NULL,
    create_time DATETIME NOT NULL,
    update_time DATETIME NOT NULL,
    shop_name VARCHAR(100) NOT NULL DEFAULT '外卖店铺',
    logo_url VARCHAR(500) NULL,
    description TEXT NOT NULL,
    business_hours VARCHAR(100) NOT NULL DEFAULT '09:00-21:00',
    delivery_range VARCHAR(255) NOT NULL,
    minimum_order_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    delivery_fee DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    is_open BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (id),
    CONSTRAINT ck_shop_singleton CHECK (id = 1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO shop (
    id,
    create_time,
    update_time,
    shop_name,
    description,
    delivery_range
) VALUES (
    1,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    '外卖店铺',
    '',
    ''
);
