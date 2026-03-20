from flask import Flask, request, jsonify
from scraper import extract_article_data
from nlp import extract_keywords

app = Flask(__name__)

# Endpoint di test
@app.route("/")
def home():
    return "API Wikimedia Italia - Online!"

# Endpoint per caricare un articolo
@app.route("/upload", methods=["POST"])
def upload_article():
    data = request.get_json()

    # Controllo di base
    if not data or 'url' not in data:
        return jsonify({"error": "URL mancante"}), 400

    url = data["url"]

    testo = extract_article_data(url)
    keywords = extract_keywords(testo["content"])

    return jsonify({
        "title": testo["title"],
        "content": testo["content"],
        "date" : testo["date"],
        "keywords": keywords
    }), 200


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
