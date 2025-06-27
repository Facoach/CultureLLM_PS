CREATE DATABASE IF NOT EXISTS Culture;
USE Culture


CREATE TABLE IF NOT EXISTS users(
        id int AUTO_INCREMENT,
        username varchar(128) NOT NULL,
        password varchar(128) NOT NULL,
        score int NOT NULL DEFAULT 0,
        PRIMARY KEY(id),
        UNIQUE(username),
        check(score>=0)

);

CREATE TABLE IF NOT EXISTS questions(
        id int AUTO_INCREMENT,
        payload varchar(256) NOT NULL,
        theme varchar(64) DEFAULT NULL,
        answered boolean DEFAULT 0,
        checked boolean DEFAULT 0,
        is_answering boolean DEFAULT 0,
        author int NOT NULL,
        PRIMARY KEY(id),
        FOREIGN KEY (author) REFERENCES users(id)

);

CREATE TABLE IF NOT EXISTS answers(
        id int AUTO_INCREMENT,
        payload varchar(256) NOT NULL,
        question int NOT NULL,
        best boolean DEFAULT 0,
        author int NOT NULL,
        PRIMARY KEY(id),
        FOREIGN KEY (question) REFERENCES questions(id),
        FOREIGN KEY (author) REFERENCES users(id)

);