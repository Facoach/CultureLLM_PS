# Immagine base Python
FROM python:3.9-slim

# /app è la directory di lavoro all'interno del container
WORKDIR /app

# Copia il file requirements.txt nella directory di lavoro
COPY backend/requirements.txt /app

# Installa le librerie necessarie per i requirements
RUN apt-get update
RUN apt-get install -y libmariadb-dev gcc build-essential curl

# Installa le dipendenze dal requirements.txt
RUN pip install -r requirements.txt

# Copia i file necessari nella directory di lavoro
COPY backend/src/backend /app

# Imposta host e porta del backend come variabili d'ambiente
ENV HOST_DB=mariadb-cinema
ENV PORT_DB=3306

# Espone la porta su cui il server backend sarà in ascolto
EXPOSE 8003

# Comando per avviare l'applicazione  del backend
CMD ["uvicorn", "backend:app","--host","0.0.0.0","--port","8003"]