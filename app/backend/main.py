from flask import Flask, request, jsonify
from flask_cors import CORS
from scraper import extract_article_data
from nlp import extract_keywords
from db import save_article, search_articles_by_keyword, get_latest_articles

app = Flask(__name__)
CORS(app)


@app.route("/")
def home():
    return jsonify({"status": "API Wikimedia Italia - Online!"})


@app.route("/upload", methods=["POST"])
def upload_article():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({"error": "URL mancante"}), 400

    url = data["url"]

    try:
        testo = extract_article_data(url)
    except Exception as e:
        return jsonify({"error": f"Scraper fallito: {str(e)}"}), 500

    if not testo["html_content"]:
        return jsonify({"error": "Contenuto articolo non trovato nella pagina"}), 422

    keywords = extract_keywords(testo["plain_text"])

    doc_data = {
        "title": testo["title"],
        "content": testo["html_content"],
        "date": testo["date"],
        "image_url": testo.get("image_url"),
        "author": "Sconosciuto (Scraping)",
        "keywords": keywords,
        "source_url": url,
        "upload_method": "auto"
    }

    saved_doc, is_new = save_article(doc_data)

    if is_new:
        return jsonify({"message": "Articolo salvato con successo", "data": saved_doc}), 201
    else:
        return jsonify({"message": "Articolo già presente nel sistema", "data": saved_doc}), 200


@app.route("/upload_manual", methods=["POST"])
def upload_article_manual():
    data = request.get_json()
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()

    if not title or not content:
        return jsonify({"error": "Dati mancanti: 'title' e 'content' sono obbligatori e non possono essere vuoti"}), 400

    raw_content = data["content"]
    keywords = extract_keywords(raw_content)
    html_formatted_content = "".join(f"<p>{par}</p>" for par in raw_content.split('\n') if par.strip())

    doc_data = {
        "title": data["title"],
        "content": html_formatted_content,
        "author": data.get("author", "Sconosciuto"),
        "date": data.get("date", "Sconosciuta"),
        "keywords": keywords,
        "upload_method": "manual"
    }

    saved_doc, is_new = save_article(doc_data)

    if is_new:
        return jsonify({"message": "Articolo salvato con successo", "data": saved_doc}), 201
    else:
        return jsonify({"message": "Articolo già presente nel sistema", "data": saved_doc}), 200


@app.route("/search", methods=["GET"])
def search():
    query = request.args.get("q")
    if not query:
        return jsonify({"error": "Parametro 'q' mancante per la ricerca"}), 400

    results = search_articles_by_keyword(query)
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


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")