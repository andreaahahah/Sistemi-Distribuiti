# WikiNews Cloud Explorer

Applicazione web per raccogliere, classificare e cercare notizie dal sito [Wikimedia Italia](https://www.wikimedia.it/), sviluppata come progetto per il corso di **Sistemi Distribuiti e Cloud Computing** (Università della Calabria).

Il sistema permette di caricare articoli (manualmente o tramite scraping automatico dell'URL), estrarne le keyword con NLP e renderli ricercabili attraverso un motore semantico.

## Stack

| Componente | Tecnologia |
|---|---|
| Backend | Python 3.11, Flask, Gunicorn |
| Frontend | HTML5, CSS, JavaScript vanilla |
| Database | Google Cloud Firestore (prod) / JSON locale (dev) |
| NLP | Google Cloud Natural Language API + YAKE (fallback) |
| Auth | Firebase Authentication |
| Messaging | Google Cloud Pub/Sub (dispatching task NLP) |
| Deploy | Docker → Google Cloud Run |

## Struttura del progetto

```
app/
├── backend/
│   ├── main.py              # Entry point Flask, rotte API
│   ├── scraper.py           # Scraping articoli da Wikimedia
│   ├── nlp.py               # Estrazione keyword (Google NL + YAKE)
│   ├── nlp_dispatcher.py    # Dispatching asincrono (Pub/Sub o thread)
│   ├── db.py                # Layer persistenza (Firestore / JSON)
│   ├── related_search.py    # Ricerca correlata (3 strategie)
│   ├── config.py            # Configurazione centralizzata (Singleton)
│   ├── config.yaml          # Parametri applicativi
│   └── exceptions.py        # Eccezioni custom
└── frontend/
    ├── index.html            # Homepage (SPA)
    ├── script.js             # Logica client-side + Firebase Auth
    ├── style.css             # Stile (design editoriale)
    └── templates/
        └── article.html      # Pagina articolo (SSR Jinja2)
```

## Setup locale

### Prerequisiti

- Docker
- Un progetto GCP con Firestore e Natural Language API abilitati
- File `credentials.json` (Service Account key) nella root del progetto

### Configurazione

```bash
# Imposta le variabili d'ambiente
source set_env.sh

# Build + avvio container
./run_docker.sh
```

L'app sarà disponibile su `http://localhost:8080`.

Per sviluppo senza GCP, modifica `app/backend/config.yaml`:

```yaml
nlp:
  use_google: false    # usa YAKE locale
db:
  use_firestore: false # usa local_db.json
```

### Senza Docker

```bash
pip install -r requirements.txt
cd app/backend
python main.py
```

## Deploy su Cloud Run

```bash
# Build e push immagine
gcloud builds submit --tag gcr.io/$GOOGLE_CLOUD_PROJECT/wikinews-cloud-explorer

# Deploy
gcloud run deploy wikinews-cloud-explorer \
  --image gcr.io/$GOOGLE_CLOUD_PROJECT/wikinews-cloud-explorer \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT
```

## Come funziona

1. L'utente si registra/logga tramite Firebase Auth
2. Carica un articolo: inserendo l'URL (scraping automatico) oppure compilando il form manuale
3. Il backend salva l'articolo su Firestore e dispatcha un task NLP in background
4. Il motore NLP estrae le keyword (Google NL API, con fallback su YAKE se non disponibile)
5. Il frontend fa polling sullo stato e mostra le keyword appena pronte
6. Le keyword alimentano la ricerca: match diretto + ricerca correlata (substring, Jaro-Winkler, matching semantico)

## Variabili d'ambiente

| Variabile | Descrizione | Default |
|---|---|---|
| `GOOGLE_CLOUD_PROJECT` | ID progetto GCP | `sistemi-distribuiti-nuovo` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path al file credentials | — |
| `USE_PUBSUB` | Abilita Pub/Sub per task NLP | `false` |
| `PORT` | Porta del server | `8080` |



