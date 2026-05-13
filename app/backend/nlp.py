import yake

def extract_keywords_local(text, max_keywords=10):
    kw_extractor = yake.KeywordExtractor(
        lan="it",
        n=1,
        top=max_keywords,
        dedupLim=0.9
    )
    keywords = [kw for kw, score in kw_extractor.extract_keywords(text)]
    return keywords



def extract_keywords(text, use_google=False, max_keywords=10):
    if not use_google:
        return extract_keywords_local(text, max_keywords)

    from google.cloud import language_v1
    client = language_v1.LanguageServiceClient()
    document = language_v1.Document(content=text, type_=language_v1.Document.Type.PLAIN_TEXT)
    response = client.analyze_entities(document=document)
    return [entity.name for entity in response.entities][:max_keywords]

