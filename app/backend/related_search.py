import logging
import time
import jellyfish
from typing import Set, Dict, Optional
from config import Config

logger = logging.getLogger(__name__)
config = Config()

# Cache per i risultati NLP delle keyword (evita chiamate ripetute)
_entity_cache = {"key": None, "data": {}, "timestamp": 0}
ENTITY_CACHE_TTL = 600  # 10 minuti


def _substring_matches(query: str, keywords: Set[str]) -> Dict[str, float]:
    """Strategia 1: matching per sottostringhe e prefissi comuni.
    Cattura varianti morfologiche (es. 'sicilia' -> 'siciliano').
    """
    query_lower = query.lower().strip()
    matches = {}

    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower == query_lower:
            continue

        # La query è contenuta nella keyword
        if len(query_lower) >= 3 and query_lower in kw_lower:
            ratio = len(query_lower) / len(kw_lower)
            matches[kw] = 0.85 * ratio
            continue

        # La keyword è contenuta nella query
        if len(kw_lower) >= 3 and kw_lower in query_lower:
            ratio = len(kw_lower) / len(query_lower)
            matches[kw] = 0.80 * ratio
            continue

        # Prefisso comune (almeno 4 caratteri per qualità)
        common = 0
        for c1, c2 in zip(query_lower, kw_lower):
            if c1 == c2:
                common += 1
            else:
                break
        if common >= 4:
            score = 0.6 * (common / max(len(query_lower), len(kw_lower)))
            matches[kw] = score

    return matches


def _similarity_matches(query: str, keywords: Set[str], threshold: float = 0.78) -> Dict[str, float]:
    """Strategia 2: similarità stringa con Jaro-Winkler.
    Cattura parole simili e typo (es. 'roma' -> 'romano').
    """
    query_lower = query.lower().strip()
    matches = {}

    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower == query_lower:
            continue

        jw_score = jellyfish.jaro_winkler_similarity(query_lower, kw_lower)

        if jw_score >= threshold:
            matches[kw] = jw_score * 0.75

    return matches


def _nlp_semantic_matches(query: str, keywords: Set[str]) -> Dict[str, float]:
    """Strategia 3: matching semantico via Google Cloud Natural Language API.
    Analizza i tipi di entità (LOCATION, PERSON, ORG, etc.) per trovare
    keyword dello stesso dominio semantico (es. 'sicilia' -> 'palermo', 'italia').
    """
    try:
        from google.cloud import language_v1
        client = language_v1.LanguageServiceClient()

        # Analizza la query con contesto per migliore riconoscimento entità
        query_context = f"Questo articolo tratta di: {query}"
        query_doc = language_v1.Document(
            content=query_context,
            type_=language_v1.Document.Type.PLAIN_TEXT,
            language="it"
        )
        query_response = client.analyze_entities(document=query_doc)

        if not query_response.entities:
            logger.info(f"[Related] NLP: nessuna entità trovata per '{query}'")
            return {}

        # Tipi di entità della query
        query_types = set()
        for entity in query_response.entities:
            query_types.add(entity.type_)

        logger.info(f"[Related] NLP query entity types: {[str(t) for t in query_types]}")

        # Analizza le keyword in batch (con cache)
        global _entity_cache
        now = time.time()
        cache_key = frozenset(keywords)

        if (_entity_cache.get("key") == cache_key and
                (now - _entity_cache["timestamp"]) < ENTITY_CACHE_TTL):
            entity_type_map = _entity_cache["data"]
            logger.info("[Related] NLP: uso cache entità keyword")
        else:
            entity_type_map = {}
            kw_list = list(keywords)

            # Batch da max 80 keyword per chiamata API
            for i in range(0, len(kw_list), 80):
                batch = kw_list[i:i + 80]
                batch_text = ". ".join(batch) + "."

                if len(batch_text.strip()) < 5:
                    continue

                kw_doc = language_v1.Document(
                    content=batch_text,
                    type_=language_v1.Document.Type.PLAIN_TEXT,
                    language="it"
                )
                kw_response = client.analyze_entities(document=kw_doc)

                for entity in kw_response.entities:
                    name_lower = entity.name.lower()
                    for kw in batch:
                        if kw.lower() == name_lower:
                            entity_type_map[kw] = entity.type_

            _entity_cache = {"key": cache_key, "data": entity_type_map, "timestamp": now}
            logger.info(f"[Related] NLP: analizzate {len(entity_type_map)} keyword")

        # Trova keyword con lo stesso tipo di entità della query
        matches = {}
        for kw, kw_type in entity_type_map.items():
            if kw.lower() == query.lower():
                continue
            if kw_type in query_types:
                matches[kw] = 0.9
                logger.debug(f"[Related] NLP semantic match: '{kw}' (tipo: {kw_type})")

        logger.info(f"[Related] NLP: {len(matches)} keyword semanticamente correlate")
        return matches

    except ImportError:
        logger.warning("[Related] google-cloud-language non installato")
        return {}
    except Exception as e:
        logger.error(f"[Related] Errore NLP semantic match: {e}")
        return {}


def find_related_articles(query: str, current_user_id: Optional[str],
                          direct_result_ids: Set[str], max_related: int = 8) -> Dict:
    """Funzione principale: trova articoli correlati alla query.

    Usa 3 strategie in cascata per massima qualità:
    1. Substring matching (varianti morfologiche)
    2. Jaro-Winkler similarity (parole simili, typo)
    3. Google NL API entity type (relazioni semantiche)
    """
    from db import get_all_unique_keywords, search_articles_by_keywords

    all_keywords = get_all_unique_keywords()
    query_lower = query.lower().strip()

    # Rimuovi match esatto dai candidati
    candidates = {kw for kw in all_keywords if kw.lower() != query_lower}

    if not candidates:
        return {"keywords_found": [], "count": 0, "results": []}

    # Raccogli match da tutte le strategie con score
    all_matches: Dict[str, float] = {}

    # Strategia 1: Substring
    for kw, score in _substring_matches(query, candidates).items():
        all_matches[kw] = max(all_matches.get(kw, 0), score)

    # Strategia 2: Similarità stringa (jellyfish)
    for kw, score in _similarity_matches(query, candidates).items():
        all_matches[kw] = max(all_matches.get(kw, 0), score)

    # Strategia 3: NLP semantico (se abilitato)
    use_google = config.get("nlp", "use_google", default=False)
    if use_google:
        for kw, score in _nlp_semantic_matches(query, candidates).items():
            all_matches[kw] = max(all_matches.get(kw, 0), score)

    if not all_matches:
        return {"keywords_found": [], "count": 0, "results": []}

    # Ordina per score e prendi le migliori keyword
    sorted_kws = sorted(all_matches.items(), key=lambda x: x[1], reverse=True)
    top_keywords = [kw for kw, _ in sorted_kws[:12]]

    logger.info(f"[Related] Top keyword correlate per '{query}': {top_keywords}")

    # Cerca articoli con queste keyword
    related_articles = search_articles_by_keywords(
        top_keywords, current_user_id, direct_result_ids
    )

    return {
        "keywords_found": [kw for kw, _ in sorted_kws[:6]],
        "count": len(related_articles[:max_related]),
        "results": related_articles[:max_related]
    }
