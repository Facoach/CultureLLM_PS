from classes.models import ResponseCheckNewAnswers, ResponseLogout, ResponsePassreset, ResponseRegister, ResponseHuman, RequestLogin, RequestRegister, ResponseLogin, RequestAsk, RequestAnswer, ResponseAsk, ResponseAnswer, ResponseProfile, RequestValidate, ResponseLeaderboard, ResponseValidate, RequestHuman, RequestBest, RequestPassreset
from classes.database_connection import DatabaseConnection, DBPoolManager
from database_management.execute_query import execute_query_modify, execute_query_ask
from ai_management.ai_answers import process_ai_response 
from utils.jwt_utils import create_access_token
from utils.generic_utils import get_question, get_current_user_id
from os import getenv
from sys import exit
from mariadb import Connection, Error
from fastapi import FastAPI, HTTPException, Depends, Response
from random import randint, shuffle
from requests import get, post
from requests.exceptions import RequestException
from threading import Thread
from ai_management.ai_wrapper import check_theme_coherence, EvaluateRequest
from passlib.context import CryptContext


# Configurazione parametri JWT
ACCESS_TOKEN_EXPIRE_MINUTES = int(getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))


# Parametri per la connessione al db
HOST_DB = getenv("MYSQL_HOST", "localhost")
PORT_DB = getenv("MYSQL_PORT", 3307)
USER_DB = getenv("MYSQL_USER", "root")
PASSWORD_DB = getenv("MYSQL_PASSWORD", "root")
NAME_DB = getenv("MYSQL_DATABASE", "Culture")
POOL_SIZE = getenv("MYSQL_POOL_SIZE", 10)
POOL_NAME = getenv("MYSQL_POOL_NAME", "CultureAppMariaDBPool")

#variabile per la crittografia password
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Inizializza il gestore del connection pool, il pool
# sarà inizializzato formalmente all'evento 'startup' di FastAPI
db_pool_manager = DatabaseConnection(
    host=HOST_DB,
    port=int(PORT_DB),
    user=USER_DB,
    password=PASSWORD_DB,
    database=NAME_DB,
    pool_size=int(POOL_SIZE),
    pool_name=POOL_NAME
)
db_manager = DBPoolManager(db_pool_manager)
get_db_connection = db_manager.get_db_connection

# Applicazione FastAPI
app = FastAPI()


@app.get("/health")
def health() -> dict:
    """Verifica lo stato di salute dell'applicazione."""
    return {"status": "ok"}


@app.post("/login")
async def login(dati: RequestLogin, response: Response, db_conn: Connection = Depends(get_db_connection)) -> ResponseLogin :
    """
    Gestisce il login dell'utente e imposta un token di sessione JWT.

    :param dati: Oggetto RequestLogin con dati utente.
    :param response: Oggetto Response di FastAPI per impostare i cookie.
    :param db_conn: Connessione al database ottenuta dal pool.
    :return: Oggetto ResponseLogin con username e id utente.
    :raises HTTPException: Se le credenziali sono errate o c'è un errore nel DB.
    """
    if not dati.username.strip() or not dati.password.strip():
        raise HTTPException(status_code=400, detail="Credenziali non valide o vuote.")

    # Verifica se le credenziali sono corrette (No ad accesso con id -1 che appartiene all'IA, ecc...)
    try:
        utente_raw = execute_query_ask(db_conn, f"select id, username, password from users where username=%s;", [dati.username])
    except Error as e:
        raise HTTPException(status_code=500, detail="Errore del server durante il login.")
    
    if not utente_raw or not utente_raw[1:] or utente_raw[1][0]==-1:
        raise HTTPException(status_code=401, detail="Nome utente o password errati.")

    user_id = utente_raw[1][0]
    username = utente_raw[1][1]
    hashed_password = utente_raw[1][2]

    if not pwd_context.verify(dati.password, hashed_password):
        raise HTTPException(status_code=401, detail="Nome utente o password errati.")

    # Crea il token JWT con l'ID utente ed imposta il cookie nella risposta
    access_token = create_access_token(data={"sub": str(user_id)})
    response.set_cookie(
        key="session_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

    return ResponseLogin(username=username, id=user_id)


@app.post("/register")
def register(dati: RequestRegister, db_conn: Connection = Depends(get_db_connection)) -> ResponseRegister:
    """
    Registra un nuovo utente nel database.

    :param dati: Oggetto RequestRegister con dati utente.
    :param db_conn: Connessione al database ottenuta dal pool.
    :return: Oggetto ResponseRegister con messaggio di successo.
    :raises HTTPException: Se l'username è già registrato o si verifica un errore nel DB.
    """
    # Controlla la correttezza dei dati in input (username e password)
    if not dati.username.strip() or not dati.password.strip() or not dati.repeatpass.strip():
        raise HTTPException(status_code=400, detail="Username o password non validi.")

    if dati.password != dati.repeatpass:
        raise HTTPException(status_code=422, detail="Le due password non coincidono")

    #hash della password prima di inserirla
    hashed_password = pwd_context.hash(dati.password)

    try:
        # Verifica se lo username esiste già
        existing_user = execute_query_ask(db_conn, f"select id from users where username=%s;", [dati.username])
        if existing_user and existing_user[1:]: # Se ci sono righe oltre le intestazioni di colonna
            raise HTTPException(status_code=409, detail="Nome utente già registrato.")

        # Genera codice amico nel formato 0000-0000-0000, max attempts serve per non 
        # avere un ciclo infinito in casi estremi (riprova al massimo 20 volte)
        max_attempts = 20 
        attempts = 0
        code = ""

        while attempts < max_attempts:
            # Crea 3 blocchi di 4 cifre
            blocchi = []
            for i in range(3):
                blocco = ''
                for j in range(4):
                    blocco += str(randint(0, 9))
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
        ret = execute_query_ask(db_conn, f"SELECT id FROM users WHERE friend_code=%s;", [dati.friend_code])
        if ret and len(ret)>1:
            score = 50

        # Inserimento del nuovo utente nel db con eventuale score aggiuntivo
        execute_query_modify(db_conn, 'START TRANSACTION')
        execute_query_modify(db_conn, f'insert into users (username,password,score,friend_code) values (%s, %s, %s, %s);', [dati.username, hashed_password, score, code])
        execute_query_modify(db_conn, 'COMMIT')
    except Error as e:
        # Effettua il rollback in caso di errore e lo logga per debug
        execute_query_modify(db_conn, 'ROLLBACK')
        print(f"Errore DB durante la registrazione: {e}")
        raise HTTPException(status_code=500, detail=f"Errore durante la registrazione dell'utente.")
    except HTTPException:
        raise
    
    try:
        execute_query_modify(db_conn, 'START TRANSACTION')

        ret = execute_query_ask(db_conn, f"SELECT id FROM users WHERE friend_code=%s;", [dati.friend_code])
        if ret and len(ret)>1:
            #inserimento achievement friend code
            ach_id=execute_query_ask(db_conn, f'select id from achievements where type=%s;', ["codice_amico"])
            if len(ach_id) > 1:
                execute_query_modify(db_conn, f'insert into reached (user,achievement) values (%s, %s);', [ret[1][0], ach_id[1][0]])

            execute_query_modify(db_conn, 'COMMIT')
    except Error as e:
        if (e.errno==1062):
            print("achievement già presente")
        else:
            execute_query_modify(db_conn, 'ROLLBACK')
            print(f"Errore DB durante l'assegnazione di un achievement': {e}")
            raise HTTPException(status_code=500, detail=f"Errore durante l'assegnazione di un achievement'.")

    return ResponseRegister(message = "Registrazione avvenuta con successo")


@app.post("/ask")
async def ask(domanda: RequestAsk, user_id: int = Depends(get_current_user_id), db_conn: Connection = Depends(get_db_connection)) -> ResponseAsk:
    """
    Permette ad un utente autenticato di porre una domanda ed aggiorna il suo punteggio (incrementandolo).

    :param domanda: Oggetto RequestAsk con la domanda da porre.
    :param user_id: ID dell'utente autenticato.
    :param db_conn: Connessione al database ottenuta dal pool.
    :return: Oggetto ResponseAsk con un messaggio e la lista delle domande dell'utente.
    :raises HTTPException: Se la domanda è vuota o si verifica un errore nel DB.
    """
    temi=[]
    msg = "" if domanda.tab_creation == 1 else "Domanda aggiunta con successo"
    
    if domanda.tab_creation==0:
        if not domanda.question.strip():
            raise HTTPException(status_code=400, detail="La domanda non può essere vuota.")
        
        # Verifica della coerenza della domanda col tema scelto
        data = EvaluateRequest(question=domanda.question, theme=domanda.tema)
        ai_response = check_theme_coherence(data)
        print("AI_RESPONSE IN BACKEND -> ")
        print(ai_response)

        # Se il livello di coerenza è almeno 5 la domanda viene accettata
        if ai_response.bool == "Vero":
            try:
                # Recupera l'id del tema scelto, inserisce la domanda nel db
                # aggiorna il punteggio dell'utente
                execute_query_modify(db_conn, 'START TRANSACTION')
                tema_id= execute_query_ask(db_conn, f'select id from themes where theme=%s;', [domanda.tema])
                execute_query_modify(db_conn, f'insert into questions (payload,theme_id,author) values (%s, %s, %s);', [domanda.question[:255], tema_id[1][0], user_id])
                execute_query_modify(db_conn, f'UPDATE users SET score = score+10 WHERE id=%s;', [user_id])

                #controllo achievement domande
                questnum=execute_query_ask(db_conn, f'select count(*) from questions where author=%s;', [user_id])
                ach_id=execute_query_ask(db_conn, f'select id from achievements where threshold=%s and type=%s;', [questnum[1][0], "domande_poste"])
                if len(ach_id) > 1:
                    execute_query_modify(db_conn, f'insert into reached (user,achievement) values (%s, %s);', [user_id, ach_id[1][0]])

                execute_query_modify(db_conn, 'COMMIT')
                # Avvia l'IA su un thread separato per generare la risposta
                t = Thread(target=process_ai_response, args=(domanda.question, db_pool_manager))
                t.start()
            # Controlla il tipo di errore (duplicate entry o altro) ed effettua il rollback in caso di errore
            except Error as e:
                if (e.errno==1062): 
                    msg ="Questa domanda è stata già posta da qualcuno, e cerchiamo di averne di più varie possibili!\n Poni un'altra domanda!"
                else:
                    msg= "Errore durante l'inserimento della domanda"
                execute_query_modify(db_conn, 'ROLLBACK')
                print(f"Errore DB durante l'inserimento della domanda: {e}")

            try:
                execute_query_modify(db_conn, 'START TRANSACTION')

                #controllo achievement punti
                points=execute_query_ask(db_conn, f'select score from users where id=%s;', [user_id])
                ach_id1=execute_query_ask(db_conn, f'select id from achievements where type=%s AND %s BETWEEN threshold AND threshold+50;', ["punti", points[1][0]])
                if len(ach_id1) > 1:
                    execute_query_modify(db_conn, f'insert into reached (user,achievement) values (%s, %s);', [user_id, ach_id1[1][0]])
                
                execute_query_modify(db_conn, 'COMMIT')
            except Error as e:
                if (e.errno==1062):
                    print("achievement già inserito")
                else:
                    print(f"Errore DB durante l'inserimento dell'obbiettivo: {e}")
                    raise HTTPException(status_code=500, detail=f"Errore durante l'inserimento dell'obbiettivo: {e}")
                
        else:
            msg= "l'IA ritiene che la domanda non sia coerente con il tema"

    # Recupera la lista aggiornata delle domande e dei temi dell'utente
    try:
        elenco = execute_query_ask(db_conn, f'select questions.id, payload, theme, answered, checked from questions join themes on themes.id=theme_id where author=%s;', [user_id])
        themes = execute_query_ask(db_conn, f'select theme from themes;')
    except Error as e:
        print(f"Errore DB durante l'ottenimento delle domande: {e}")
        raise HTTPException(status_code=500, detail=f"Errore durante l'ottenimento delle domande: {e}")
    themes.pop(0)
    elenco.pop(0)
    # Costruzione della lista di temi da dare in output, rimuovendo l'ultimo usato per dare 
    # varietà alle domande e non permettendo due domande di fila con lo stesso tema
    for item in themes:
        temi.append(item[0])
    if domanda.tema in temi:
        temi.remove(domanda.tema)

    return ResponseAsk(message= msg, domande=elenco, temi=temi)


@app.post("/validate")
async def validate(domanda: RequestValidate, db_conn: Connection = Depends(get_db_connection)) -> ResponseValidate:
    """
    Ottiene i dettagli di una domanda e tutte le sue risposte per la validazione.

    :param domanda: Oggetto RequestValidate contenente l'ID della domanda da validare.
    :param db_conn: Connessione al database ottenuta dal pool.
    :return: Oggetto ResponseValidate con testo della domanda, elenco risposte, stato validazione, eventuale miglior risposta.
    :raises HTTPException: Se si verifica un errore nel DB.
    """
    # Recupera il testo e l'id della domanda, le domande ad essa associate, il suo stato
    # di validazione (checked) e l'eventuale miglior risposta
    try:
        payload = execute_query_ask(db_conn, f'select id, payload from questions where id=%s;', [domanda.questionid])
        risposte = execute_query_ask(db_conn, f'select id, payload from answers where question=%s;', [domanda.questionid])
        check = execute_query_ask(db_conn, f'select checked from questions where id=%s;', [domanda.questionid])
        best = execute_query_ask(db_conn, f'select payload from answers where question=%s and best=1;', [domanda.questionid])
        # Controlla l'esistenza della miglior risposta
        if len(best) > 1:
            best = best[1][0]
        else:
            best = ""
    except Error as e:
        print(f"Errore DB durante l'ottenimento di domanda/risposte per validazione: {e}")
        raise HTTPException(status_code=500, detail=f"Errore durante l'ottenimento della domanda: {e}")

    risposte.pop(0)
    # Effettua lo shuffle randomico dell'ordine delle risposte per 
    # evitare un bias durante la scelta della best ed il turing test
    shuffle(risposte)

    return ResponseValidate(message = "Scegli la risposta che ti sembra migliore", question=payload[1], answers=risposte, checked=check[1][0], best_answer=best)

@app.post("/best")
async def best(data: RequestBest, user_id: int = Depends(get_current_user_id), db_conn: Connection = Depends(get_db_connection)) -> ResponseValidate:
    """
    Marca una risposta come la migliore per una data domanda ed
    aggiorna il punteggio dell'autore della domanda (lo incrementa)

    :param data: Oggetto RequestBest con ID domanda e ID della risposta migliore.
    :param db_conn: Connessione al database ottenuta dal pool.
    :return: oggetto ResponseValidate riutilizzato per visualizzare le risposte aggiornate.
    :raises HTTPException: Se si verifica un errore nel DB.
    """
    # Segna la domanda come "checked" e la risposta come "best", 
    # aggiorna lo score dell'autore della risposta migliore
    try:
        execute_query_modify(db_conn, 'START TRANSACTION')
        execute_query_modify(db_conn, f'UPDATE questions SET checked=1 WHERE id=%s;', [data.questionid])
        execute_query_modify(db_conn, f'UPDATE answers SET best=1 WHERE id=%s;', [data.answerid])
        execute_query_modify(db_conn, f'UPDATE users SET score=score+40 WHERE id in (select author from answers where id=%s);', [data.answerid])
 
        #controllo achievement validazione
        valnum=execute_query_ask(db_conn, f'select count(*) from questions where author=%s and checked=1;', [user_id])
        ach_id=execute_query_ask(db_conn, f'select id from achievements where threshold=%s and type=%s;', [valnum[1][0], "domande_valutate"])
        if len(ach_id) > 1:
            execute_query_modify(db_conn, f'insert into reached (user,achievement) values (%s, %s);', [user_id, ach_id[1][0]])

        execute_query_modify(db_conn, 'COMMIT')
    # Effettua il rollback in caso di errore
    except Error as e:
        execute_query_modify(db_conn, 'ROLLBACK')
        print(f"Errore DB durante la selezione della migliore risposta: {e}")
        raise HTTPException(status_code=500, detail=f"Errore durante l'inserimento della valutazione: {e}")
    
    try:
        execute_query_modify(db_conn, 'START TRANSACTION')

        #controllo achievement punti
        user=execute_query_ask(db_conn, f'select author from answers where id=%s;', [data.answerid])
        if len(user)>1:
            points=execute_query_ask(db_conn, f'select score from users where id=%s;', [user[1][0]])
            ach_id1=execute_query_ask(db_conn, f'select id from achievements where type=%s AND %s BETWEEN threshold AND threshold+50;', ["punti", points[1][0]])
            if len(ach_id1) > 1:
                execute_query_modify(db_conn, f'insert into reached (user,achievement) values (%s, %s);', [user_id, ach_id1[1][0]])
                
        execute_query_modify(db_conn, 'COMMIT')
    except Error as e:
        if (e.errno==1062):
            print("achievement già inserito")
        else:
            print(f"Errore DB durante l'inserimento dell'obbiettivo: {e}")
            raise HTTPException(status_code=500, detail=f"Errore durante l'inserimento dell'obbiettivo: {e}")
        
    # Recupera la domanda aggiornata, il suo stato ("checked" o meno) e tutte le sue risposte 
    try:
        payload = execute_query_ask(db_conn, f'select id, payload from questions where id=%s;', [data.questionid])
        risposte = execute_query_ask(db_conn, f'select id, payload, author from answers where question=%s;', [data.questionid])
        check = execute_query_ask(db_conn, f'select checked from questions where id=%s;', [data.questionid])
    except Error as e:
        print(f"Errore DB durante l'ottenimento di domanda/risposte dopo la selezione della migliore: {e}")
        raise HTTPException(status_code=500, detail=f"Errore durante l'ottenimento della domanda: {e}")

    risposte.pop(0)

    return ResponseValidate(message = "Scegli la risposta che credi sia stata data da un umano", question=payload[1], answers=risposte, checked=check[1][0], best_answer="")

@app.post("/human")
async def human(data: RequestHuman, user_id: int = Depends(get_current_user_id), db_conn: Connection = Depends(get_db_connection)) -> ResponseHuman:
    """
    Registra la scelta di un utente che indica se una risposta è stata data da un umano ed
    aggiorna il punteggio dell'utente se la risposta è positiva (ha indovinato)

    :param data: Oggetto RequestHuman con indicatore umano (se è stata ritenuta una risposta umana o meno)
    :param user_id: ID dell'utente autenticato.
    :param db_conn: Connessione al database ottenuta dal pool.
    :return: Oggetto ResponseHuman con messaggio di successo.
    :raises HTTPException: Se si verifica un errore nel DB.
    """
    # Se la risposta è stata indicata come umana aggiunge 10 punti all'utente
    if data.human > 0:
        try:
            execute_query_modify(db_conn, 'START TRANSACTION')
            execute_query_modify(db_conn, f'UPDATE users SET score=score+10 WHERE id=%s;', [user_id])
            execute_query_modify(db_conn, 'COMMIT')
        # Effettua il rollback in caso di errore
        except Error as e:
            execute_query_modify(db_conn, 'ROLLBACK')
            print(f"Errore DB durante l'aggiornamento del punteggio per il voto umano: {e}")
            raise HTTPException(status_code=500, detail=f"Errore durante l'ottenimento della domanda: {e}")
        
        try:
            execute_query_modify(db_conn, 'START TRANSACTION')

            #controllo achievement punti
            points=execute_query_ask(db_conn, f'select score from users where id=%s;', [user_id])
            ach_id1=execute_query_ask(db_conn, f'select id from achievements where type=%s AND %s BETWEEN threshold AND threshold+50;', ["punti", points[1][0]])
            if len(ach_id1) > 1:
                execute_query_modify(db_conn, f'insert into reached (user,achievement) values (%s, %s);', [user_id, ach_id1[1][0]])
                
            execute_query_modify(db_conn, 'COMMIT')
        except Error as e:
            if (e.errno==1062):
                print("achievement già inserito")
            else:
                print(f"Errore DB durante l'inserimento dell'obbiettivo: {e}")
                raise HTTPException(status_code=500, detail=f"Errore durante l'inserimento dell'obbiettivo: {e}")

    return ResponseHuman(message = "Grazie per aver partecipato, bye bye")


@app.post("/answer")
async def answer(risposta: RequestAnswer, user_id: int = Depends(get_current_user_id), db_conn: Connection = Depends(get_db_connection)) -> ResponseAnswer:
    """
    Permette ad un utente autenticato di rispondere a una domanda.

    :param risposta: Oggetto RequestAnswer con testo risposta, ID domanda, tema, e tab_creation.
    :param user_id: ID dell'utente autenticato.
    :param db_conn: Connessione al database ottenuta dal pool.
    :return: Oggetto ResponseAnswer con un messaggio e la prossima domanda.
    :raises HTTPException: Se la risposta è vuota o si verifica un errore nel DB.
    """
    if risposta.tab_creation==1:
        msg=""
    else:
        msg="Risposta aggiunta con successo"

    if risposta.tab_creation==0:
        if not risposta.answer.strip():
            raise HTTPException(status_code=400, detail="La risposta non può essere vuota.")
        # Inserisce la risposta nel db troncandola a 511 caratteri, aggiorna la domanda come "answered"
        try:
            execute_query_modify(db_conn, 'START TRANSACTION')
            execute_query_modify(db_conn, f'insert into answers (payload,question,author) values (%s, %s, %s);', [risposta.answer[:511], risposta.domandaid, user_id])
            execute_query_modify(db_conn, f'UPDATE questions SET answered=1 WHERE id=%s;', [risposta.domandaid])

            #controllo achievement risposte
            ansnum=execute_query_ask(db_conn, f'select count(*) from answers where author=%s;', [user_id])
            ach_id=execute_query_ask(db_conn, f'select id from achievements where threshold=%s and type=%s;', [ansnum[1][0], "risposte_date"])
            if len(ach_id) > 1:
                execute_query_modify(db_conn, f'insert into reached (user,achievement) values (%s, %s);', [user_id, ach_id[1][0]])
                
            execute_query_modify(db_conn, 'COMMIT')
        # Effettua il rollback in caso di errore
        except Error as e:
            execute_query_modify(db_conn, 'ROLLBACK')
            print(f"Errore DB durante l'inserimento della risposta: {e}")
            msg="Errore durante l'inserimento della risposta"

    return ResponseAnswer(message= msg, payload=get_question(user_id, risposta.tema, risposta.domandaid, db_conn))
    
@app.get("/leaderboard")
async def leaderboard(db_conn: Connection = Depends(get_db_connection)) -> ResponseLeaderboard:
    """
    Restituisce la classifica degli utenti basata sul punteggio.

    :param db_conn: Connessione al database ottenuta dal pool.
    :return: Oggetto ResponseLeaderboard con la classifica.
    :raises HTTPException: Se si verifica un errore nel DB.
    """
    # Recupera la leaderboard ordinando gli utenti per punteggio decrescente escludendo l'utente IA 
    try:
        leaderboard_data = execute_query_ask(db_conn, f'select username, score from users where username != "IA" order by score DESC;') #non mostriamo l'ia, sarebbe uno svantaggio scorretto mettere gli utenti a confronto con l'ia
    except Error as e:
        print(f"Errore DB durante la formazione della Leaderboard: {e}")
        raise HTTPException(status_code=500, detail=f"Errore nella formazione della Leaderboard: {e}")
    
    leaderboard_data.pop(0)

    return ResponseLeaderboard(leaderboard=leaderboard_data)


@app.get("/profile")
async def profile(user_id: int = Depends(get_current_user_id), db_conn: Connection = Depends(get_db_connection)) -> ResponseProfile:
    """
    Restituisce i dati del profilo dell'utente autenticato.

    :param user_id: ID dell'utente autenticato.
    :param db_conn: Connessione al database ottenuta dal pool.
    :return: Oggetto ResponseProfile con dati utente, numero domande e risposte.
    :raises HTTPException: Se si verifica un errore nel DB.
    """
    # Recupera username, punteggio e codice amico dell'utente autenticato,
    # e conta il numero di domande/risposte poste/date dall'utente 
    try:
        userdata=execute_query_ask(db_conn, f'select username, score, friend_code from users where id=%s;', [user_id])
        questnum=execute_query_ask(db_conn, f'select count(*) from questions where author=%s;', [user_id])
        ansnum=execute_query_ask(db_conn, f'select count(*) from answers where author=%s;', [user_id])
        rows=execute_query_ask(db_conn, f'select achievements.name from reached join achievements on reached.achievement=achievements.id where reached.user=%s;', [user_id]) 
        rows.pop(0)
        print("\n\nDEBUG ROWS:\n", rows)
        objectives = [r[0] for r in rows]
        print("\nOBJECTIVESSSSSS:",objectives)
    except Error as e:
        print(f"Errore DB nella raccolta dei dati del profilo: {e}")
        raise HTTPException(status_code=500, detail=f"Errore nella raccolta dei dati: {e}")

    return ResponseProfile(username=userdata[1][0], score=userdata[1][1], questions=questnum[1][0], answers= ansnum[1][0], friend_code= userdata[1][2], achievements=objectives)


@app.post("/passreset")
async def passreset(password: RequestPassreset, user_id: int = Depends(get_current_user_id), db_conn: Connection = Depends(get_db_connection)) -> ResponsePassreset:
    """
    Permette a un utente autenticato di reimpostare la propria password.

    :param password: Oggetto RequestPassreset con la nuova password.
    :param user_id: ID dell'utente autenticato.
    :param db_conn: Connessione al database ottenuta dal pool.
    :return: Oggetto ResponsePassreset con messaggio di successo.
    :raises HTTPException: Se si verifica un errore nel DB.
    """

    #hash della password prima di inserirla
    hashed_password = pwd_context.hash(password.newpass)

    # Aggiorna la password dell'utente corrente
    try:
        execute_query_modify(db_conn, 'START TRANSACTION')
        execute_query_modify(db_conn, f'UPDATE users SET password=%s WHERE id=%s;', [hashed_password, user_id])
        execute_query_modify(db_conn, 'COMMIT')
    # Effettua il rollback in caso di errrore
    except Error as e:
        execute_query_modify(db_conn, 'ROLLBACK')
        print(f"Errore DB nella modifica della password: {e}")
        raise HTTPException(status_code=500, detail=f"Errore nella modifica della password: {e}")

    return ResponsePassreset(message = "ok")


@app.post("/logout")
async def logout(response: Response, user_id: int = Depends(get_current_user_id), db_conn: Connection = Depends(get_db_connection)) -> ResponseLogout:
    """
    Gestisce il logout dell'utente, rimuovendo il token di sessione e aggiornando lo stato delle domande.

    :param response: Oggetto Response di FastAPI per eliminare i cookie.
    :param user_id: ID dell'utente corrente.
    :param db_conn: Connessione al database ottenuta dal pool.
    :return: Oggetto ResponseLogout con messaggio di successo.
    :raises HTTPException: Se si verifica un errore DB.
    """
    # Aggiorna lo stato delle domande a cui l'utente stava rispondendo
    try:
        transazione = execute_query_modify(db_conn, 'START TRANSACTION')
        execute_query_modify(db_conn, f'UPDATE questions SET is_answering=0 WHERE is_answering=%s;', [user_id])
        transazione = execute_query_modify(db_conn, 'COMMIT')
    # Effettua il rollback in caso di errore
    except Error as e:
        transazione = execute_query_modify(db_conn, 'ROLLBACK')
        print(f"Errore DB durante l'aggiornamento dello stato delle domande al logout: {e}")
        raise HTTPException(status_code=500, detail="Errore durante l'aggiornamento dello stato delle domande.")
    # Cancella il cookie di sessione per effettuare effettivamente il logout lato client
    response.delete_cookie(key="session_token")

    return ResponseLogout(message = "Logout effettuato con successo")


@app.get("/check_new_answers")
async def check_new_answers(user_id: int = Depends(get_current_user_id), db_conn: Connection = Depends(get_db_connection)) -> ResponseCheckNewAnswers:
    """
    Verifica quali domande hanno ricevuto risposta

    :param user_id: ID dell'utente autenticato.
    :param db_conn: Connessione al database ottenuta dal pool.
    :return: Oggetto ResponseCheckNewAnswers con la lista di ID delle domande.
    :raises HTTPException: Se si verifica un errore nel DB.
    """
    # Recupera gli id delle domande che sono "answered", hanno almeno 4 risposte e
    # non sono state ancora verificate (checked = 0)
    try:
        questions = execute_query_ask(db_conn, f"SELECT distinct questions.id FROM questions JOIN answers on (questions.id=answers.question) WHERE questions.author=%s AND questions.answered=1 AND questions.checked=0 GROUP BY questions.id HAVING count(answers.id)>=4;", [user_id])
    except Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    questions.pop(0)
    # Estrae solo gli ID delle domande dal risultato
    question_ids = [q[0] for q in questions]

    return ResponseCheckNewAnswers(new_answers = question_ids)


@app.on_event("startup")
def connect_mariadb_pool() -> None:
    """
    Evento di avvio dell'applicazione che inizializza il connection pool del database.
    """
    try:
        db_pool_manager.connect()
    except Error as e:
        print(f"Errore critico, impossibile inizializzare il connection pool del database: {e}")
        exit(1)


@app.on_event("shutdown")
def disconnect_mariadb_pool() -> None:
    """
    Evento di spegnimento dell'applicazione che chiude le connessioni nel pool.
    """
    # Chiude il pool in modo esplicito e resetta il contatore delle connessioni attive
    db_pool_manager.close_pool()
    db_pool_manager.reset_active_count()
    print("DEBUG_POOL: Contatore connessioni attive resettato al riavvio dell'applicazione.")
