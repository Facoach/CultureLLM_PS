from mariadb import connect, Connection, Error
from os import getenv


class DatabaseConnection:
    """
    Classe per gestire la configurazione del connection pool per MariaDB.
    Fornisce metodi per inizializzare, ottenere e chiudere connessioni da esso.
    """
    def __init__(self, host=None, port=None, user=None, password=None, database=None, pool_size=None, pool_name=None) -> None:
        """
        Inizializza i parametri di connessione e la configurazione del pool, 
        i valori vengono presi dalle variabili d'ambiente se non forniti esplicitamente
        """
        self.host = host or getenv("MYSQL_HOST", "mariadb-cinema")
        self.port = int(port or getenv("MYSQL_PORT", 3306))
        self.user = user or getenv("MYSQL_USER", "root")
        self.password = password or getenv("MYSQL_PASSWORD", "root")
        self.database = database or getenv("MYSQL_DATABASE", "cinema_db")
        self.pool_size = int(pool_size or getenv("MYSQL_POOL_SIZE", 10))
        self.pool_name = pool_name or getenv("MYSQL_POOL_NAME", "CultureAppMariaDBPool")
        self._is_pool_initialized = False


    def __str__(self) -> str:
        """
        Restituisce una rappresentazione leggibile della configurazione.
        """
        return (f"Host:{self.host}, Porta:{self.port}, Utente:{self.user}, "
                f"Database:{self.database}, PoolSize:{self.pool_size}, PoolName:{self.pool_name}")


    def connect(self) -> None:
        """
        Inizializza il pool di connessioni MariaDB se non già presente.
        Una connessione temporanea viene creata e rilasciata immediatamente
        per attivare la creazione del pool.
        """
        if not self._is_pool_initialized:
            try:
                temp_conn = connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                    pool_size=self.pool_size,
                    pool_name=self.pool_name
                )
                temp_conn.close()
                self._is_pool_initialized = True
                print(f"DEBUG_POOL: Connection pool '{self.pool_name}' a MariaDB inizializzato con dimensione massima {self.pool_size}.")
            except Error as e:
                print(f"Errore durante l'inizializzazione del connection pool a MariaDB: {e}")
                raise


    def get_connection(self) -> Connection:
        """
        Funzione che restituisce una connessione dal pool (già inizializzato).
        """
        
        # Dovrebbe essere un caso raro se connect() viene chiamata allo startup 
        if not self._is_pool_initialized:
            self.connect()

        try:
            conn = connect(pool_name=self.pool_name)
            return conn
        except Error as e:
            print(f"Errore durante l'ottenimento di una connessione dal pool '{self.pool_name}': {e}")
            raise


    def close_pool(self) -> None:
        """
        Segnala la chiusura del pool resettando il flag.
        """
        self._is_pool_initialized = False
        print(f"DEBUG_POOL: Segnalazione di chiusura per il pool '{self.pool_name}'. "
              "Le connessioni saranno rilasciate automaticamente dal driver.")
