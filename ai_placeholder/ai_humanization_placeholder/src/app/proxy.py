import requests
from os import getenv
from fastapi import FastAPI, Request
from pydantic import BaseModel
from requests.exceptions import RequestException
from requests import get, post


MODEL_NAME = getenv("MODEL_NAME", "gemma3:1b")
OLLAMA_URL = getenv("OLLAMA_URL", "http://ollama:11434/api")


app = FastAPI()

class HumanizeRequest(BaseModel):
    llm_response: str
    level:int

class HumanizeResponse(BaseModel):
    humanized_response: str
    raw: str

@app.get("/health")
def health() -> dict:
    """Verifica lo stato di salute dell'applicazione."""
    return {"status": "ok"}


@app.post("/humanize")
def humanize(data: HumanizeRequest):

    param={
            "model": MODEL_NAME, 
            "messages":[{
                "role":"user", 
                "content":f"modifica, se necessario, la seguente frase rendendola più 'umana', rimuovendo le caratteristiche tipiche delle ia: '{data.llm_response}'. Restituisci UNICAMENTE la frase modificata"
            }], 
            "stream":False
        }
    response= requests.post(f"{OLLAMA_URL}/chat", json=param)
    response.raise_for_status()
    ollama_response = response.json().get("message", "").get("content", "")
    print(ollama_response)

    return HumanizeResponse(humanized_response=ollama_response, raw=data.llm_response)


@app.on_event("startup")
def pull() -> None:
    """Avvia, se non è presente, il download del modello di Ollama"""
    modello=False
    # Richiede la lista dei modelli attualmente disponibili su Ollama 
    # e cerca tra i modelli disponibili quello desiderato
    try:
        response= get(f"{OLLAMA_URL}/tags")
        response.raise_for_status()
        data=response.json()
        if "models" in data:
            for model in data["models"]:
                if model["name"] == MODEL_NAME:
                    modello=True
    except RequestException as e:
        print(f"Errore durante la comunicazione con l'api di Ollama: {e}")
        raise
    # Se il modello non è presente, avvia il download
    if not modello:
        data={"model": MODEL_NAME}
        try:
            response= post(f"{OLLAMA_URL}/pull", json=data)
            response.raise_for_status()
        except RequestException as e:
            print(f"Errore durante la comunicazione con l'api di Ollama: {e}")
            raise