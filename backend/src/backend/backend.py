import random
from fastapi import FastAPI, HTTPException, Request, Depends, Response
from typing import Dict, Optional, List
from classes.models import ResponseHuman, RequestLogin, RequestRegister, ResponseLogin, RequestAsk, RequestAnswer, ResponseAsk, ResponseAnswer, ResponseProfile, RequestValidate, ResponseLeaderboard, ResponseValidate, RequestHuman, RequestBest, RequestPassreset
from classes.database_connection import DatabaseConnection
from database_management.execute_query import execute_query_modify, execute_query_ask
from ai_management.ai_answers import process_ai_response 
import requests
import mariadb
import os
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
import threading # Necessario per la gestione del conteggio thread-safe
import sys

# --- Configurazione JWT ---
SECRET_KEY = "d8a3f7c9e1b2a4d6f8e0c2b1a3d5e7f9c1b2a4d6f8e0c2b1a3d5e7f9c1b2a4d6" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 # Durata della sessione in minuti

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Crea un token di accesso JWT.
    :param data: Dati da includere nel token (es. {"sub": user_id}).
    :param expires_delta: Durata del token (opzionale, default ACCESS_TOKEN_EXPIRE_MINUTES).
    :return: Token JWT codificato.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    """
    Decodifica un token di accesso JWT e estrae l'ID utente.
    :param token: Token JWT da decodificare.
    :return: L'ID utente (int) se il token è valido, altrimenti None.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            return None
        return int(user_id) # Assicurati che l'ID utente sia un int
    except JWTError:
        return None # Token non valido o scaduto

# Parametri globali per la connessione al database
HOST_DB = os.getenv("E_HOST_DB", "localhost")
PORT_DB = os.getenv("E_PORT_DB", "3307")
#metterli da os
MODEL_NAME = "gemma3:1b"
OLLAMA_URL = "http://ollama:11434/api"

# Inizializza il gestore del connection pool
# Il pool sarà inizializzato formalmente all'evento 'startup' di FastAPI
db_pool_manager = DatabaseConnection(
    host=HOST_DB,
    port=int(PORT_DB),
    user="root",
    password="root",
    database="Culture",
    pool_size=10, # Dimensione del tuo pool di connessioni
    pool_name="CultureAppMariaDBPool" # Nome unico per il tuo pool
)

# --- Variabili globali per il conteggio delle connessioni attive ---
_active_connections_count = 0
_connections_lock = threading.Lock()

# --- Dipendenza per ottenere una connessione dal pool ---
async def get_db_connection():
    """
    FastAPI Dependency che fornisce una connessione al database dal pool.
    La connessione viene acquisita prima della richiesta e rilasciata al pool
    alla fine della richiesta. Include la logica di conteggio per il debugging.
    """
    global _active_connections_count # Dichiarazione global spostata all'inizio della funzione

    conn = None
    try:
        conn = db_pool_manager.get_connection()
        
        # Incrementa il contatore delle connessioni attive
        with _connections_lock:
            _active_connections_count += 1
            current_active = _active_connections_count
        print(f"DEBUG_POOL: Connessione acquisita. Connessioni attive (stimate dall'app): {current_active} / {db_pool_manager.pool_size} (Pool Max).")

        yield conn # Rende la connessione disponibile all'endpoint
    except mariadb.Error as e:
        print(f"Errore durante l'ottenimento della connessione dal pool: {e}")
        raise HTTPException(status_code=500, detail="Impossibile connettersi al database.")
    finally:
        if conn:
            # Rilascia la connessione al pool. Non chiude la connessione fisicamente.
            conn.close()
            # Decrementa il contatore delle connessioni attive
            with _connections_lock:
                _active_connections_count -= 1
                current_active_after_close = _active_connections_count
            print(f"DEBUG_POOL: Connessione rilasciata. Connessioni attive (stimate dall'app): {current_active_after_close} / {db_pool_manager.pool_size} (Pool Max).")


# Creazione dell'applicazione FastAPI
app = FastAPI()

# --- Dipendenza per l'utente corrente (da usare negli endpoint protetti) ---
async def get_current_user_id(request: Request) -> int:
    """
    Dipendenza FastAPI per estrarre l'ID utente dal token di sessione.
    :param request: Oggetto Request di FastAPI.
    :return: L'ID utente (int).
    :raises HTTPException: Se il token di sessione è mancante, non valido o scaduto.
    """
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Non autenticato: token di sessione mancante")

    user_id = decode_access_token(session_token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Non autenticato: token di sessione non valido o scaduto")

    return user_id


@app.get("/health")
def health() -> dict:
    """Verifica lo stato di salute dell'applicazione."""
    return {"status": "ok"}

@app.post("/login")
async def login(dati: RequestLogin, response: Response, db_conn: mariadb.Connection = Depends(get_db_connection)) -> ResponseLogin :
    """
    Gestisce il login dell'utente e imposta un token di sessione.
    :param dati: Dati di login (username e password).
    :param response: Oggetto Response di FastAPI per impostare i cookie.
    :param db_conn: Connessione al database ottenuta dal pool.
    :return: Oggetto ResponseLogin con username e id utente.
    :raises HTTPException: Se le credenziali non sono valide o si verifica un errore DB.
    """
    if not dati.username.strip() or not dati.password.strip():
        raise HTTPException(status_code=400, detail="Credenziali non valide o vuote.")

    try:
        utente_raw = execute_query_ask(db_conn, f"select id, username from users where username=%s and password=%s;", [dati.username, dati.password])
    except mariadb.Error as e:
        # Errore generico del DB, non dare dettagli specifici sulla causa al client.
        raise HTTPException(status_code=500, detail="Errore del server durante il login.")

    if not utente_raw or not utente_raw[1:] or utente_raw[1][0]==-1: # utente_raw[0] contiene i nomi delle colonne, e non si può accedere con l'utente id=-1, che è l'ia
        raise HTTPException(status_code=401, detail="Nome utente o password errati.")

    user_id = utente_raw[1][0]
    username = utente_raw[1][1]

    # Creazione del token JWT con l'ID utente
    access_token = create_access_token(data={"sub": str(user_id)})

    # Imposta il cookie nella risposta
    response.set_cookie(
        key="session_token",
        value=access_token,
        httponly=True,  # Impedisce l'accesso al cookie tramite JavaScript
        samesite="lax", # Protezione CSRF, "Lax" per la maggior parte dei casi
        secure=True,    # Solo su HTTPS (in produzione)
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60 # Durata in secondi
    )

    return ResponseLogin(username=username, id=user_id)

@app.post("/register")
def register(dati: RequestRegister, db_conn: mariadb.Connection = Depends(get_db_connection)):
    """
    Registra un nuovo utente nel database.
    :param dati: Dati di registrazione (username e password).
    :param db_conn: Connessione al database ottenuta dal pool.
    :return: Messaggio di successo.
    :raises HTTPException: Se l'username è già registrato o si verifica un errore DB.
    """
    if not dati.username.strip() or not dati.password.strip() or not dati.repeatpass.strip():
        raise HTTPException(status_code=400, detail="Username o password non validi.")

    if dati.password!= dati.repeatpass:
        raise HTTPException(status_code=422, detail="Le due password non coincidono")

    try:
        # Controlla se l'utente esiste già
        existing_user = execute_query_ask(db_conn, f"select id from users where username=%s;", [dati.username])
        if existing_user and existing_user[1:]: # Se ci sono righe oltre le intestazioni di colonna
            raise HTTPException(status_code=409, detail="Nome utente già registrato.")


        # Genera codice amico nel formato 0000-0000-0000, max attempts serve per non avere un ciclo infinito
        # in casi estremi (riprova al massimo 20 volte)
        max_attempts = 20 
        attempts = 0
        code = ""

        while attempts < max_attempts:
            # Crea 3 blocchi di 4 cifre ez
            blocchi = []
            for i in range(3):
                blocco = ''
                for j in range(4):
                    blocco += str(random.randint(0, 9))
                blocchi.append(blocco)

            ret = '-'.join(blocchi)

            # Controlla se il codice esiste già nel db
            result = execute_query_ask(db_conn, f"SELECT id FROM users WHERE friend_code=%s;", [ret])
            if not result or len(result) == 1:
                code = ret
                break
            attempts += 1
        
        # Controlla se esiste un utente con tale codice amico ed in tal caso aggiunge 50 punti all'utente che si è registrato
        score = 0
        ret = execute_query_ask(db_conn, f"SELECT username FROM users WHERE friend_code=%s;", [dati.friend_code])
        if ret and len(ret)>1:
            score = 50
        # Inserimento del nuovo utente
        inserimento = execute_query_modify(db_conn, f'insert into users (username,password,score,friend_code) values (%s, %s, %s, %s);', [dati.username, dati.password, score, code])
    except mariadb.Error as e:
        print(f"Errore DB durante la registrazione: {e}") # Logga l'errore per debugging
        raise HTTPException(status_code=500, detail=f"Errore durante la registrazione dell'utente.")
    except HTTPException:
        raise # Rilancia le HTTPException già generate (es. 409)

    return {"message":"Registrazione avvenuta con successo"}

@app.post("/ask")
async def ask(domanda: RequestAsk, user_id: int = Depends(get_current_user_id), db_conn: mariadb.Connection = Depends(get_db_connection)):
    """
    Permette a un utente autenticato di porre una domanda.
    Incrementa il punteggio dell'utente.
    :param domanda: Dati della domanda (domanda, tema, tab_creation).
    :param user_id: ID dell'utente corrente, ottenuto dalla dipendenza.
    :param db_conn: Connessione al database ottenuta dal pool.
    :return: Oggetto ResponseAsk con un messaggio e l'elenco delle domande dell'utente.
    :raises HTTPException: Se la domanda è vuota o si verifica un errore DB.
    """
    temi=[]
    msg = "" if domanda.tab_creation == 1 else "Domanda aggiunta con successo"
    if domanda.tab_creation==0:
        if not domanda.question.strip():
            raise HTTPException(status_code=400, detail="La domanda non può essere vuota.")

        try:
            # Inizia una transazione per assicurare l'atomicità delle operazioni
            execute_query_modify(db_conn, 'START TRANSACTION')
            tema_id= execute_query_ask(db_conn, f'select id from themes where theme=%s;', [domanda.tema])
            execute_query_modify(db_conn, f'insert into questions (payload,theme_id,author) values (%s, %s, %s);', [domanda.question, tema_id[1][0], user_id])
            execute_query_modify(db_conn, f'UPDATE users SET score = score+10 WHERE id=%s;', [user_id])
            execute_query_modify(db_conn, 'COMMIT')
            t = threading.Thread(target=process_ai_response, args=(domanda.question, db_pool_manager)) # Passa l'istanza del pool
            t.start()
        except mariadb.Error as e:
            if (e.errno==1062): #controlla se l'errore è di duplicate entry (errno 1062)
                msg ="Questa domanda è stata già posta da qualcuno, e cerchiamo di averne di più varie possibili!\n Poni un'altra domanda!"
            else:
                msg= "Errore durante l'inserimento della domanda"
            execute_query_modify(db_conn, 'ROLLBACK') # Effettua il rollback in caso di errore
            print(f"Errore DB durante l'inserimento della domanda: {e}")


    
    try:
        elenco = execute_query_ask(db_conn, f'select questions.id, payload, theme, answered, checked from questions join themes on themes.id=theme_id where author=%s;', [user_id])
        themes = execute_query_ask(db_conn, f'select theme from themes;')
    except mariadb.Error as e:
        print(f"Errore DB durante l'ottenimento delle domande: {e}")
        raise HTTPException(status_code=500, detail=f"Errore durante l'ottenimento delle domande: {e}")
    themes.pop(0)
    elenco.pop(0) # Rimuove le intestazioni di colonna
    #costruzione della lista di temi da dare in output, rimuovendo l'ultimo usato per dare varietà alle domande e non permettendo due domande di fila con lo stesso tema
    for item in themes:
        temi.append(item[0])
    if domanda.tema in temi:
        temi.remove(domanda.tema)
    return ResponseAsk(message= msg, domande=elenco, temi=temi)


@app.post("/validate")
async def validate(domanda: RequestValidate, db_conn: mariadb.Connection = Depends(get_db_connection)):
    """
    Ottiene i dettagli di una domanda e le sue risposte per la validazione.
    :param domanda: Dati della richiesta di validazione (ID domanda).
    :param db_conn: Connessione al database ottenuta dal pool.
    :return: Oggetto ResponseValidate con domanda e risposte.
    :raises HTTPException: Se si verifica un errore DB.
    """
    try:
        payload = execute_query_ask(db_conn, f'select id, payload from questions where id=%s;', [domanda.questionid])
        risposte = execute_query_ask(db_conn, f'select id, payload from answers where question=%s;', [domanda.questionid])
        check = execute_query_ask(db_conn, f'select checked from questions where id=%s;', [domanda.questionid])
        best = execute_query_ask(db_conn, f'select payload from answers where question=%s and best=1;', [domanda.questionid])
        if len(best) > 1:
            best = best[1][0]
        else:
            best = ""
    except mariadb.Error as e:
        print(f"Errore DB durante l'ottenimento di domanda/risposte per validazione: {e}")
        raise HTTPException(status_code=500, detail=f"Errore durante l'ottenimento della domanda: {e}")

    risposte.pop(0) # Rimuove le intestazioni di colonna
    return ResponseValidate(message = "Scegli la risposta che ti sembra migliore", question=payload[1], answers=risposte, checked=check[1][0], best_answer=best)

@app.post("/best")
async def best(data: RequestBest, db_conn: mariadb.Connection = Depends(get_db_connection)):
    """
    Marca una risposta come la migliore per una data domanda.
    Incrementa il punteggio dell'autore della risposta.
    :param data: Dati della richiesta (ID domanda, ID risposta migliore).
    :param db_conn: Connessione al database ottenuta dal pool.
    :return: Oggetto ResponseValidate (riutilizzato per visualizzare le risposte).
    :raises HTTPException: Se si verifica un errore DB.
    """
    try:
        execute_query_modify(db_conn, 'START TRANSACTION')
        execute_query_modify(db_conn, f'UPDATE questions SET checked=1 WHERE id=%s;', [data.questionid])
        execute_query_modify(db_conn, f'UPDATE answers SET best=1 WHERE id=%s;', [data.answerid])
        execute_query_modify(db_conn, f'UPDATE users SET score=score+40 WHERE id in (select author from answers where id=%s);', [data.answerid])
        execute_query_modify(db_conn, 'COMMIT')
    except mariadb.Error as e:
        execute_query_modify(db_conn, 'ROLLBACK')
        print(f"Errore DB durante la selezione della migliore risposta: {e}")
        raise HTTPException(status_code=500, detail=f"Errore durante l'inserimento della valutazione: {e}")

    try:
        payload = execute_query_ask(db_conn, f'select id, payload from questions where id=%s;', [data.questionid])
        risposte = execute_query_ask(db_conn, f'select id, payload, author from answers where question=%s;', [data.questionid])
        check = execute_query_ask(db_conn, f'select checked from questions where id=%s;', [data.questionid])
    except mariadb.Error as e:
        print(f"Errore DB durante l'ottenimento di domanda/risposte dopo la selezione della migliore: {e}")
        raise HTTPException(status_code=500, detail=f"Errore durante l'ottenimento della domanda: {e}")

    risposte.pop(0)
    return ResponseValidate(message = "Scegli la risposta che credi sia stata data da un umano", question=payload[1], answers=risposte, checked=check[1][0], best_answer="")

@app.post("/human")
async def human(data: RequestHuman, user_id: int = Depends(get_current_user_id), db_conn: mariadb.Connection = Depends(get_db_connection)):
    """
    Registra l'input utente per indicare se una risposta è stata data da un umano.
    Incrementa il punteggio dell'utente che vota.
    :param data: Dati della richiesta (indicatore umano).
    :param user_id: ID dell'utente corrente.
    :param db_conn: Connessione al database ottenuta dal pool.
    :return: Messaggio di successo.
    :raises HTTPException: Se si verifica un errore DB.
    """
    if data.human > 0:
        try:
            execute_query_modify(db_conn, f'UPDATE users SET score=score+10 WHERE id=%s;', [user_id])
        except mariadb.Error as e:
            print(f"Errore DB durante l'aggiornamento del punteggio per il voto umano: {e}")
            raise HTTPException(status_code=500, detail=f"Errore durante l'ottenimento della domanda: {e}")

    return ResponseHuman(message = "Grazie per aver partecipato, bye bye")


def get_question(user_id: int, theme: str, questionid: int, db_conn: mariadb.Connection):
    """
    Funzione helper per ottenere una nuova domanda da rispondere.
    Marca la domanda come "in risposta" dall'utente corrente.
    :param user_id: ID dell'utente corrente.
    :param theme: Tema da escludere.
    :param questionid: ID della domanda precedente da escludere.
    :param db_conn: Connessione al database.
    :return: Dettagli della domanda selezionata.
    :raises mariadb.Error: Se si verifica un errore DB.
    """
    try:
        # Seleziona 10 domande non ancora risposte e non in fase di risposta
        # escludendo quelle dell'autore e il tema e ID specifici.
        ret = execute_query_ask(
            db_conn, f'SELECT questions.id, payload, theme FROM questions join themes on themes.id=theme_id WHERE author != %s AND is_answering=0 AND answered = 0 AND theme!=%s AND questions.id != %s ORDER BY id ASC LIMIT 10;', [user_id, theme, questionid]
        )
        ret.pop(0) # Rimuove le intestazioni di colonna

        if not ret:
            # Se non ci sono domande disponibili, potresti voler gestire questo caso
            # ad esempio, restituendo un messaggio specifico o un'eccezione.
            # Per ora, si limita a sollevare un errore se random.choice riceve una lista vuota.
            
            #raise HTTPException(status_code=404, detail="Nessuna nuova domanda disponibile.")
            return [0,"Non ci sono ulteriori domande a cui rispondere, vai a porne di nuove!", "placeholder"]

        scelta=random.choice(ret)
        # Inizia una transazione per aggiornare lo stato della domanda
        execute_query_modify(db_conn, 'START TRANSACTION')
        execute_query_modify(db_conn, f'UPDATE questions SET is_answering=0 WHERE is_answering=%s;', [user_id]) # Rilascia eventuali domande precedenti
        execute_query_modify(db_conn, f'UPDATE questions SET is_answering=%s WHERE id=%s;', [user_id, scelta[0]]) # Marca la nuova domanda come "in risposta"
        execute_query_modify(db_conn, 'COMMIT')
    except mariadb.Error as e:
        execute_query_modify(db_conn, 'ROLLBACK') # Rollback in caso di errore
        print(f"Errore DB in get_question: {e}")
        raise # Rilancia l'eccezione
    return scelta

@app.post("/answer")
async def answer(risposta: RequestAnswer, user_id: int = Depends(get_current_user_id), db_conn: mariadb.Connection = Depends(get_db_connection)):
    """
    Permette a un utente autenticato di rispondere a una domanda.
    :param risposta: Dati della risposta (testo risposta, ID domanda, tema, tab_creation).
    :param user_id: ID dell'utente corrente.
    :param db_conn: Connessione al database ottenuta dal pool.
    :return: Oggetto ResponseAnswer con un messaggio e la prossima domanda.
    :raises HTTPException: Se la risposta è vuota o si verifica un errore DB.
    """
    if risposta.tab_creation==1:
        msg=""
    else:
        msg="Risposta aggiunta con successo"
    if risposta.tab_creation==0:
        if not risposta.answer.strip():
            raise HTTPException(status_code=400, detail="La risposta non può essere vuota.")

        try:
            execute_query_modify(db_conn, 'START TRANSACTION')
            execute_query_modify(db_conn, f'insert into answers (payload,question,author) values (%s, %s, %s);', [risposta.answer, risposta.domandaid, user_id])
            execute_query_modify(db_conn, f'UPDATE questions SET answered=1 WHERE id=%s;', [risposta.domandaid])
            execute_query_modify(db_conn, 'COMMIT')
        except mariadb.Error as e:
            execute_query_modify(db_conn, 'ROLLBACK')
            print(f"Errore DB durante l'inserimento della risposta: {e}")
            msg="Errore durante l'inserimento della risposta"
    # Passa la connessione del database alla funzione helper get_question
    return ResponseAnswer(message= msg, payload=get_question(user_id, risposta.tema, risposta.domandaid, db_conn))
    
@app.get("/leaderboard")
async def leaderboard(db_conn: mariadb.Connection = Depends(get_db_connection)):
    """
    Restituisce la classifica degli utenti basata sul punteggio.
    :param db_conn: Connessione al database ottenuta dal pool.
    :return: Oggetto ResponseLeaderboard con la classifica.
    :raises HTTPException: Se si verifica un errore DB.
    """
    try:
        leaderboard_data = execute_query_ask(db_conn, f'select username, score from users where username != "IA" order by score DESC;') #non mostriamo l'ia, sarebbe uno svantaggio scorretto mettere gli utenti a confronto con l'ia
    except mariadb.Error as e:
        print(f"Errore DB durante la formazione della Leaderboard: {e}")
        raise HTTPException(status_code=500, detail=f"Errore nella formazione della Leaderboard: {e}")
    leaderboard_data.pop(0) # Rimuove le intestazioni di colonna
    return ResponseLeaderboard(leaderboard=leaderboard_data)

@app.get("/profile")
async def profile(user_id: int = Depends(get_current_user_id), db_conn: mariadb.Connection = Depends(get_db_connection)):
    """
    Restituisce i dati del profilo dell'utente autenticato.
    :param user_id: ID dell'utente corrente.
    :param db_conn: Connessione al database ottenuta dal pool.
    :return: Oggetto ResponseProfile con dati utente, numero domande e risposte.
    :raises HTTPException: Se si verifica un errore DB.
    """
    try:
        userdata=execute_query_ask(db_conn, f'select username, score, friend_code from users where id=%s;', [user_id])
        questnum=execute_query_ask(db_conn, f'select count(*) from questions where author=%s;', [user_id])
        ansnum=execute_query_ask(db_conn, f'select count(*) from answers where author=%s;', [user_id])
    except mariadb.Error as e:
        print(f"Errore DB nella raccolta dei dati del profilo: {e}")
        raise HTTPException(status_code=500, detail=f"Errore nella raccolta dei dati: {e}")

    return ResponseProfile(username=userdata[1][0], score=userdata[1][1], questions=questnum[1][0], answers= ansnum[1][0], friend_code= userdata[1][2])

@app.post("/passreset")
async def passreset(password: RequestPassreset, user_id: int = Depends(get_current_user_id), db_conn: mariadb.Connection = Depends(get_db_connection)):
    """
    Permette a un utente autenticato di reimpostare la propria password.
    :param password: Nuova password.
    :param user_id: ID dell'utente corrente.
    :param db_conn: Connessione al database ottenuta dal pool.
    :return: Messaggio di successo.
    :raises HTTPException: Se si verifica un errore DB.
    """
    try:
        # Esempio di come usare una query parametrizzata (molto più sicuro!):
        # cursor = db_conn.cursor()
        # cursor.execute("UPDATE users SET password=? WHERE id=?", (password.newpass, user_id))
        # db_conn.commit()
        # cursor.close()
        # Per semplicità, mantengo la f-string come nel codice originale, ma con un avviso.
        aggiornamento = execute_query_modify(db_conn, f'UPDATE users SET password=%s WHERE id=%s;', [password.newpass, user_id])
    except mariadb.Error as e:
        print(f"Errore DB nella modifica della password: {e}")
        raise HTTPException(status_code=500, detail=f"Errore nella modifica della password: {e}")

    return {"message": "ok"}


@app.post("/logout")
async def logout(response: Response, user_id: int = Depends(get_current_user_id), db_conn: mariadb.Connection = Depends(get_db_connection)):
    """
    Gestisce il logout dell'utente, rimuovendo il token di sessione e aggiornando lo stato delle domande.
    :param response: Oggetto Response di FastAPI per eliminare i cookie.
    :param user_id: ID dell'utente corrente.
    :param db_conn: Connessione al database ottenuta dal pool.
    :return: Messaggio di successo.
    :raises HTTPException: Se si verifica un errore DB.
    """
    try:
        # Aggiorna lo stato delle domande che l'utente stava rispondendo
        execute_query_modify(db_conn, f'UPDATE questions SET is_answering=0 WHERE is_answering=%s;', [user_id])
    except mariadb.Error as e:
        print(f"Errore DB durante l'aggiornamento dello stato delle domande al logout: {e}")
        raise HTTPException(status_code=500, detail="Errore durante l'aggiornamento dello stato delle domande.")

    response.delete_cookie(key="session_token")
    return {"message": "Logout effettuato con successo"}



@app.get("/check_new_answers")
async def check_new_answers(user_id: int = Depends(get_current_user_id), db_conn: mariadb.Connection = Depends(get_db_connection)):
    try:
        questions = execute_query_ask(db_conn, f"SELECT id FROM questions WHERE author=%s AND answered=1 AND checked=0;", [user_id])
    except mariadb.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    questions.pop(0)  # Rimuovi intestazioni colonne

    question_ids = [q[0] for q in questions]

    return {"new_answers": question_ids}




@app.on_event("startup")
def pull() -> None:
    """Avvia, se non è presente, il download del modello di Ollama"""
    modello=False
    try:
        response= requests.get(f"{OLLAMA_URL}/tags")
        response.raise_for_status()
        data=response.json()
        if "models" in data:
            for model in data["models"]:
                if model["name"] == MODEL_NAME:
                    modello=True
    except requests.exceptions.RequestException as e:
        print(f"Errore durante la comunicazione con l'api di Ollama: {e}")
        raise
    if not modello:
        data={"model": MODEL_NAME
                }
        try:
            response= requests.post(f"{OLLAMA_URL}/pull", json=data)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Errore durante la comunicazione con l'api di Ollama: {e}")
            raise

@app.on_event("startup")
def connect_mariadb_pool() -> None:
    """
    Evento di avvio dell'applicazione: inizializza il connection pool del database.
    """
    try:
        db_pool_manager.connect() # Questo chiama il metodo che inizializza il pool
    except mariadb.Error as e:
        print(f"Errore critico, impossibile inizializzare il connection pool del database: {e}")
        sys.exit(1) # Termina l'applicazione se il pool non può essere inizializzato


@app.on_event("shutdown")
def disconnect_mariadb_pool() -> None:
    """
    Evento di spegnimento dell'applicazione: chiude le connessioni nel pool.
    """
    # mariadb driver gestisce in gran parte la pulizia del pool
    # automaticamente all'uscita del processo. Chiamiamo comunque
    # il nostro metodo per coerenza e logging.
    db_pool_manager.close_pool()
    # Resetta il contatore delle connessioni attive al shutdown
    with _connections_lock:
        global _active_connections_count
        _active_connections_count = 0
    print("DEBUG_POOL: Contatore connessioni attive resettato al riavvio dell'applicazione.")
