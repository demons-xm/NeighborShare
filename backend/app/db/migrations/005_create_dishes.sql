CREATE TABLE dishes (
    id INT NOT NULL AUTO_INCREMENT,
    create_time DATETIME NOT NULL,
    update_time DATETIME NOT NULL,
    category_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    image_url VARCHAR(500) NULL,
    price DECIMAL(10, 2) NOT NULL,
    stock INT NOT NULL DEFAULT 0,
    description TEXT NULL,
    is_available BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (id),
    KEY ix_dishes_category_id (category_id),
    CONSTRAINT ck_dishes_price_nonnegative CHECK (price >= 0),
    CONSTRAINT ck_dishes_stock_nonnegative CHECK (stock >= 0),
    CONSTRAINT fk_dishes_category_id_categories
        FOREIGN KEY (category_id) REFERENCES categories (id)
        ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
