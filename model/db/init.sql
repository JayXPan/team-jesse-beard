CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    email_verified VARCHAR(255) NOT NULL,
    verification_token VARCHAR(255),
    hashed_token VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS posts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255),
    title VARCHAR(255),
    description VARCHAR(255),
    image VARCHAR(255),
    starting_price DECIMAL(10, 2),
    current_bid DECIMAL(10, 2),
    current_bidder VARCHAR(255) DEFAULT NULL,
    winner VARCHAR(255) DEFAULT NULL,
    winning_bid DECIMAL(10, 2) DEFAULT NULL,
    duration INT,
    end_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS post_likes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    post_id INT,
    user_id INT,
    FOREIGN KEY (post_id) REFERENCES posts(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);