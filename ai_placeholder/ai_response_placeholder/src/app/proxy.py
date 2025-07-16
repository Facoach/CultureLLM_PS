import requests
from os import getenv
from fastapi import FastAPI, Request
from pydantic import BaseModel



MODEL_NAME = getenv("MODEL_NAME", "gemma3:1b")
OLLAMA_URL = getenv("OLLAMA_URL", "http://ollama:11434/api")
lista_livelli =["rispondi come risponderebbe uno studente di scuola media alla domanda:", "rispondi come risponderebbe uno studente di scuola superiore alla domanda:", "rispondi come risponderebbe un adulto alla domanda:"]

app = FastAPI()

class AnswerRequest(BaseModel):
    argomento: str
    livello:int

class AnswerResponse(BaseModel):
    risposta: str
    raw: str

@app.get("/health")
def health() -> dict:
    """Verifica lo stato di salute dell'applicazione."""
    return {"status": "ok"}


@app.post("/answer")
def answer(data: AnswerRequest):

    param={
                "model": MODEL_NAME,
                "messages":[{
                    "role":"user", 
                    "content":f"{lista_livelli[data.livello-1]} '{data.argomento}'. Non superare i 250 caratteri (spazi inclusi) e restituisci unicamente la risposta"
                }], 
                "stream":False
            }
            # Invia la richiesta ed estrare la risposta
    response = requests.post(f"{OLLAMA_URL}/chat", json=param)
    response.raise_for_status()
    ollama_response = response.json().get("message", "").get("content", "")
    print(ollama_response)

    return AnswerResponse(risposta=ollama_response, raw=ollama_response)