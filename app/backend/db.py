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
            return doc.to_dict(), False
        else:
            article_data['inserted_at'] = datetime.now().isoformat()
            doc_ref.set(article_data)
            return article_data, True

    else:
        with open(LOCAL_DB_FILE, 'r') as f:
            db = json.load(f)

        for item in db:
            if item.get('id') == custom_id:
                return item, False

        article_data['inserted_at'] = datetime.now().isoformat()
        db.append(article_data)
        with open(LOCAL_DB_FILE, 'w') as f:
            json.dump(db, f, indent=4)

        return article_data, True

def search_articles_by_keyword(keyword):
    keyword = keyword.lower()
    results = []

    if USE_FIRESTORE:
        docs = db_client.collection("articles").where("keywords", "array_contains", keyword).stream()
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            results.append(data)
    else:
        with open(LOCAL_DB_FILE, 'r') as f:
            db = json.load(f)
        for article in db:
            keywords_lower = [kw.lower() for kw in article.get('keywords', [])]
            title_lower = article.get('title', '').lower()
            # Cerca sia nelle keyword NLP sia nel titolo
            if keyword in keywords_lower or keyword in title_lower:
                results.append(article)

    return results



def get_latest_articles(limit=5):
    """Restituisce gli ultimi articoli caricati, ordinati per data di inserimento."""
    results = []

    if USE_FIRESTORE:
        docs = db_client.collection("articles").order_by("inserted_at", direction=firestore.Query.DESCENDING).limit(
            limit).stream()
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            results.append(data)
    else:
        try:
            with open(LOCAL_DB_FILE, 'r') as f:
                db = json.load(f)
            db.sort(key=lambda x: x.get('inserted_at', ''), reverse=True)
            results = db[:limit]
        except (json.JSONDecodeError, FileNotFoundError):
            pass

    return results