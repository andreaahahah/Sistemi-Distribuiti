import logging
import yake
from typing import List
from config import Config

logger = logging.getLogger(__name__)
config = Config()

def extract_keywords_local(text: str, max_keywords: int = 10) -> List[str]:
    kw_extractor = yake.KeywordExtractor(
        lan=config.get("nlp", "language", default="it"),
        n=1,
        top=max_keywords,
        dedupLim=0.9
    )
    keywords = [kw.lower() for kw, _ in kw_extractor.extract_keywords(text)]
    logger.info(f"Estratte {len(keywords)} keywords locali")
    return keywords

def extract_keywords(text: str, title: str = "", use_google: bool = True, max_keywords: int = 10) -> List[str]:
    full_text = f"{title}.\n{text}".strip() if title else text.strip()
    if not full_text:
        logger.warning("Testo vuoto per estrazione keywords")
        return []

    if not use_google:
        return extract_keywords_local(full_text, max_keywords)

    try:
        from google.cloud import language_v1
        client = language_v1.LanguageServiceClient()
        document = language_v1.Document(content=full_text, type_=language_v1.Document.Type.PLAIN_TEXT)
        response = client.analyze_entities(document=document)
        keywords = [entity.name.lower() for entity in response.entities][:max_keywords]
        logger.info(f"Estratte {len(keywords)} keywords Google")
        return keywords
    except Exception as e:
        logger.warning(f"Errore Google NL API ({e}), fallback su YAKE locale")
        return extract_keywords_local(full_text, max_keywords)