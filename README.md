Per eseguire il progetto, prima scaricarlo in una cartella

Se sulla macchina non è installato docker-compose, su Linux installarlo con 
 - pip install docker
 - pip install docker-compose

mentre su Windows è compreso in Docker Desktop, per installarlo seguire la guida ufficiale sul sito


Dopodichè, per l'esecuzione del progetto, aprire il terminale, ed eseguire
 - cd <percorso_verso_la_cartella>
 - mkdir ollama_data
 - mkdir mariadb_data
 - docker-compose up --build -d (Al primo avvio può essere richiesto fino a 1 o 2 minuti)

L'applicazione sarà accessibile tramite browser dalla pagina http://localhost:8001.

Per la chiusura, eseguire sempre nel terminale della stessa directory
 - docker-compose down

Per riavviarlo, eseguire di nuovo, all'apertura del terminale
 - cd <percorso_verso_la_cartella>
 - docker-compose up --build -d (Gli avvii successivi saranno molto più veloci )