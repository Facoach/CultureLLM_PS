from pydantic import BaseModel
from typing import List


#pydantic models
class RequestLogin(BaseModel):
    username:str
    password:str

class RequestRegister(BaseModel):
    username:str
    password:str
     
class RequestAsk(BaseModel):
    question:str
    tema:str
    tab_creation:bool

class ResponseLogin(BaseModel):
    username:str
    id:int

class RequestAnswer(BaseModel):
    domanda:str 
    answer:str
    domandaid:int
    tema:str
    tab_creation:bool

class RequestRegister(BaseModel):
    username:str
    password:str
    repeatpass:str
    friend_code: str

class ResponseAnswer(BaseModel):
    message:str
    payload:List

class ResponseAsk(BaseModel):
    message:str
    domande:List[list]
    temi: List

class ResponseProfile(BaseModel):
    username:str
    score: int
    questions: int
    answers: int
    friend_code: str

class RequestValidate(BaseModel):
    questionid:int

class ResponseValidate(BaseModel):
    message:str
    question:List
    answers:List[list]
    checked: bool
    best_answer: str

class RequestBest(BaseModel):
    questionid:int
    answerid:int

class RequestPassreset(BaseModel):
    newpass:str

class RequestHuman(BaseModel):
    human:int
    questionid:int

class ResponseLeaderboard(BaseModel):
    leaderboard:List

class ResponseHuman(BaseModel):
    message: str