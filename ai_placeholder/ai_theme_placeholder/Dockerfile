# immagine base Python
FROM python:3.9-slim

# /app è la directory all'interno del container
WORKDIR /app

# Copia il file requirements.txt in /app
COPY ai_placeholder/ai_theme_placeholder/requirements.txt /app

# Installa le dipendenze dal requirements.txt
RUN apt-get update && apt-get install -y curl
RUN pip install -r requirements.txt

# Copia il file frontend.py e i templates nella directory del container
COPY ai_placeholder/ai_theme_placeholder/src/app/proxy.py /app
COPY ai_placeholder/ai_theme_placeholder/src/app/__init__.py /app

# imposta l'url del backend come variabile d'ambiente
ENV OLLAMA_URL=http://ollama:11434/api 
ENV MODEL_NAME=gemma3:1b

# Espone la porta su cui il server frontend sarà in ascolto
EXPOSE 8075

# Comando per avviare l'applicazione del frontend
CMD ["uvicorn", "proxy:app","--host","0.0.0.0","--port","8075"]