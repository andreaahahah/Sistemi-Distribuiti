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
    from google.cloud.firestore_v1.base_query import FieldFilter, Or, And
    db_client = firestore.Client()
else:
    if not os.path.exists(LOCAL_DB_FILE):
        with open(LOCAL_DB_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False)
_lock = threading.Lock()
def generate_deterministic_id(title: str, date: Optional[str], user_id: Optional[str] = None, is_public: bool = True) -> str:
    import hashlib
    if is_public:
        unique_string = f"{title}_{date}".encode("utf-8")
    else:
        unique_string = f"{title}_{date}_{user_id}".encode("utf-8")
    return hashlib.sha256(unique_string).hexdigest()[:32]
def save_article(article_data: dict) -> tuple:
    custom_id = generate_deterministic_id(article_data["title"], article_data.get("date"), article_data.get("user_id"), article_data.get("is_public", True))
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
def get_article_by_id(article_id: str, current_user_id: Optional[str] = None) -> Optional[dict]:
    if USE_FIRESTORE:
        doc = db_client.collection("articles").document(article_id).get()
        if doc.exists:
            data = doc.to_dict()
            is_public = data.get("is_public", True)
            owner_id = data.get("user_id")
            if not is_public and owner_id != current_user_id:
                return None
            data["id"] = doc.id
            return data
        return None
    with _lock:
        try:
            with open(LOCAL_DB_FILE, "r", encoding="utf-8") as f:
                db = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            db = []
        for article in db:
            if article.get("id") == article_id:
                is_public = article.get("is_public", True)
                owner_id = article.get("user_id")
                if not is_public and owner_id != current_user_id:
                    return None
                return article
    return None
def search_articles_by_keyword(keyword: str, current_user_id: Optional[str] = None) -> list:
    keyword = keyword.lower()
    results = []
    if USE_FIRESTORE:
        keyword_filter = FieldFilter("keywords", "array_contains", keyword)
        if current_user_id:
            access_filter = Or(filters=[
                FieldFilter("is_public", "==", True), 
                FieldFilter("user_id", "==", current_user_id)
            ])
            final_filter = And(filters=[keyword_filter, access_filter])
        else:
            final_filter = And(filters=[
                keyword_filter, 
                FieldFilter("is_public", "==", True)
            ])
        docs = db_client.collection("articles").where(filter=final_filter).stream()
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
            is_public = article.get("is_public", True)
            owner_id = article.get("user_id")
            if not is_public and owner_id != current_user_id:
                continue
            keywords_lower = [kw.lower() for kw in article.get("keywords", [])]
            if keyword in keywords_lower:
                results.append(article)
    logger.info(f"Ricerca '{keyword}': {len(results)} risultati")
    return results
def get_latest_articles(limit: int = 5, current_user_id: Optional[str] = None) -> list:
    results = []
    if USE_FIRESTORE:
        if current_user_id:
            access_filter = Or(filters=[
                FieldFilter("is_public", "==", True), 
                FieldFilter("user_id", "==", current_user_id)
            ])
        else:
            access_filter = FieldFilter("is_public", "==", True)
        docs = db_client.collection("articles").where(filter=access_filter).order_by("inserted_at", direction=firestore.Query.DESCENDING).limit(limit).stream()
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
            for article in db:
                is_public = article.get("is_public", True)
                owner_id = article.get("user_id")
                if is_public or owner_id == current_user_id:
                    results.append(article)
                    if len(results) >= limit:
                        break
        except (json.JSONDecodeError, FileNotFoundError):
            logger.warning("Database locale non leggibile")
    return results
def get_user_articles(user_id: str, limit: int = 50) -> list:
    results = []
    if USE_FIRESTORE:
        docs = (
            db_client.collection("articles")
            .where(filter=FieldFilter("user_id", "==", user_id))
            .order_by("inserted_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
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
            if article.get("user_id") == user_id:
                results.append(article)
        results.sort(key=lambda x: x.get("inserted_at", ""), reverse=True)
        results = results[:limit]
    logger.info(f"Articoli utente '{user_id}': {len(results)} risultati")
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