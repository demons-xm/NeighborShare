CREATE TABLE admins (
    id INT NOT NULL AUTO_INCREMENT,
    create_time DATETIME NOT NULL,
    update_time DATETIME NOT NULL,
    username VARCHAR(50) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (id),
    CONSTRAINT uq_admins_username UNIQUE (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
