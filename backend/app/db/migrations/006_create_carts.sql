CREATE TABLE carts (
    id INT NOT NULL AUTO_INCREMENT,
    create_time DATETIME NOT NULL,
    update_time DATETIME NOT NULL,
    user_id INT NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_carts_user_id UNIQUE (user_id),
    CONSTRAINT fk_carts_user_id_users
        FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE cart_items (
    id INT NOT NULL AUTO_INCREMENT,
    create_time DATETIME NOT NULL,
    update_time DATETIME NOT NULL,
    cart_id INT NOT NULL,
    dish_id INT NOT NULL,
    quantity INT NOT NULL,
    PRIMARY KEY (id),
    KEY ix_cart_items_cart_id (cart_id),
    CONSTRAINT uq_cart_items_cart_dish UNIQUE (cart_id, dish_id),
    CONSTRAINT ck_cart_items_quantity_positive CHECK (quantity > 0),
    CONSTRAINT fk_cart_items_cart_id_carts
        FOREIGN KEY (cart_id) REFERENCES carts (id)
        ON DELETE CASCADE,
    CONSTRAINT fk_cart_items_dish_id_dishes
        FOREIGN KEY (dish_id) REFERENCES dishes (id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
