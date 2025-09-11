CREATE DATABASE IF NOT EXISTS Culture;
USE Culture

CREATE TABLE IF NOT EXISTS themes(
        id int AUTO_INCREMENT,
        theme varchar(64) NOT NULL,
        PRIMARY KEY(id)

);

CREATE TABLE IF NOT EXISTS achievements(
        id int AUTO_INCREMENT,
        name varchar(64) NOT NULL,
        type varchar(64) NOT NULL,
        threshold int (64) NOT NULL,
        PRIMARY KEY(id)

);

CREATE TABLE IF NOT EXISTS users(
        id int AUTO_INCREMENT,
        username varchar(128) NOT NULL,
        password varchar(256) NOT NULL,
        score int NOT NULL DEFAULT 0,
        friend_code varchar(128) NOT NULL,
        PRIMARY KEY(id),
        UNIQUE(username),
        UNIQUE(friend_code),
        check(score>=0)

);

CREATE TABLE IF NOT EXISTS questions(
        id int AUTO_INCREMENT,
        payload varchar(256) NOT NULL,
        theme_id int NOT NULL,
        answered boolean DEFAULT 0,
        checked boolean DEFAULT 0,
        is_answering boolean DEFAULT 0,
        author int NOT NULL,
        PRIMARY KEY(id),
        UNIQUE(payload),
        FOREIGN KEY (author) REFERENCES users(id),
        FOREIGN KEY (theme_id) REFERENCES themes(id)

);

CREATE TABLE IF NOT EXISTS answers(
        id int AUTO_INCREMENT,
        payload varchar(512) NOT NULL,
        question int NOT NULL,
        best boolean DEFAULT 0,
        author int NOT NULL,
        PRIMARY KEY(id),
        FOREIGN KEY (question) REFERENCES questions(id),
        FOREIGN KEY (author) REFERENCES users(id)

);

CREATE TABLE IF NOT EXISTS reached(
        user int NOT NULL,
        achievement int NOT NULL,
        PRIMARY KEY (user,achievement),
        FOREIGN KEY (user) REFERENCES users(id),
        FOREIGN KEY (achievement) REFERENCES achievements(id)

);


INSERT INTO themes (theme) VALUES
("Arte italiana"),
("Calcio italiano"),
("Cinema italiano"),
("Cucina italiana"),
("Feste e tradizioni italiane"),
("Filosofia italiana"),
("Geografia italiana"),
("Letteratura italiana"),
("Lingua italiana"),
("Moda italiana"),
("Musica italiana"),
("Personaggi famosi italiani"),
("Politica italiana"),
("Religione"),
("Scienza e tecnologia italiana"),
("Sport italiano"),
("Storia italiana");

INSERT INTO users (id, username, password, score, friend_code) VALUES
(-1, "IA", "ia", 0, 1);

INSERT INTO questions (payload, theme_id, author) VALUES
("Quali sono le caratteristiche principali dell'arte rinascimentale italiana?", 1, -1),
("Quale squadra ha vinto più scudetti nella Serie A italiana?", 2, -1),
("Chi è il regista italiano noto per il film 'La dolce vita'?", 3, -1),
("Quali sono gli ingredienti tradizionali della pizza margherita?", 4, -1),
("In quale città italiana si svolge il famoso Carnevale con le maschere?", 5, -1),
("Chi è stato Giordano Bruno e perché è importante nella filosofia italiana?", 6, -1),
("Qual è il vulcano attivo situato vicino a Napoli?", 7, -1),
("Chi ha scritto 'La Divina Commedia'?", 8, -1),
("Qual è la differenza tra l'uso del passato prossimo e dell'imperfetto in italiano?", 9, -1),
("Quali sono le principali città italiane della moda?", 10, -1),
("Chi ha scritto la canzone 'Volare' (Nel blu dipinto di blu)?", 11, -1),
("Chi era Leonardo da Vinci e quali sono le sue invenzioni più famose?", 12, -1),
("Chi è stato il primo presidente della Repubblica Italiana?", 13, -1),
("Qual è la città italiana considerata il centro del cattolicesimo?", 14, -1),
("Chi era Galileo Galilei e quale fu il suo contributo alla scienza?", 15, -1),
("Qual è lo sport più praticato in Italia oltre al calcio?", 16, -1),
("Quale evento segnò l'inizio della Repubblica Italiana?", 17, -1);


INSERT INTO achievements (name, type, threshold) VALUES
("Domandatore novizio", "domande_poste", 10),
("Domandatore abile", "domande_poste", 50),
("Domandatore esperto", "domande_poste", 100),
("Risponditore novizio", "risposte_date", 25),
("Risponditore abile", "risposte_date", 75),
("Risponditore esperto", "risposte_date", 150),
("Amico", "codice_amico", 1),
("Valutatore novizio", "domande_valutate", 10), 
("Valutatore abile", "domande_valutate", 50),
("Valutatore esperto", "domande_valutate", 100),
("Giocatore novizio", "punti", 100),
("Giocatore abile", "punti", 500),
("Giocatore esperto", "punti", 1000);
