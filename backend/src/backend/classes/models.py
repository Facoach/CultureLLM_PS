from pydantic import BaseModel
from typing import List


#Modelli Pydantic
class RequestLogin(BaseModel):
    username:str
    password:str

class ResponseLogin(BaseModel):
    username:str
    id:int


class RequestRegister(BaseModel):
    username:str
    password:str
    repeatpass:str
    friend_code:str

class ResponseRegister(BaseModel):
    message:str
     

class RequestAsk(BaseModel):
    question:str
    tema:str
    tab_creation:bool

class ResponseAsk(BaseModel):
    message:str
    domande:List[list]
    temi:List


class RequestAnswer(BaseModel):
    domanda:str 
    answer:str
    domandaid:int
    tema:str
    tab_creation:bool

class ResponseAnswer(BaseModel):
    message:str
    payload:List


class RequestValidate(BaseModel):
    questionid:int

class ResponseValidate(BaseModel):
    message:str
    question:List
    answers:List[list]
    checked:bool
    best_answer:str


class RequestPassreset(BaseModel):
    newpass:str

class ResponsePassreset(BaseModel):
    message:str


class RequestHuman(BaseModel):
    human:int
    questionid:int

class ResponseHuman(BaseModel):
    message:str


class AnswerRequest(BaseModel):
    argomento: str
    livello:int

class AnswerResponse(BaseModel):
    risposta: str
    raw: str


class HumanizeRequest(BaseModel):
    llm_response: str
    level:int

class HumanizeResponse(BaseModel):
    humanized_response: str
    raw: str


class EvaluateRequest(BaseModel):
    question:str
    theme:str

class EvaluateResponse(BaseModel):
    bool: str
    raw: str


class ResponseCheckNewAnswers(BaseModel):
    new_answers:list

class ResponseLogout(BaseModel):
    message:str

class ResponseLeaderboard(BaseModel):
    leaderboard:List

class RequestBest(BaseModel):
    questionid:int
    answerid:int

class ResponseProfile(BaseModel):
    username:str
    score:int
    questions:int
    answers:int
    friend_code:str