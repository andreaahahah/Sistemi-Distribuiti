import logging
import json
import os
import threading
from nlp import extract_keywords
from db import update_article_keywords
logger = logging.getLogger(__name__)
USE_PUBSUB = os.environ.get("USE_PUBSUB", "false").lower() == "true"
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "sistemi-distribuiti-nuovo")
TOPIC_ID = os.environ.get("PUBSUB_TOPIC_ID", "nlp-tasks")
publisher = None
if USE_PUBSUB:
    try:
        from google.cloud import pubsub_v1
        publisher = pubsub_v1.PublisherClient()
        logger.info(f"Pub/Sub abilitato sul topic: {TOPIC_ID}")
    except ImportError:
        logger.warning("google-cloud-pubsub non installato, fallback locale.")
        USE_PUBSUB = False
def dispatch_nlp_task(article_id: str, plain_text: str, title: str = "") -> None:
    if USE_PUBSUB and publisher:
        try:
            topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)
            payload = {"article_id": article_id, "text": plain_text, "title": title}
            message_data = json.dumps(payload).encode("utf-8")
            future = publisher.publish(topic_path, data=message_data)
            message_id = future.result(timeout=5)
            logger.info(f"[Dispatcher] Evento NLP pubblicato su Pub/Sub! Message ID: {message_id} per articolo: {article_id}")
            return
        except Exception as e:
            logger.error(f"[Dispatcher] Errore pubblicazione Pub/Sub per {article_id}: {e}. Fallback locale.")
    logger.info(f"[Dispatcher] Avvio task NLP locale (Thread separato) per articolo: {article_id}")
    threading.Thread(target=_run_local, args=(article_id, plain_text, title), daemon=True).start()
def _run_local(article_id: str, plain_text: str, title: str = "") -> None:
    try:
        keywords = extract_keywords(plain_text, title=title)
        update_article_keywords(article_id, keywords)
        logger.info(
            f"[Dispatcher] Task NLP completato per {article_id}: "
            f"{len(keywords)} keyword estratte."
        )
    except Exception as e:
        logger.exception(
            f"[Dispatcher] Errore durante il task NLP per {article_id}: {e}"
        )