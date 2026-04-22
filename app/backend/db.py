import json
import os
import hashlib
from datetime import datetime

USE_FIRESTORE = False
LOCAL_DB_FILE = "local_db.json"

if USE_FIRESTORE:
    from google.cloud import firestore

    db_client = firestore.Client()
else:
    if not os.path.exists(LOCAL_DB_FILE):
        with open(LOCAL_DB_FILE, 'w') as f:
            json.dump([], f)


def generate_deterministic_id(title, date):
    """Genera un ID univoco basato su Titolo e Data."""
    unique_string = f"{title}_{date}".encode('utf-8')
    return hashlib.md5(unique_string).hexdigest()


def save_article(article_data):
    """
    Salva l'articolo o restituisce quello esistente.
    Ritorna una tupla: (dati_articolo, is_new_boolean)
    """
    custom_id = generate_deterministic_id(article_data['title'], article_data['date'])
    article_data['id'] = custom_id

    if USE_FIRESTORE:
        doc_ref = db_client.collection("articles").document(custom_id)
        doc = doc_ref.get()

        if doc.exists:
            # L'articolo esiste già! Lo restituiamo senza fare altre scritture
            return doc.to_dict(), False
        else:
            # È un articolo nuovo, lo salviamo
            article_data['inserted_at'] = datetime.now().isoformat()
            doc_ref.set(article_data)
            return article_data, True

    else:
        with open(LOCAL_DB_FILE, 'r') as f:
            db = json.load(f)

        # Cerchiamo se l'ID esiste già nell'array locale
        for item in db:
            if item.get('id') == custom_id:
                # Trovato! Restituiamo quello già presente
                return item, False

        # Se il ciclo finisce senza trovarlo, è nuovo
        article_data['inserted_at'] = datetime.now().isoformat()
        db.append(article_data)
        with open(LOCAL_DB_FILE, 'w') as f:
            json.dump(db, f, indent=4)

        return article_data, True

def search_articles_by_keyword(keyword):
    """Cerca articoli che contengono una specifica keyword."""
    keyword = keyword.lower()
    results = []

    if USE_FIRESTORE:
        # Logica Cloud: Query Firestore iper-efficiente
        docs = db_client.collection("articles").where("keywords", "array_contains", keyword).stream()
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            results.append(data)
    else:
        # Logica Locale: Scansione lineare (va bene solo per test!)
        with open(LOCAL_DB_FILE, 'r') as f:
            db = json.load(f)
        for article in db:
            # Controlliamo se la keyword cercata è tra quelle estratte (case-insensitive)
            keywords_lower = [kw.lower() for kw in article.get('keywords', [])]
            if keyword in keywords_lower:
                results.append(article)

    return results


# Aggiungi questa funzione in fondo a db.py

def get_latest_articles(limit=5):
    """Restituisce gli ultimi articoli caricati, ordinati per data di inserimento."""
    results = []

    if USE_FIRESTORE:
        # Logica Cloud: Usiamo order_by e limit per non leggere tutto il DB!
        docs = db_client.collection("articles").order_by("inserted_at", direction=firestore.Query.DESCENDING).limit(
            limit).stream()
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            results.append(data)
    else:
        # Logica Locale
        try:
            with open(LOCAL_DB_FILE, 'r') as f:
                db = json.load(f)
            # Ordiniamo l'array locale basandoci sul campo 'inserted_at' (dal più recente al più vecchio)
            db.sort(key=lambda x: x.get('inserted_at', ''), reverse=True)
            # Prendiamo solo i primi 'limit' elementi
            results = db[:limit]
        except (json.JSONDecodeError, FileNotFoundError):
            pass  # DB vuoto

    return results