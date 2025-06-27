'''import mariadb
import sys

class DatabaseConnection:
    """
    Classe per gestire la configurazione del connection pool per MariaDB.
    Fornisce metodi per inizializzare il pool e ottenere connessioni da esso.
    """
    def __init__(self, host, port, user, password, database, pool_size=10, pool_name="default_mariadb_pool") -> None:
        """
        Inizializza la configurazione del database e del pool.
        :param host: Indirizzo IP o hostname del database.
        :param port: Porta del database.
        :param user: Utente del database.
        :param password: Password dell'utente.
        :param database: Nome del database.
        :param pool_size: Dimensione massima del connection pool.
        :param pool_name: Nome del pool di connessioni.
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.pool_size = pool_size
        self.pool_name = pool_name
        self._is_pool_initialized = False # Flag per assicurarsi che il pool sia inizializzato una sola volta

    def __str__(self):
        """
        Restituisce una rappresentazione in stringa dell'oggetto di connessione.
        """
        return (f"Host:{self.host}, Porta:{self.port}, Utente:{self.user}, "
                f"Database:{self.database}, PoolSize:{self.pool_size}, PoolName:{self.pool_name}")

    def connect(self) -> None:
        """
        Inizializza il connection pool.
        Viene chiamato all'avvio dell'applicazione per configurare il pool.
        Una connessione temporanea viene creata e rilasciata immediatamente
        per attivare la creazione del pool.
        """
        if not self._is_pool_initialized:
            try:
                # Creiamo una connessione temporanea con i parametri del pool.
                # Questo è il modo in cui il driver mariadb inizializza il pool.
                # Questa connessione viene immediatamente chiusa e restituita al pool.
                temp_conn = mariadb.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                    pool_size=self.pool_size,
                    pool_name=self.pool_name
                )
                temp_conn.close() # Rilascia la connessione iniziale al pool
                self._is_pool_initialized = True
                print(f"Connection pool '{self.pool_name}' a MariaDB inizializzato con dimensione {self.pool_size}.")
            except mariadb.Error as e:
                print(f"Errore durante l'inizializzazione del connection pool a MariaDB: {e}")
                raise

    def get_connection(self):
        """
        Acquisisce una connessione dal connection pool.
        Se il pool non è ancora stato inizializzato, lo inizializza (anche se dovrebbe essere
        chiamato allo startup dell'applicazione).
        :return: Un oggetto connessione di mariadb.
        """
        if not self._is_pool_initialized:
            # Questo caso dovrebbe essere raro se connect() viene chiamato allo startup.
            # È una salvaguardia nel caso in cui la dipendenza provi ad ottenere una connessione
            # prima che l'evento di startup abbia completato l'inizializzazione del pool.
            self.connect()

        try:
            # Ottiene una connessione dal pool esistente usando il pool_name
            conn = mariadb.connect(pool_name=self.pool_name)
            return conn
        except mariadb.Error as e:
            print(f"Errore durante l'ottenimento di una connessione dal pool '{self.pool_name}': {e}")
            raise

    def close_pool(self) -> None:
        """
        Segnala la chiusura del pool.
        Nel driver mariadb, le connessioni nel pool vengono rilasciate
        quando non ci sono più riferimenti a esse, e il pool stesso
        viene pulito dal garbage collector all'uscita del programma.
        Questo metodo è principalmente per segnalare che l'applicazione
        si sta spegnendo e il pool non sarà più usato.
        """
        print(f"Segnalazione di chiusura per il pool '{self.pool_name}'. "
              "Le connessioni saranno rilasciate automaticamente dal driver.")
        self._is_pool_initialized = False # Resetta il flag'''

import mariadb
import sys
# Non è più necessario importare threading qui, lo useremo nel main.py

class DatabaseConnection:
    """
    Classe per gestire la configurazione del connection pool per MariaDB.
    Fornisce metodi per inizializzare il pool e ottenere connessioni da esso.
    La logica di conteggio delle connessioni attive è stata spostata al livello
    dell'applicazione (es. nella dipendenza FastAPI).
    """
    def __init__(self, host, port, user, password, database, pool_size=10, pool_name="default_mariadb_pool") -> None:
        """
        Inizializza la configurazione del database e del pool.
        :param host: Indirizzo IP o hostname del database.
        :param port: Porta del database.
        :param user: Utente del database.
        :param password: Password dell'utente.
        :param database: Nome del database.
        :param pool_size: Dimensione massima del connection pool.
        :param pool_name: Nome del pool di connessioni.
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.pool_size = pool_size
        self.pool_name = pool_name
        self._is_pool_initialized = False # Flag per assicurarsi che il pool sia inizializzato una sola volta

    def __str__(self):
        """
        Restituisce una rappresentazione in stringa dell'oggetto di connessione.
        """
        return (f"Host:{self.host}, Porta:{self.port}, Utente:{self.user}, "
                f"Database:{self.database}, PoolSize:{self.pool_size}, PoolName:{self.pool_name}")

    def connect(self) -> None:
        """
        Inizializza il connection pool.
        Viene chiamato all'avvio dell'applicazione per configurare il pool.
        Una connessione temporanea viene creata e rilasciata immediatamente
        per attivare la creazione del pool.
        """
        # Non usiamo più un lock qui, la gestione del flag è sufficiente
        if not self._is_pool_initialized:
            try:
                temp_conn = mariadb.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                    pool_size=self.pool_size,
                    pool_name=self.pool_name
                )
                temp_conn.close() # Rilascia la connessione iniziale al pool
                self._is_pool_initialized = True
                print(f"DEBUG_POOL: Connection pool '{self.pool_name}' a MariaDB inizializzato con dimensione massima {self.pool_size}.")
            except mariadb.Error as e:
                print(f"Errore durante l'inizializzazione del connection pool a MariaDB: {e}")
                raise

    def get_connection(self):
        """
        Acquisisce una connessione dal connection pool.
        Questa funzione non traccia più il conteggio delle connessioni attive.
        :return: Un oggetto connessione di mariadb.
        """
        if not self._is_pool_initialized:
            # Questo caso dovrebbe essere raro se connect() viene chiamato allo startup.
            self.connect()

        try:
            conn = mariadb.connect(pool_name=self.pool_name)
            # Rimossa la logica di conteggio e di wrapping del close() da qui
            return conn
        except mariadb.Error as e:
            print(f"Errore durante l'ottenimento di una connessione dal pool '{self.pool_name}': {e}")
            raise

    def close_pool(self) -> None:
        """
        Segnala la chiusura del pool.
        Nel driver mariadb, le connessioni nel pool vengono rilasciate
        quando non ci sono più riferimenti a esse, e il pool stesso
        viene pulito dal garbage collector all'uscita del programma.
        Questo metodo è principalmente per segnalare che l'applicazione
        si sta spegnendo e il pool non sarà più usato.
        """
        # Il reset del contatore active_connections_count avverrà in main.py
        self._is_pool_initialized = False # Resetta il flag
        print(f"DEBUG_POOL: Segnalazione di chiusura per il pool '{self.pool_name}'. "
              "Le connessioni saranno rilasciate automaticamente dal driver.")
