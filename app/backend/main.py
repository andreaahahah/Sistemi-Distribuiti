import logging
import os
import json
import base64
from flask import Flask, request, jsonify, render_template, abort, send_from_directory
from markupsafe import escape as html_escape
from flask_cors import CORS
from config import Config
from exceptions import AppError, ValidationError, NoContentError, ArticleNotFoundError, ScraperError
from scraper import extract_article_data
from nlp import extract_keywords  
from db import save_article, get_article_by_id, search_articles_by_keyword, get_latest_articles, get_user_articles
from nlp_dispatcher import dispatch_nlp_task, _run_local
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
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
try:
    firebase_admin.initialize_app(options={'projectId': 'sistemidistribuiti-butte-dbfb6'})
    logger.info("Firebase Admin inizializzato con successo.")
except ValueError:
    pass
def get_current_user():
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    else:
        token = request.args.get("token")
    if not token:
        return None
    try:
        decoded_token = firebase_auth.verify_id_token(token)
        return decoded_token.get("uid") 
    except Exception as e:
        logger.warning(f"Tentativo di accesso con JWT non valido: {e}")
        return None
@app.route("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")
@app.route("/article/<article_id>")
def article_page(article_id: str):
    current_user = get_current_user()
    article = get_article_by_id(article_id, current_user)
    if not article:
        return render_template("article.html", error="Articolo non trovato o accesso negato"), 404
    return render_template("article.html", article=article)
@app.route("/upload", methods=["POST"])
def upload_article():
    current_user = get_current_user()
    if not current_user:
        return jsonify({"message": "Autenticazione richiesta"}), 401
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
        "user_id": current_user,
        "is_public": data.get("is_public", True),
    }
    saved_doc, is_new = save_article(doc_data)
    status = 201 if is_new else 200
    msg = "Articolo salvato con successo" if is_new else "Articolo già presente nel sistema"
    logger.info(f"{msg}: {saved_doc['id']}")
    if is_new:
        dispatch_nlp_task(saved_doc["id"], testo["plain_text"])
    return jsonify({"message": msg, "data": saved_doc}), status
@app.route("/upload_manual", methods=["POST"])
def upload_article_manual():
    current_user = get_current_user()
    if not current_user:
        return jsonify({"message": "Autenticazione richiesta"}), 401
    data = request.get_json()
    title = data.get("title", "").strip()
    content = data.get("content", "").strip()
    if not title or not content:
        raise ValidationError("'title' e 'content' sono obbligatori e non possono essere vuoti")
    html_formatted_content = "".join(f"<p>{html_escape(par)}</p>" for par in content.split("\n") if par.strip())
    doc_data = {
        "title": data["title"],
        "content": html_formatted_content,
        "author": data.get("author", "Sconosciuto"),
        "date": data.get("date", "Sconosciuta"),
        "keywords": [],
        "nlp_status": "PENDING",
        "upload_method": "manual",
        "user_id": current_user,
        "is_public": data.get("is_public", True)
    }
    saved_doc, is_new = save_article(doc_data)
    status = 201 if is_new else 200
    msg = "Articolo salvato con successo" if is_new else "Articolo già presente nel sistema"
    logger.info(f"{msg}: {saved_doc['id']}")
    if is_new:
        dispatch_nlp_task(saved_doc["id"], content)
    return jsonify({"message": msg, "data": saved_doc}), status
@app.route("/search", methods=["GET"])
def search():
    query = request.args.get("q")
    if not query:
        raise ValidationError("Parametro 'q' mancante per la ricerca")
    current_user = get_current_user()
    results = search_articles_by_keyword(query, current_user)
    logger.info(f"Ricerca '{query}': {len(results)} risultati")
    return jsonify({
        "query": query,
        "count": len(results),
        "results": results
    }), 200
@app.route("/latest", methods=["GET"])
def latest_articles():
    current_user = get_current_user()
    results = get_latest_articles(5, current_user)
    return jsonify({
        "count": len(results),
        "results": results
    }), 200
@app.route("/api/user/articles", methods=["GET"])
def user_articles():
    current_user = get_current_user()
    if not current_user:
        return jsonify({"message": "Autenticazione richiesta"}), 401
    results = get_user_articles(current_user)
    logger.info(f"Dashboard utente '{current_user}': {len(results)} articoli")
    return jsonify({
        "user_id": current_user,
        "count": len(results),
        "results": results
    }), 200
@app.route("/article/<article_id>/json", methods=["GET"])
def article_json(article_id: str):
    current_user = get_current_user()
    article = get_article_by_id(article_id, current_user)
    if not article:
        raise ArticleNotFoundError("Articolo non trovato o accesso negato")
    return jsonify(article), 200
@app.route("/pubsub/push", methods=["POST"])
def pubsub_push():
    expected_token = os.environ.get("PUBSUB_VERIFICATION_TOKEN")
    if expected_token:
        request_token = request.args.get("token")
        if request_token != expected_token:
            logger.warning("Tentativo di accesso non autorizzato a /pubsub/push")
            return jsonify({"message": "Accesso negato"}), 403

    envelope = request.get_json()
    if not envelope:
        return jsonify({"message": "Payload mancante"}), 400
    pubsub_message = envelope.get("message")
    if not pubsub_message:
        return jsonify({"message": "Formato messaggio non valido"}), 400
    if isinstance(pubsub_message, dict) and "data" in pubsub_message:
        try:
            data_str = base64.b64decode(pubsub_message["data"]).decode("utf-8")
            data = json.loads(data_str)
            article_id = data.get("article_id")
            text = data.get("text")
            if not article_id or not text:
                raise ValueError("Dati mancanti nel payload")
            logger.info(f"[Pub/Sub Push] Ricevuto messaggio per elaborazione NLP articolo: {article_id}")
            _run_local(article_id, text)
            return jsonify({"message": "ACK"}), 200
        except Exception as e:
            logger.exception("Errore nell'elaborazione del messaggio Pub/Sub")
            return jsonify({"message": f"NACK: {str(e)}"}), 500
    return jsonify({"message": "Dati non trovati nel messaggio"}), 400
if __name__ == "__main__":
    host = config.get("app", "host", default="0.0.0.0")
    port = config.get("app", "port", default=5000)
    debug = config.get("app", "debug", default=True)
    logger.info(f"Avvio server su {host}:{port}")
    app.run(debug=debug, host=host, port=port)