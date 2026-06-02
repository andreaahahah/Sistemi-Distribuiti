import json
import logging
import os
import threading
from datetime import datetime
from typing import Optional

from config import Config
from exceptions import DatabaseError

logger = logging.getLogger(__name__)
config = Config()

USE_FIRESTORE = config.get("db", "use_firestore", default=False)
LOCAL_DB_FILE = os.path.join(os.path.dirname(__file__), config.get("db", "local_db_file", default="local_db.json"))

if USE_FIRESTORE:
    from google.cloud import firestore
    db_client = firestore.Client()
else:
    if not os.path.exists(LOCAL_DB_FILE):
        with open(LOCAL_DB_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False)


_lock = threading.Lock()


def generate_deterministic_id(title: str, date: Optional[str]) -> str:
    import hashlib
    unique_string = f"{title}_{date}".encode("utf-8")
    return hashlib.md5(unique_string).hexdigest()


def save_article(article_data: dict) -> tuple:
    custom_id = generate_deterministic_id(article_data["title"], article_data.get("date"))

    if USE_FIRESTORE:
        doc_ref = db_client.collection("articles").document(custom_id)
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            data["id"] = custom_id
            logger.info(f"Articolo già presente: {custom_id}")
            return data, False
        article_data["id"] = custom_id
        article_data["inserted_at"] = datetime.now().isoformat()
        doc_ref.set(article_data)
        logger.info(f"Articolo salvato su Firestore: {custom_id}")
        return article_data, True

    with _lock:
        try:
            with open(LOCAL_DB_FILE, "r", encoding="utf-8") as f:
                db = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            db = []

        for item in db:
            if item.get("id") == custom_id:
                logger.info(f"Articolo già presente: {custom_id}")
                return item, False

        article_data["id"] = custom_id
        article_data["inserted_at"] = datetime.now().isoformat()
        db.append(article_data)
        with open(LOCAL_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=4, ensure_ascii=False)

    logger.info(f"Articolo salvato localmente: {custom_id}")
    return article_data, True


def get_article_by_id(article_id: str) -> Optional[dict]:
    if USE_FIRESTORE:
        doc = db_client.collection("articles").document(article_id).get()
        if doc.exists:
            data = doc.to_dict()
            data["id"] = doc.id
            return data
        return None

    with _lock:
        with open(LOCAL_DB_FILE, "r", encoding="utf-8") as f:
            db = json.load(f)
        for article in db:
            if article.get("id") == article_id:
                return article
    return None


def search_articles_by_keyword(keyword: str) -> list:
    keyword = keyword.lower()
    results = []

    if USE_FIRESTORE:
        docs = db_client.collection("articles").where("keywords", "array_contains", keyword).stream()
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            results.append(data)
    else:
        with _lock:
            try:
                with open(LOCAL_DB_FILE, "r", encoding="utf-8") as f:
                    db = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                db = []

        for article in db:
            keywords_lower = [kw.lower() for kw in article.get("keywords", [])]
            title_lower = article.get("title", "").lower()
            if keyword in keywords_lower or keyword in title_lower:
                results.append(article)

    logger.info(f"Ricerca '{keyword}': {len(results)} risultati")
    return results


def get_latest_articles(limit: int = 5) -> list:
    results = []

    if USE_FIRESTORE:
        docs = db_client.collection("articles").order_by("inserted_at", direction=firestore.Query.DESCENDING).limit(limit).stream()
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            results.append(data)
    else:
        try:
            with _lock:
                with open(LOCAL_DB_FILE, "r", encoding="utf-8") as f:
                    db = json.load(f)
            db.sort(key=lambda x: x.get("inserted_at", ""), reverse=True)
            results = db[:limit]
        except (json.JSONDecodeError, FileNotFoundError):
            logger.warning("Database locale non leggibile")

    return results


def update_article_keywords(article_id: str, keywords: list) -> bool:
    if USE_FIRESTORE:
        doc_ref = db_client.collection("articles").document(article_id)
        doc = doc_ref.get()
        if not doc.exists:
            logger.warning(f"update_article_keywords: articolo non trovato su Firestore: {article_id}")
            return False
        doc_ref.update({
            "keywords": keywords,
            "nlp_status": "DONE",
        })
        logger.info(f"Keyword aggiornate su Firestore per {article_id}")
        return True

    with _lock:
        try:
            with open(LOCAL_DB_FILE, "r", encoding="utf-8") as f:
                db = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            logger.warning("update_article_keywords: database locale non leggibile")
            return False

        for article in db:
            if article.get("id") == article_id:
                article["keywords"] = keywords
                article["nlp_status"] = "DONE"
                with open(LOCAL_DB_FILE, "w", encoding="utf-8") as f:
                    json.dump(db, f, indent=4, ensure_ascii=False)
                logger.info(f"Keyword aggiornate localmente per {article_id}")
                return True

    logger.warning(f"update_article_keywords: articolo non trovato nel DB locale: {article_id}")
    return False