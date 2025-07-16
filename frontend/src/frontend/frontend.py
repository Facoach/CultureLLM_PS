from requests import get, post
from requests.exceptions import RequestException, HTTPError
from fastapi import FastAPI, Request, Form, Query, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from typing import Dict, Optional, List, Callable, Any, Union
from urllib.parse import quote
from os import getenv
from json import loads
from starlette.templating import _TemplateResponse


# Parametri globali
BASE_URL = getenv("BACKEND_API_URL", "http://localhost:8001")

# Avvio dell'applicazione
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Mount delle directory per template e file statici (come immagini, css, js)
app.mount("/templates", StaticFiles(directory="templates"), name="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


# Funzione ausiliaria per effettuare richieste al backend
async def make_backend_request(
    request: Request,
    method: str,
    endpoint: str,
    data: Optional[Dict] = None,
    success_template: str = None,
    error_template: str = None,
    redirect_url_on_unauthorized: str = "/directlogin",
    **template_args: Any
):
    """
    Effettua una richiesta al backend e gestisce errori, redirect e rendering di template.

    :param request: Oggetto Request FastAPI.
    :param method: Metodo HTTP ("get" o "post").
    :param endpoint: Endpoint API nel backend.
    :param data: Dati JSON per la richiesta ("post").
    :param success_template: Template da mostrare in caso di successo.
    :param error_template: Template da mostrare in caso di errore.
    :param redirect_url_on_unauthorized: Redirect se manca token.
    :param template_args: Argomenti extra per il template.
    :return: Se viene specificato un template restituisce una TemplateResponse (la pagina HTML da mostrare),
             se il template di ritorno non è specificato restituisce soltanto
             il JSON ricevuto dal backend.
             Se l'utente non è autenticato restituisce una RedirectResponse alla pagina di login.
    """
    # Prepara headers e forwarding del cookie di sessione se esiste
    session_token = request.cookies.get("session_token")
    headers = {}
    if session_token:
        headers["Cookie"] = f"session_token={session_token}"
    elif redirect_url_on_unauthorized:
        # Se manca token e non siamo su login/register, redirect a login
        if endpoint not in ["/login", "/register"]:
            return RedirectResponse(url=redirect_url_on_unauthorized, status_code=302)

    try:
        # Effettua una richiesta al backend ("get" o "post")
        if method.lower() == "post":
            response_backend = post(f"{BASE_URL}{endpoint}", json=data, headers=headers)
        elif method.lower() == "get":
            response_backend = get(f"{BASE_URL}{endpoint}", headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response_backend.raise_for_status()
        retrieved_data = response_backend.json()
        
        # Fa il merge tra dati dal backend e gli eventuali argomenti aggiuntivi (per i template)
        final_template_args = {**template_args, **retrieved_data}
        if success_template:
            return templates.TemplateResponse(success_template, {"request": request, **final_template_args})
        # Se non c'è un template di ritorno restituisce soltanto l'oggetto ricevuto dal backend
        return retrieved_data
    # Gestisce eventuali errori del backend
    except HTTPError as e:
        # Caso token scaduto o assente
        if e.response.status_code==401:
            return RedirectResponse(url=redirect_url_on_unauthorized+"?message=Token scaduto o assente", status_code=302)
        detail = "Si è verificato un errore durante la richiesta al backend."
        if e.response is not None:
            try:
                error_response_json = e.response.json()
                if "detail" in error_response_json:
                    detail = error_response_json["detail"]
                elif "message" in error_response_json:
                    detail = error_response_json["message"]
            except ValueError:
                detail = e.response.text or detail
        # Renderizza la pagina di errore se definita, altrimenti rilancia l'eccezione
        print(f"Errore HTTP durante la richiesta a {endpoint}: {e} - Dettaglio: {detail}")
        template_to_render = error_template if error_template else success_template
        if template_to_render:
            return templates.TemplateResponse(template_to_render, {"request": request, "message": detail, **template_args})
        raise e
    # Gestione eventuali errori di connessione
    except RequestException as e:
        print(f"Si è verificato un errore di connessione al backend per {endpoint}: {e}")
        template_to_render = error_template if error_template else success_template
        if template_to_render:
            return templates.TemplateResponse(template_to_render, {"request": request, "message": f"Impossibile connettersi al servizio di backend: {e}", **template_args})
        raise e


# Definizione degli endpoint

@app.get("/", response_class=HTMLResponse)
def init(request: Request):
    """Visualizza la Homepage"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/directlogin", response_class=HTMLResponse)
def directlogin(request: Request, message:str=""):
    """Pagina di login con messaggio opzionale."""
    return templates.TemplateResponse("login.html", {"request": request, "message":message})

@app.get("/directregister", response_class=HTMLResponse)
def directregister(request: Request):
    """Pagina di registrazione."""
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/directpassreset", response_class=HTMLResponse)
def directpassreset(request: Request):
    """Pagina di reset password."""
    return templates.TemplateResponse("passreset.html", {"request": request})


@app.post("/login", response_class=HTMLResponse)
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    """
    Gestisce il login via form, effettua chiamata al backend e copia il cookie di sessione.
    """
    if not username.strip() or not password.strip():
        return templates.TemplateResponse("login.html", {"request": request, "message": "Username o password non validi."})
    
    data = {
        "username": username,
        "password": password
    }
    
    # Effettua la richiesta POST al backend per autenticare l'utente
    try:
        response_backend = post(f"{BASE_URL}/login", json=data)
        response_backend.raise_for_status()
        retrieved_obj= response_backend.json
    # In caso di errore HTTP, mostra il dettaglio ritornato dal backend se disponibile
    except HTTPError as e:
        detail = "Si è verificato un errore durante la richiesta al backend."
        if e.response is not None and e.response.json() is not None and "detail" in e.response.json():
            detail = e.response.json()["detail"]
        print(f"Errore HTTP durante la richiesta di login: {e} - Dettaglio: {detail}")
        return templates.TemplateResponse("login.html", {"request": request, "message": detail})
    # Gestisce errori di connessione o altri problemi con la richiesta
    except RequestException as e:
        print(f"Si è verificato un errore durante la richiesta: {e}")
        return templates.TemplateResponse("login.html", {"request": request, "message": f"Impossibile connettersi al servizio di backend: {e}"})

    # Se il login ha successo, il backend avrà impostato il cookie,
    # dunque reindirizza l'utente ad una pagina protetta e copia
    # tutti i cookie settati dal backend
    response_redirect = RedirectResponse(url="/dashboard", status_code=302)
    for cookie_name, cookie_value in response_backend.cookies.items():
        response_redirect.set_cookie(key=cookie_name, value=cookie_value, httponly=True, samesite="lax", secure=True)
    
    return response_redirect


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """
    Visualizza la dashboard utente.
    """
    # Verifica la presenza del cookie di sessione, se non è presente
    # fa un redirect alla pagina di login
    session_token = request.cookies.get("session_token")
    if not session_token:
        return RedirectResponse(url="/directlogin", status_code=302)
    
    return templates.TemplateResponse("dashboard.html", {"request": request, "message": "Benvenuto nella tua dashboard!"})


@app.get("/get_tab_content/ask", response_class=HTMLResponse)
async def get_ask_tab_content(request: Request):
    """
    Carica la tab di creazione domanda.
    """
    data = {
        "question": "placeholder",
        "tema": "placeholder",
        "tab_creation": 1
    }
    # Effettua richiesta al backend
    return await make_backend_request(
        request,
        method="post",
        endpoint="/ask",
        data=data,
        success_template="ask.html",
        error_template="ask.html",
    )


@app.get("/get_tab_content/leaderboard", response_class=HTMLResponse)
async def get_leaderboard_tab_content(request: Request):
    """
    Carica la tab leaderboard.
    """
    # Effettua richiesta al backend
    return await make_backend_request(
        request,
        method="get",
        endpoint="/leaderboard",
        success_template="leaderboard.html",
        error_template="leaderboard.html",
        message=""
    )

@app.get("/get_tab_content/answer", response_class=HTMLResponse)
async def get_answer_tab_content(request: Request):
    """
    Carica la tab di risposta.
    """
    data = {
        "domanda": "placeholder",
        "answer": "placeholder",
        "domandaid": 0,
        "tema": "placeholder",
        "tab_creation": 1
    }
    # Effettua richiesta al backend
    return await make_backend_request(
        request,
        method="post",
        endpoint="/answer",
        data=data,
        success_template="answer.html",
        error_template="answer.html"
    )

@app.post("/register", response_class=HTMLResponse)
async def register_post(request: Request, username: str = Form(...), password: str = Form(...), repeatpass: str = Form(...), friend_code: str = Form("")):
    """
    Gestisce la registrazione nuovo utente.
    """
    if not username.strip() or not password.strip():
        return templates.TemplateResponse("register.html", {"request": request, "message": "Username o password non validi."})
    
    data = {
        "username": username,
        "password": password,
        "repeatpass": repeatpass,
        "friend_code": friend_code
    }
    # Effettua richiesta al backend
    return await make_backend_request(
        request,
        method="post",
        endpoint="/register",
        data=data,
        success_template="register.html",
        error_template="register.html"
    )


@app.post("/passreset", response_class=HTMLResponse)
async def passreset(request: Request, newpass: str = Form(...), newpass2: str = Form(...)):
    """
    Gestisce il reset della password.
    """
    # Verifica che le due password coincidano e non siano vuote
    if newpass != newpass2:
        return templates.TemplateResponse("passreset.html", {"request": request, "message": "Le password inserite sono diverse."})
    if not newpass.strip():
        return templates.TemplateResponse("passreset.html", {"request": request, "message": "Password non valida."})
    
    data = {
        "newpass": newpass
    }
    # Effettua richiesta al backend
    response = await make_backend_request(
        request,
        method="post",
        endpoint="/passreset",
        data=data,
        success_template=None,
        error_template="passreset.html"
    )
    # In caso di errore HTML, ritorna la pagina di errore
    if isinstance(response, HTMLResponse):
        return response
    
    return RedirectResponse(url="/profile", status_code=302)


@app.post("/ask", response_class=HTMLResponse)
async def ask_post(request: Request, question: str = Form(...), tema: str = Form(...), temi_json:str =Form(...)):
    """
    Invia una nuova domanda.
    """
    if not question.strip():
        # Ricostruisce i temi per la renderizzazione in caso di errore
        listatemi = loads(temi_json)
        return templates.TemplateResponse("ask.html", {"request": request, "message": "La domanda non può essere vuota.", "temi": listatemi})

    data = {
        "question": question,
        "tema": tema,
        "tab_creation": 0
    }
    # Effettua richiesta al backend
    return await make_backend_request(
        request,
        method="post",
        endpoint="/ask",
        data=data,
        success_template="ask.html",
        error_template="ask.html",
    )


@app.post("/validate")
async def validate_post(request: Request, questionid: int = Form(...)):
    """
    Richiede la validazione di una domanda.
    """
    data = {
        "questionid": questionid
    }
    # Effettua richiesta al backend
    return await make_backend_request(
        request,
        method="post",
        endpoint="/validate",
        data=data,
    )


@app.post("/best")
async def best_post(request: Request, questionid: int = Form(...), answerid: int = Form(...)):
    """
    Marca la migliore risposta per una domanda.
    """
    data = {
        "questionid": questionid,
        "answerid": answerid
    }
    # Effettua richiesta al backend
    return await make_backend_request(
        request,
        method="post",
        endpoint="/best",
        data=data,
    )


@app.post("/human")
async def human_post(request: Request, human: int = Form(...), questionid: int = Form(...)):
    """
    Registra se una risposta è stata data da un umano.
    """
    data = {
        "human": human,
        "questionid": questionid
    }
    # Effettua richiesta al backend
    return await make_backend_request(
        request,
        method="post",
        endpoint="/human",
        data=data,
    )


@app.post("/answer", response_class=HTMLResponse)
async def answer_post(request: Request, answer: str = Form(...), domanda: str = Form(...), domandaid: int = Form(...), tab_creation: int = Form(...), tema: str = Form(...)):
    """
    Invia una risposta.
    """
    if not answer.strip():
        return templates.TemplateResponse("answer.html", {"request": request, "message": "La risposta non può essere vuota."})
    
    data = {
        "domanda": domanda,
        "answer": answer,
        "domandaid": domandaid,
        "tema": tema,
        "tab_creation": tab_creation
    }
    # Effettua richiesta al backend
    return await make_backend_request(
        request,
        method="post",
        endpoint="/answer",
        data=data,
        success_template="answer.html",
        error_template="answer.html"
    )

@app.get("/profile", response_class=HTMLResponse)
async def profile(request: Request):
    """
    Mostra il profilo dell'utente.
    """
    # Effettua richiesta al backend
    return await make_backend_request(
        request,
        method="get",
        endpoint="/profile",
        success_template="profile.html",
        error_template="dashboard.html"
    )

@app.post("/logout", response_class=HTMLResponse)
async def logout_post(request: Request):
    """
    Gestisce il logout, elimina il cookie di sessione e reindirizza.
    """
    # Recupera il token di sessione dal cookie, se presente
    session_token = request.cookies.get("session_token")
    headers = {}
    if session_token:
        headers["Cookie"] = f"session_token={session_token}"

    # Effettua richiesta al backend per eseguire logout lato server
    try:
        response_backend = post(f"{BASE_URL}/logout", headers=headers)
        response_backend.raise_for_status()
    # Gestisce l'errore ma effettua comunque la rimozione del cookie 
    except RequestException as e:
        print(f"Errore durante il logout dal backend: {e}")
    
    # Rimuove il cookie di sessione lato browser
    response_redirect = RedirectResponse(url="/directlogin", status_code=302)
    response_redirect.delete_cookie(key="session_token")
    return response_redirect


@app.get("/check_new_answers")
async def frontend_check_new_answers(request: Request):
    """
    Mostra all'utente se ci sono nuove risposte da validare.
    """
    # Effettua richiesta al backend
    return await make_backend_request(
        request,
        method="get",
        endpoint="/check_new_answers"
    )
