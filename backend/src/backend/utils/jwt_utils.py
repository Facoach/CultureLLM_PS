from os import getenv
from typing import Optional
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError


# Configurazione parametri JWT
SECRET_KEY = getenv("JWT_SECRET_KEY", "SOSTITUISCI_QUESTO_VALORE")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crea un token di accesso JWT, con possibilità di specificare la scadenza
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[int]:
    """
    Decodifica un token di accesso JWT e restituisce l'id utente (come int) o None se il token non è valido.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            return None
        return int(user_id)
    except JWTError:
        return None
