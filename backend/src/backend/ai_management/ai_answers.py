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

            data={
                "argomento": question_payload,
                "livello" : i+1
            }
            # Invia la richiesta ed estrare la risposta
            response = requests.post(f"http://ai_response:8073/answer", json=data)
            response.raise_for_status()
            ai_response = response.json()
            actual_answer=ai_response["risposta"]
            print(actual_answer)

            data={
                "llm_response": actual_answer,
                "level" : 3
            }

            response = requests.post(f"http://ai_humanization:8074/humanize", json=data)
            response.raise_for_status()
            ai_response = response.json()
            humanized_answer=ai_response["humanized_response"]
            print(humanized_answer)

            # Acquisisce una connessione dal pool specificamente per questo thread
            conn = db_pool_manager.get_connection() 
            print(f"[{thread_name}] Connessione DB acquisita dal pool per la task {i}.")

            # Trova l'id della domanda nel db ed inserisce la risposta nel db
            iddomanda= execute_query_ask(conn, f'select id from questions where payload=%s;', [question_payload])
            transazione = execute_query_modify(conn, 'START TRANSACTION')
            execute_query_modify(conn, f'insert into answers (payload,question,author) values (%s, %s, %s);', [humanized_answer[:511], iddomanda[1][0], -1])
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
