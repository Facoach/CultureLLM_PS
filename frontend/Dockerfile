# immagine base Python
FROM python:3.9-slim

# /app è la directory all'interno del container
WORKDIR /app

# Copia il file requirements.txt in /app
COPY frontend/requirements.txt /app

# Installa le dipendenze dal requirements.txt
RUN apt-get update && apt-get install -y curl
RUN pip install -r requirements.txt

# Copia il file frontend.py e i templates nella directory del container
COPY frontend/src/frontend/frontend.py /app
COPY frontend/src/frontend/__init__.py /app
COPY frontend/templates /app/templates
COPY frontend/static /app/static


# imposta l'url del backend come variabile d'ambiente
ENV BASE_URL=http://backend:8003

# Espone la porta su cui il server frontend sarà in ascolto
EXPOSE 8001

# Comando per avviare l'applicazione del frontend
CMD ["uvicorn", "frontend:app","--host","0.0.0.0","--port","8001"]