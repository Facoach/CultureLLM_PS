import requests
import mariadb
import threading
from classes.database_connection import DatabaseConnection
from database_management.execute_query import execute_query_modify, execute_query_ask


MODEL_NAME = "gemma3:1b" 
OLLAMA_URL = "http://ollama:11434/api"
lista_livelli =["rispondi come risponderebbe uno studente di scuola media alla domanda:", "rispondi come risponderebbe uno studente di scuola superiore alla domanda:", "rispondi come risponderebbe un adulto alla domanda:"]


def process_ai_response(question_payload: str,  db_pool_manager : DatabaseConnection) -> None:
    """
    Funzione edeguita da un thread separato per non bloccare il main thread,
    interagisce con il modello di IA (Ollama) mandando una richiesta per ogni 
    livello in 'lista_livelli' e salva le risposte nel database.
    """
    thread_name = threading.current_thread().name
    print(f"[{thread_name}] Avvio elaborazione Ollama")

    for i in range(3):
        try:
            # Acquisisce una connessione dal pool specificamente per questo thread e passa i dati ad Ollama
            conn = db_pool_manager.get_connection() 
            print(f"[{thread_name}] Connessione DB acquisita dal pool per la task {i}.")

            data={
                "model": MODEL_NAME,
                "messages":[{
                    "role":"user", 
                    "content":f"{lista_livelli[i]} '{question_payload}'. Non superare i 250 caratteri (spazi inclusi) e restituisci unicamente la risposta"
                }], 
                "stream":False
            }
            # Invia la richiesta ed estrare la risposta
            response = requests.post(f"{OLLAMA_URL}/chat", json=data)
            response.raise_for_status()
            ollama_response = response.json().get("message", "").get("content", "")
            print(ollama_response)

            # Trova l'id della domanda nel db ed inserisce la risposta nel db
            iddomanda= execute_query_ask(conn, f'select id from questions where payload=%s;', [question_payload])
            transazione = execute_query_modify(conn, 'START TRANSACTION')
            execute_query_modify(conn, f'insert into answers (payload,question,author) values (%s, %s, %s);', [ollama_response[:255], iddomanda[1][0], -1])
            transazione = execute_query_modify(conn, 'COMMIT')

        except requests.exceptions.RequestException as e:
            print(f"[{thread_name}] Errore durante la richiesta all'ia nella task {i}: {e}")
        except mariadb.Error as e:
            print(f"[{thread_name}] Errore DB durante il salvataggio della risposta ia nella task {i}: {e}")
        except Exception as e:
            print(f"[{thread_name}] Errore inatteso nel thread ia nella task {i}: {e}")
        finally:
            if conn:
                conn.close()
                print(f"[{thread_name}] Connessione DB rilasciata dal pool per la task {i}.")
