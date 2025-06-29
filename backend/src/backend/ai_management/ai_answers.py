import requests
import mariadb
import threading
from classes.database_connection import DatabaseConnection
from database_management.execute_query import execute_query_modify, execute_query_ask

MODEL_NAME = "gemma3:1b" 
OLLAMA_URL = "http://ollama:11434/api"
lista_livelli =["rispondi come risponderebbe uno studente di scuola media alla domanda:", "rispondi come risponderebbe uno studente di scuola superiore alla domanda:", "rispondi come risponderebbe un adulto alla domanda:"]

def process_ai_response(question_payload: str,  db_pool_manager : DatabaseConnection):
    """
    Funzione eseguita da un thread separato per interagire con Ollama
    e salvare la risposta nel database.
    """
    thread_name = threading.current_thread().name # Ottieni il nome del thread per i log
    print(f"[{thread_name}] Avvio elaborazione Ollama")

    for i in range(3):
        try:
            # Acquisisce una connessione dal pool specificamente per questo thread
            # Il db_pool_manager_instance è l'oggetto passato dal main thread
            conn = db_pool_manager.get_connection() 
            print(f"[{thread_name}] Connessione DB acquisita dal pool per la task {i}.")

            data={"model": MODEL_NAME, "messages":[{"role":"user", "content":f"{lista_livelli[0]} '{question_payload}'. Non superare i 250 caratteri (spazi inclusi) e restituisci unicamente la risposta"}], "stream":False}
            response= requests.post(f"{OLLAMA_URL}/chat", json=data)
            response.raise_for_status()
            ollama_response = response.json().get("message", "").get("content", "")
            print(ollama_response)
            iddomanda= execute_query_ask(conn, f'select id from questions where payload=%s;', [question_payload])
            execute_query_modify(conn, f'insert into answers (payload,question,author) values (%s, %s, %s);', [ollama_response, iddomanda[1][0], -1])
        except requests.exceptions.RequestException as e:
            print(f"[{thread_name}] Errore durante la richiesta all'ia nella task {i}: {e}")
        except mariadb.Error as e:
            print(f"[{thread_name}] Errore DB durante il salvataggio della risposta ia nella task {i}: {e}")
            # Gestisci l'errore DB nel thread
        except Exception as e:
            print(f"[{thread_name}] Errore inatteso nel thread ia nella task {i}: {e}")
        finally:
            if conn:
                conn.close() # Rilascia la connessione al pool
                print(f"[{thread_name}] Connessione DB rilasciata dal pool per la task {i}.")
