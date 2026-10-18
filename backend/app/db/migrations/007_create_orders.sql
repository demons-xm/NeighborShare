CREATE TABLE orders (
    id INT NOT NULL AUTO_INCREMENT,
    create_time DATETIME NOT NULL,
    update_time DATETIME NOT NULL,
    order_no VARCHAR(32) NOT NULL,
    user_id INT NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'pending_payment',
    recipient_name VARCHAR(50) NOT NULL,
    recipient_phone VARCHAR(11) NOT NULL,
    province VARCHAR(50) NOT NULL,
    city VARCHAR(50) NOT NULL,
    district VARCHAR(50) NOT NULL,
    address_detail VARCHAR(255) NOT NULL,
    dish_amount DECIMAL(10, 2) NOT NULL,
    delivery_fee DECIMAL(10, 2) NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_orders_order_no (order_no),
    KEY ix_orders_user_id (user_id),
    KEY ix_orders_status (status),
    CONSTRAINT fk_orders_user_id_users
        FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE order_items (
    id INT NOT NULL AUTO_INCREMENT,
    create_time DATETIME NOT NULL,
    update_time DATETIME NOT NULL,
    order_id INT NOT NULL,
    dish_id INT NULL,
    dish_name VARCHAR(100) NOT NULL,
    dish_image_url VARCHAR(500) NULL,
    category_name VARCHAR(50) NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    quantity INT NOT NULL,
    subtotal DECIMAL(10, 2) NOT NULL,
    PRIMARY KEY (id),
    KEY ix_order_items_order_id (order_id),
    KEY ix_order_items_dish_id (dish_id),
    CONSTRAINT ck_order_items_quantity_positive CHECK (quantity > 0),
    CONSTRAINT fk_order_items_order_id_orders
        FOREIGN KEY (order_id) REFERENCES orders (id)
        ON DELETE CASCADE,
    CONSTRAINT fk_order_items_dish_id_dishes
        FOREIGN KEY (dish_id) REFERENCES dishes (id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
