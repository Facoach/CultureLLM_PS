import requests
from os import getenv
from classes.models import AnswerRequest, AnswerResponse, HumanizeRequest, HumanizeResponse, EvaluateRequest, EvaluateResponse


AI_CYAN_URL = getenv("AI_CYAN_URL", "http://all_in_one:8071/cyan")
AI_MAGENTA_URL = getenv("AI_MAGENTA_URL", "http://all_in_one:8071/magenta")
AI_GREEN_QT_URL = getenv("AI_GREEN_QT_URL", "http://all_in_one:8071/green_coherence_QT")


def generate_answer(data: AnswerRequest) -> AnswerResponse:
    payload = {"argomento": data.argomento, "livello": data.livello}
    try:
        r = requests.post(AI_CYAN_URL, json=payload)
        r.raise_for_status()
        data = r.json()
        risposta = data.get("risposta", "")
        raw = data.get("raw", "")
        return AnswerResponse(risposta=risposta, raw=raw)
    except Exception as e:
        return AnswerResponse(risposta=f"Errore IA: {e}", raw="")


def humanize_response(data: HumanizeRequest) -> HumanizeResponse:
    payload = {"llm_response": data.llm_response, "level": data.level}
    try:
        r = requests.post(AI_MAGENTA_URL, json=payload)
        r.raise_for_status()
        response = r.json()
        humanized = response.get("humanized_response", "")
        raw = response.get("raw", "")
        return HumanizeResponse(humanized_response=humanized, raw=raw)
    except Exception as e:
        return HumanizeResponse(humanized_response=f"Errore IA: {e}", raw="")


def check_theme_coherence(data: EvaluateRequest) -> EvaluateResponse:
    payload = {"question": data.question, "theme": data.theme}
    try:
        r = requests.post(AI_GREEN_QT_URL, json=payload)
        r.raise_for_status()
        resp = r.json()
        bool_val = resp.get("bool", "")
        return EvaluateResponse(bool=bool_val, raw=resp.get("raw", ""))
    except Exception as e:
        return EvaluateResponse(bool="Falso", raw=f"Errore IA: {e}")

