import logging
import os
from flask import Flask, request, jsonify, render_template, abort, send_from_directory
from flask_cors import CORS

from config import Config
from exceptions import AppError, ValidationError, NoContentError, ArticleNotFoundError, ScraperError
from scraper import extract_article_data
from nlp import extract_keywords
from db import save_article, get_article_by_id, search_articles_by_keyword, get_latest_articles
from nlp_dispatcher import dispatch_nlp_task

config = Config()
config.setup_logging()
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
TEMPLATES_DIR = os.path.join(FRONTEND_DIR, "templates")
STATIC_DIR = os.path.join(FRONTEND_DIR, "static") if os.path.exists(os.path.join(FRONTEND_DIR, "static")) else FRONTEND_DIR

app = Flask(__name__, template_folder=TEMPLATES_DIR)
CORS(app)


@app.route("/style.css")
def serve_css():
    return send_from_directory(FRONTEND_DIR, "style.css", mimetype="text/css")


@app.route("/script.js")
def serve_js():
    return send_from_directory(FRONTEND_DIR, "script.js", mimetype="application/javascript")


@app.errorhandler(AppError)
def handle_app_error(error):
    logger.error(f"AppError: {error.message}")
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@app.route("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/article/<article_id>")
def article_page(article_id: str):
    article = get_article_by_id(article_id)
    if not article:
        return render_template("article.html", error="Articolo non trovato"), 404
    return render_template("article.html", article=article)


@app.route("/upload", methods=["POST"])
def upload_article():
    data = request.get_json()
    if not data or "url" not in data:
        raise ValidationError("URL mancante")

    url = data["url"]
    logger.info(f"Upload richiesto per URL: {url}")

    try:
        testo = extract_article_data(url)
    except ScraperError:
        raise
    except Exception as e:
        logger.exception("Errore scraper")
        raise ScraperError(f"Scraper fallito: {str(e)}")

    if not testo["html_content"]:
        raise NoContentError("Contenuto articolo non trovato nella pagina")

    # per ora salviamo l'articolo sneza keyword
    doc_data = {
        "title": testo["title"],
        "content": testo["html_content"],
        "date": testo["date"],
        "image_url": testo.get("image_url"),
        "author": testo.get("author") or "Sconosciuto",
        "keywords": [],          
        "nlp_status": "PENDING",
        "source_url": url,
        "upload_method": "auto",
    }

    saved_doc, is_new = save_article(doc_data)
    status = 201 if is_new else 200
    msg = "Articolo salvato con successo" if is_new else "Articolo già presente nel sistema"
    logger.info(f"{msg}: {saved_doc['id']}")

    #calcolo le keyword
    if is_new:
        dispatch_nlp_task(saved_doc["id"], testo["plain_text"])

    return jsonify({"message": msg, "data": saved_doc}), status


@app.route("/upload_manual", methods=["POST"])
def upload_article_manual():
    data = request.get_json()
    title = data.get("title", "").strip()
    content = data.get("content", "").strip()

    if not title or not content:
        raise ValidationError("'title' e 'content' sono obbligatori e non possono essere vuoti")

    keywords = extract_keywords(content)
    html_formatted_content = "".join(f"<p>{par}</p>" for par in content.split("\n") if par.strip())

    doc_data = {
        "title": data["title"],
        "content": html_formatted_content,
        "author": data.get("author", "Sconosciuto"),
        "date": data.get("date", "Sconosciuta"),
        "keywords": keywords,
        "upload_method": "manual"
    }

    saved_doc, is_new = save_article(doc_data)
    status = 201 if is_new else 200
    msg = "Articolo salvato con successo" if is_new else "Articolo già presente nel sistema"
    logger.info(f"{msg}: {saved_doc['id']}")
    return jsonify({"message": msg, "data": saved_doc}), status


@app.route("/search", methods=["GET"])
def search():
    query = request.args.get("q")
    if not query:
        raise ValidationError("Parametro 'q' mancante per la ricerca")

    results = search_articles_by_keyword(query)
    logger.info(f"Ricerca '{query}': {len(results)} risultati")
    return jsonify({
        "query": query,
        "count": len(results),
        "results": results
    }), 200


@app.route("/latest", methods=["GET"])
def latest_articles():
    results = get_latest_articles(5)
    return jsonify({
        "count": len(results),
        "results": results
    }), 200


@app.route("/article/<article_id>/json", methods=["GET"])
def article_json(article_id: str):
    article = get_article_by_id(article_id)
    if not article:
        raise ArticleNotFoundError("Articolo non trovato")
    return jsonify(article), 200


if __name__ == "__main__":
    host = config.get("app", "host", default="0.0.0.0")
    port = config.get("app", "port", default=5000)
    debug = config.get("app", "debug", default=True)
    logger.info(f"Avvio server su {host}:{port}")
    app.run(debug=debug, host=host, port=port)