from threading import Lock
from mariadb import Error
from fastapi import HTTPException

class DBPoolManager:
    def __init__(self, db_pool_manager) -> None:
        self.db_pool_manager = db_pool_manager
        self._active_connections_count = 0
        self._connections_lock = Lock()

    async def get_db_connection(self):
        """
        Dependency per FastAPI che fornisce una connessione dal pool
        e aggiorna il conteggio delle connessioni attive, mostrando info di debug.
        """
        conn = None
        try:
            conn = self.db_pool_manager.get_connection()
            with self._connections_lock:
                self._active_connections_count += 1
                current_active = self._active_connections_count
            print(f"DEBUG_POOL: Connessione acquisita. Connessioni attive (stimate dall'app): {current_active} / {self.db_pool_manager.pool_size} (Pool Max).")
            yield conn
        except Error as e:
            print(f"Errore durante l'ottenimento della connessione dal pool: {e}")
            raise HTTPException(status_code=500, detail="Impossibile connettersi al database.")
        finally:
            if conn:
                conn.close()
                with self._connections_lock:
                    self._active_connections_count -= 1
                    current_active_after_close = self._active_connections_count
                print(f"DEBUG_POOL: Connessione rilasciata. Connessioni attive (stimate dall'app): {current_active_after_close} / {self.db_pool_manager.pool_size} (Pool Max).")

    def reset_active_count(self) -> None:
        with self._connections_lock:
            self._active_connections_count = 0
        print("DEBUG_POOL: Contatore connessioni attive resettato.")
