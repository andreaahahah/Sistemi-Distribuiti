import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


def parse_italian_date(date_str):
    mesi = {
        "Gennaio": "01", "Febbraio": "02", "Marzo": "03", "Aprile": "04",
        "Maggio": "05", "Giugno": "06", "Luglio": "07", "Agosto": "08",
        "Settembre": "09", "Ottobre": "10", "Novembre": "11", "Dicembre": "12"
    }
    parts = date_str.split()
    if len(parts) == 3:
        return f"{parts[2]}-{mesi.get(parts[1], '01')}-{int(parts[0]):02d}"
    return None


def extract_article_data(url):
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    # --- Titolo ---
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else soup.find("title").get_text(strip=True)

    # --- Data (dal div postdate) ---
    date_text = None
    date_div = soup.find("div", class_="the_content_wrapper postdate")
    if date_div:
        raw_date = date_div.get_text(strip=True).replace("Articolo pubblicato il", "").strip()
        date_text = parse_italian_date(raw_date)
    if not date_text:
        time_el = soup.find("time", attrs={"datetime": True})
        if time_el:
            date_text = time_el["datetime"][:10]

    # --- Immagine principale ---
    meta_img = soup.find("meta", property="og:image")
    image_url = meta_img["content"] if meta_img else None

    # --- Contenitore articolo ---
    # Su wikimedia.it il corpo e' in div.the_content_wrapper MA non quello con classe 'postdate'
    all_wrappers = soup.find_all("div", class_="the_content_wrapper")
    content_div = next(
        (d for d in all_wrappers if "postdate" not in d.get("class", [])),
        None
    )

    if not content_div:
        return {
            "title": title,
            "date": date_text,
            "image_url": image_url,
            "html_content": "",
            "plain_text": ""
        }

    # --- Rimozione elementi spazzatura specifici di wikimedia.it ---

    # Breadcrumb
    for el in content_div.find_all("ul", class_="breadcrumbs"):
        el.decompose()

    # Titolo duplicato dentro il contenuto
    for el in content_div.find_all("h2", class_="entry-title"):
        el.decompose()

    # Categorie
    for el in content_div.find_all("ul", class_="post-categories"):
        el.decompose()

    # Lista tag (ul i cui link puntano tutti a /news/tag/)
    for ul in content_div.find_all("ul"):
        links = ul.find_all("a", href=True)
        if links and all("/news/tag/" in a["href"] for a in links):
            ul.decompose()

    # Articoli correlati in fondo (h4 con link a /news/)
    for h4 in content_div.find_all("h4"):
        links = h4.find_all("a", href=True)
        if links and all("/news/" in a["href"] for a in links):
            h4.decompose()

    # Paragrafi con solo credits immagine
    for p in content_div.find_all("p"):
        text = p.get_text(strip=True)
        if text.startswith("Immagine in evidenza"):
            p.decompose()
            continue
        links = p.find_all("a", href=True)
        if links and all(
                "commons.wikimedia.org" in a["href"] or "creativecommons.org" in a["href"]
                for a in links
        ) and len(text) < 300:
            p.decompose()

    # --- Rimozione spaziatori e paragrafi vuoti ---
    for spacer in content_div.find_all("div", class_="wp-block-spacer"):
        spacer.decompose()

    for p in content_div.find_all("p"):
        # Rimuove se il paragrafo non ha testo E non contiene immagini
        if not p.get_text(strip=True) and not p.find("img"):
            p.decompose()

    # --- Fix link e immagini ---
    for a in content_div.find_all("a"):
        a["target"] = "_blank"
        a["rel"] = "noopener noreferrer"

    for img in content_div.find_all("img"):
        # Gestione lazy loading
        for lazy_attr in ["data-src", "data-lazy-src", "data-original"]:
            if img.has_attr(lazy_attr):
                img["src"] = img[lazy_attr]
                del img[lazy_attr]
        if img.has_attr("src"):
            img["src"] = urljoin(url, img["src"])
        img.attrs = {
            "src": img.get("src", ""),
            "alt": img.get("alt", ""),
            "class": "img-fluid rounded my-3",
            "loading": "lazy",
        }

    html_content = content_div.decode_contents().strip()
    plain_text = content_div.get_text(separator="\n\n", strip=True)

    return {
        "title": title,
        "date": date_text,
        "image_url": image_url,
        "html_content": html_content,
        "plain_text": plain_text,
    }