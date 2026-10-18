CREATE TABLE categories (
    id INT NOT NULL AUTO_INCREMENT,
    create_time DATETIME NOT NULL,
    update_time DATETIME NOT NULL,
    shop_id INT NOT NULL DEFAULT 1,
    name VARCHAR(50) NOT NULL,
    description TEXT NULL,
    sort_order INT NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    KEY ix_categories_shop_sort_order (shop_id, sort_order),
    CONSTRAINT fk_categories_shop_id_shop
        FOREIGN KEY (shop_id) REFERENCES shop (id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
