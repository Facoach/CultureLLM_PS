from database_management.execute_query import execute_query_modify, execute_query_ask
from .jwt_utils import decode_access_token
from mariadb import Error, Connection
from random import choice
from fastapi import Request, HTTPException


def get_question(user_id: int, theme: str, questionid: int, db_conn: Connection):
    """
    Funzione helper per ottenere una nuova domanda da rispondere.
    Marca la domanda come "in risposta" dall'utente corrente.

    :param user_id: ID dell'utente corrente.
    :param theme: Tema da escludere.
    :param questionid: ID della domanda precedente da escludere.
    :param db_conn: Connessione al database.
    :return: Dettagli della domanda selezionata.
    :raises Error: Se si verifica un errore DB.
    """
    try:
        # Seleziona 10 domande non ancora risposte e non in fase di risposta
        # escludendo quelle dell'autore e il tema e ID specifici.
        ret = execute_query_ask(db_conn, f'SELECT questions.id, payload, theme FROM questions join themes on themes.id=theme_id WHERE author != %s AND is_answering=0 AND answered = 0 AND theme!=%s AND questions.id != %s ORDER BY id ASC LIMIT 10;', [user_id, theme, questionid])
        ret.pop(0) # Rimuove le intestazioni di colonna

        if not ret:
            try:
                # Se non ci sono domande disponibili riceve una lista vuota.
                transazione = execute_query_modify(db_conn, 'START TRANSACTION')
                reset = execute_query_modify(db_conn, f'UPDATE questions SET is_answering=0 WHERE is_answering=%s;', [user_id]) 
                transazione = execute_query_modify(db_conn, 'COMMIT')
            except Error as e:
                transazione = execute_query_modify(db_conn, 'ROLLBACK')
                print(f"Errore DB: {e}")
            return [0,"Non ci sono ulteriori domande a cui rispondere, vai a porne di nuove!", "placeholder"]

        scelta=choice(ret)
        # Inizia una transazione per aggiornare lo stato della domanda
        execute_query_modify(db_conn, 'START TRANSACTION')
        execute_query_modify(db_conn, f'UPDATE questions SET is_answering=0 WHERE is_answering=%s;', [user_id]) # Rilascia eventuali domande precedenti
        execute_query_modify(db_conn, f'UPDATE questions SET is_answering=%s WHERE id=%s;', [user_id, scelta[0]]) # Marca la nuova domanda come "in risposta"
        execute_query_modify(db_conn, 'COMMIT')
    except Error as e:
        execute_query_modify(db_conn, 'ROLLBACK') # Rollback in caso di errore
        print(f"Errore DB in get_question: {e}")
        raise # Rilancia l'eccezione
    return scelta


async def get_current_user_id(request: Request) -> int:
    """
    Dipendenza FastAPI per estrarre l'ID utente dal token di sessione ed autenticare
    l'utente su ogni endpoint protetto.

    :param request: Oggetto Request di FastAPI.
    :return: L'ID utente (come int).
    :raises HTTPException: Se il token di sessione è mancante, non valido o scaduto.
    """
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Non autenticato: token di sessione mancante")

    user_id = decode_access_token(session_token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Non autenticato: token di sessione non valido o scaduto")

    return user_id
