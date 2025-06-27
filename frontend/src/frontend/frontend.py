import requests
from fastapi import FastAPI, Request, Form, Query, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from typing import Dict, Optional, List, Callable, Any
from urllib.parse import quote
import os
import json


# Parametri globali
BASE_URL = os.getenv("BACKEND_API_URL", "http://localhost:8001")

# Avvio dell'applicazione
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Per poter mostrare le immagini nelle pagine
app.mount("/templates", StaticFiles(directory="templates"), name="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


# --- Helper Function for Backend Requests ---
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
    Handles making a request to the backend, including session token forwarding,
    error handling, and rendering appropriate templates or redirects.

    Args:
        request: The FastAPI Request object.
        method: The HTTP method for the request (e.g., "get", "post").
        endpoint: The backend API endpoint (e.g., "/login", "/ask").
        data: Optional dictionary of data to send as JSON in the request body.
        success_template: The name of the template to render on successful response.
        error_template: The name of the template to render on an error. If not provided,
                        success_template will be used.
        redirect_url_on_unauthorized: URL to redirect to if session token is missing.
        **template_args: Additional keyword arguments to pass to the template.

    Returns:
        A FastAPI Response (HTMLResponse or RedirectResponse) or raises an exception.
    """
    session_token = request.cookies.get("session_token")
    headers = {}
    if session_token:
        headers["Cookie"] = f"session_token={session_token}"
    elif redirect_url_on_unauthorized: # If session_token is required but missing
        # Only redirect if this endpoint expects a session token.
        # For login/register, session_token is not expected initially.
        if endpoint not in ["/login", "/register"]:
            return RedirectResponse(url=redirect_url_on_unauthorized, status_code=302)

    try:
        if method.lower() == "post":
            response_backend = requests.post(f"{BASE_URL}{endpoint}", json=data, headers=headers)
        elif method.lower() == "get":
            response_backend = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response_backend.raise_for_status()
        retrieved_data = response_backend.json()
        
        # Merge backend data with provided template arguments, preferring backend data
        final_template_args = {**template_args, **retrieved_data}

        if success_template:
            return templates.TemplateResponse(success_template, {"request": request, **final_template_args})
        return retrieved_data # Return data if no template specified for success

    except requests.exceptions.HTTPError as e:
        #if e.response.status_code==401:
            #return RedirectResponse(url=redirect_url_on_unauthorized+"?message=Token scaduto o assente", status_code=302)
        detail = "Si è verificato un errore durante la richiesta al backend."
        if e.response is not None:
            try:
                error_response_json = e.response.json()
                if "detail" in error_response_json:
                    detail = error_response_json["detail"]
                elif "message" in error_response_json: # Some backends might use 'message'
                    detail = error_response_json["message"]
            except ValueError: # Not a JSON response
                detail = e.response.text or detail # Use raw text if available
        
        print(f"Errore HTTP durante la richiesta a {endpoint}: {e} - Dettaglio: {detail}")
        template_to_render = error_template if error_template else success_template # Fallback
        if template_to_render:
            return templates.TemplateResponse(template_to_render, {"request": request, "message": detail, **template_args})
        raise e # Re-raise if no error template is provided for a specific HTTP error

    except requests.exceptions.RequestException as e:
        print(f"Si è verificato un errore di connessione al backend per {endpoint}: {e}")
        template_to_render = error_template if error_template else success_template # Fallback
        if template_to_render:
            return templates.TemplateResponse(template_to_render, {"request": request, "message": f"Impossibile connettersi al servizio di backend: {e}", **template_args})
        raise e # Re-raise if no error template is provided for a connection error


# --- Endpoint Definitions ---

@app.get("/", response_class=HTMLResponse)
def init(request: Request):
    """Apertura Home Page"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/directlogin", response_class=HTMLResponse)
def directlogin(request: Request, message:str=""):
    return templates.TemplateResponse("login.html", {"request": request, "message":message})

@app.get("/directregister", response_class=HTMLResponse)
def directregister(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/directpassreset", response_class=HTMLResponse)
def directpassreset(request: Request): # Corrected function name
    return templates.TemplateResponse("passreset.html", {"request": request})

@app.post("/login")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    if not username.strip() or not password.strip():
        return templates.TemplateResponse("login.html", {"request": request, "message": "Username o password non validi."})
    
    data = {
        "username": username,
        "password": password
    }
    
    try:
        # Nota: La richiesta è ora POST e i dati sono JSON
        response_backend = requests.post(f"{BASE_URL}/login", json=data)
        response_backend.raise_for_status() # Lancia un'eccezione per status code 4xx/5xx
        retrieved_obj= response_backend.json
    except requests.exceptions.HTTPError as e:
        # Cattura specificamente errori HTTP e passa il dettaglio dal backend se disponibile
        detail = "Si è verificato un errore durante la richiesta al backend."
        if e.response is not None and e.response.json() is not None and "detail" in e.response.json():
            detail = e.response.json()["detail"]
        print(f"Errore HTTP durante la richiesta di login: {e} - Dettaglio: {detail}")
        return templates.TemplateResponse("login.html", {"request": request, "message": detail})
    except requests.exceptions.RequestException as e:
        print(f"Si è verificato un errore durante la richiesta: {e}")
        return templates.TemplateResponse("login.html", {"request": request, "message": f"Impossibile connettersi al servizio di backend: {e}"})

    # Se il login ha successo, il backend avrà impostato il cookie
    # Reindirizza l'utente a una pagina protetta
    response_redirect = RedirectResponse(url="/dashboard", status_code=302)
    # Copia i cookie dal backend alla risposta del frontend al browser
    for cookie_name, cookie_value in response_backend.cookies.items():
        response_redirect.set_cookie(key=cookie_name, value=cookie_value, httponly=True, samesite="lax", secure=True)
    
    return response_redirect

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    session_token = request.cookies.get("session_token")
    if not session_token:
        return RedirectResponse(url="/directlogin", status_code=302)
    
    # No backend call needed for simple dashboard display in this version
    return templates.TemplateResponse("dashboard.html", {"request": request, "message": "Benvenuto nella tua dashboard!"})


@app.get("/get_tab_content/ask", response_class=HTMLResponse)
async def get_ask_tab_content(request: Request):
    data = {
        "question": "placeholder",
        "tema": "placeholder",
        "tab_creation": 1
    }
    
    return await make_backend_request(
        request,
        method="post", # This seems to be a POST based on your original code for tab_creation=1
        endpoint="/ask",
        data=data,
        success_template="ask.html",
        error_template="ask.html",
    )


@app.get("/get_tab_content/leaderboard", response_class=HTMLResponse)
async def get_leaderboard_tab_content(request: Request): # Corrected function name for clarity
    return await make_backend_request(
        request,
        method="get",
        endpoint="/leaderboard",
        success_template="leaderboard.html",
        error_template="leaderboard.html",
        message="" # Ensure 'message' is passed if the template expects it
    )

@app.get("/get_tab_content/answer", response_class=HTMLResponse)
async def get_answer_tab_content(request: Request):
    data = {
        "domanda": "placeholder",
        "answer": "placeholder",
        "domandaid": 0,
        "tema": "placeholder",
        "tab_creation": 1
    }
    return await make_backend_request(
        request,
        method="post", # This seems to be a POST based on your original code for tab_creation=1
        endpoint="/answer",
        data=data,
        success_template="answer.html",
        error_template="answer.html"
    )

@app.post("/register")
async def register_post(request: Request, username: str = Form(...), password: str = Form(...), repeatpass: str = Form(...)):
    if not username.strip() or not password.strip():
        return templates.TemplateResponse("register.html", {"request": request, "message": "Username o password non validi."})
    
    data = {
        "username": username,
        "password": password,
        "repeatpass" :repeatpass
    }
    
    return await make_backend_request(
        request,
        method="post",
        endpoint="/register",
        data=data,
        success_template="register.html",
        error_template="register.html"
    )
@app.post("/passreset")
async def passreset(request: Request, newpass: str = Form(...), newpass2: str = Form(...)):
    if newpass != newpass2:
        return templates.TemplateResponse("passreset.html", {"request": request, "message": "Le password inserite sono diverse."})
    
    if not newpass.strip(): # Check both as they are already compared
        return templates.TemplateResponse("passreset.html", {"request": request, "message": "Password non valida."})
    
    data = {
        "newpass": newpass
    }

    response = await make_backend_request(
        request,
        method="post",
        endpoint="/passreset",
        data=data,
        success_template=None, # We'll redirect on success
        error_template="passreset.html"
    )

    if isinstance(response, HTMLResponse): # If it's an error from make_backend_request
        return response
    
    return RedirectResponse(url="/profile", status_code=302)

@app.post("/ask")
async def ask_post(request: Request, question: str = Form(...), tema: str = Form(...), temi_json:str =Form(...)):
    if not question.strip():
        # Re-creating the themes list correctly for error rendering
        listatemi=json.loads(temi_json)
        return templates.TemplateResponse("ask.html", {"request": request, "message": "La domanda non può essere vuota.", "temi": listatemi})

    data = {
        "question": question,
        "tema": tema,
        "tab_creation": 0
    }
    
    return await make_backend_request(
        request,
        method="post",
        endpoint="/ask",
        data=data,
        success_template="ask.html",
        error_template="ask.html",
    )

@app.post("/validate")
async def validate_post(request: Request, questionid: int = Form(...)): # Renamed to avoid clash
    data = {
        "questionid": questionid
    }
    
    return await make_backend_request(
        request,
        method="post",
        endpoint="/validate",
        data=data,
        #success_template="validate.html",
        #error_template="ask.html", # Error redirect to ask.html
    )

@app.post("/best")
async def best_post(request: Request, questionid: int = Form(...), answerid: int = Form(...)): # Renamed to avoid clash
    data = {
        "questionid": questionid,
        "answerid": answerid
    }
    
    return await make_backend_request(
        request,
        method="post",
        endpoint="/best",
        data=data,
        #success_template="human.html",
        #error_template="ask.html", # Error redirect to ask.html
    )

@app.post("/human")
async def human_post(request: Request, human: int = Form(...), questionid: int = Form(...)): # Renamed to avoid clash
    data = {
        "human": human,
        "questionid": questionid
    }
    
    return await make_backend_request(
        request,
        method="post",
        endpoint="/human",
        data=data,
        #success_template=None, # We'll redirect on success
        #error_template="ask.html", # Error redirect to ask.html
    )

    #if isinstance(response, HTMLResponse): # If it's an error from make_backend_request
    #    return response
    
    #return RedirectResponse(url="/get_tab_content/ask", status_code=302)

@app.post("/answer")
async def answer_post(
    request: Request,
    answer: str = Form(...),
    domanda: str = Form(...),
    domandaid: int = Form(...),
    tab_creation: int = Form(...),
    tema: str = Form(...)
):
    if not answer.strip():
        return templates.TemplateResponse("answer.html", {"request": request, "message": "La risposta non può essere vuota."})
    
    data = {
        "domanda": domanda,
        "answer": answer,
        "domandaid": domandaid,
        "tema": tema,
        "tab_creation": tab_creation
    }

    return await make_backend_request(
        request,
        method="post",
        endpoint="/answer",
        data=data,
        success_template="answer.html",
        error_template="answer.html"
    )

@app.get("/profile")
async def profile(request: Request):
    return await make_backend_request(
        request,
        method="get",
        endpoint="/profile",
        success_template="profile.html",
        error_template="dashboard.html"
    )

@app.post("/logout")
async def logout_post(request: Request):
    # This endpoint needs special handling because it clears the cookie
    session_token = request.cookies.get("session_token")
    headers = {}
    if session_token:
        headers["Cookie"] = f"session_token={session_token}"

    try:
        response_backend = requests.post(f"{BASE_URL}/logout", headers=headers)
        response_backend.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Errore durante il logout dal backend: {e}")
        # Gestisci l'errore, ma procedi comunque con la rimozione del cookie lato frontend
    
    # Rimuovi il cookie dal browser dell'utente (anche se il backend lo ha già invalidato)
    response_redirect = RedirectResponse(url="/directlogin", status_code=302)
    response_redirect.delete_cookie(key="session_token")
    return response_redirect


@app.get("/check_new_answers")
async def frontend_check_new_answers(request: Request):
    return await make_backend_request(
        request,
        method="get",
        endpoint="/check_new_answers"
    )
