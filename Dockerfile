# Usa Python 3.11 slim per un'immagine leggera e sicura (best practice GCP)
FROM python:3.11-slim

# Variabili d'ambiente per il Cloud:
# 1. PYTHONUNBUFFERED=1 assicura che i log di Python arrivino direttamente a Cloud Logging senza buffering
# 2. PYTHONDONTWRITEBYTECODE=1 impedisce a Python di creare file .pyc
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# Directory di lavoro all'interno del container
WORKDIR /workspace

# Copia i requirements e installa le dipendenze
# Fare questo passo prima del resto del codice ci permette di sfruttare la cache dei layer di Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia il codice (backend e frontend assieme, monolite web)
COPY app/ ./app/

# Sposta la WORKDIR nella cartella del backend per permettere a gunicorn
# di risolvere correttamente gli import locali come `import config`, `import db`
WORKDIR /workspace/app/backend

# Esposizione porta (informativa, Cloud Run inietta PORT)
EXPOSE 8080

# Avvio con Gunicorn (best practice per produzione Flask)
# - workers: 1 (Deleghiamo a Cloud Run la scalabilità orizzontale)
# - threads: 8 (Permette di gestire multiple richieste simultanee attendendo I/O database)
# - timeout: 0 (Cloud Run gestisce i timeout globali)
# Eseguiamo tramite `exec` per gestire correttamente i segnali di stop (SIGTERM)
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0 main:app
