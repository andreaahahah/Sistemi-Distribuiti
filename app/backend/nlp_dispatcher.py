import logging
import json

from nlp import extract_keywords
from db import update_article_keywords

logger = logging.getLogger(__name__)


def dispatch_nlp_task(article_id: str, plain_text: str) -> None:
    logger.info(f"[Dispatcher] Avvio task NLP per articolo: {article_id}")
    _run_local(article_id, plain_text)


def _run_local(article_id: str, plain_text: str) -> None:
    try:
        keywords = extract_keywords(plain_text)
        update_article_keywords(article_id, keywords)
        logger.info(
            f"[Dispatcher] Task NLP completato per {article_id}: "
            f"{len(keywords)} keyword estratte."
        )
    except Exception as e:
        logger.exception(
            f"[Dispatcher] Errore durante il task NLP per {article_id}: {e}"
        )