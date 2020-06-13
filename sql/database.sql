CREATE DATABASE progetto_tesina;

USE progetto_tesina;

CREATE TABLE users (
    IDUser int PRIMARY KEY AUTO_INCREMENT,
    username varchar(255),
    password varchar(255)
);
