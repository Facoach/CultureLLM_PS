import requests
from os import getenv
from fastapi import FastAPI, Request
from pydantic import BaseModel


MODEL_NAME = getenv("MODEL_NAME", "gemma3:1b")
OLLAMA_URL = getenv("OLLAMA_URL", "http://ollama:11434/api")


app = FastAPI()

class EvaluateRequest(BaseModel):
    question:str
    theme:str

class EvaluateResponse(BaseModel):
    bool: bool
    raw: str



@app.get("/health")
def health() -> dict:
    """Verifica lo stato di salute dell'applicazione."""
    return {"status": "ok"}


@app.post("/evaluate")
def evaluate(data: EvaluateRequest):

    param={
            "model": MODEL_NAME, 
            "messages":[{
                "role":"user", 
                "content":f"ritieni che la domanda {data.question} sia coerente col tema {data.theme}? Rispondi UNICAMENTE con un voto da 1 a 10 per la coerenza, senza spiegazioni aggiuntive o caratteri non numerici"
            }], 
            "stream":False
        }
    response= requests.post(f"{OLLAMA_URL}/chat", json=param)
    response.raise_for_status()
    ollama_response = response.json().get("message", "").get("content", "")
    print(ollama_response)
    

    if int(ollama_response.strip())>=5:
        ret=1
    else: 
        ret=0

    return EvaluateResponse(bool=ret, raw=ollama_response)