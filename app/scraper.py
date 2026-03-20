import requests
from bs4 import BeautifulSoup
from datetime import datetime

def clean_footer(text):
    footer_markers = [
        "Immagine:",
        "Associazione di Promozione Sociale",
        "Wikimedia Italia",
        "P.Iva",
        "CF ",
        "Codice SDI",
        "cookie",
        "IBAN",
        "licenza CC"
    ]
    for marker in footer_markers:
        if marker in text:
            return text.split(marker)[0].strip()
    return text.strip()


def parse_italian_date(date_str):
    mesi = {
        "Gennaio": "01",
        "Febbraio": "02",
        "Marzo": "03",
        "Aprile": "04",
        "Maggio": "05",
        "Giugno": "06",
        "Luglio": "07",
        "Agosto": "08",
        "Settembre": "09",
        "Ottobre": "10",
        "Novembre": "11",
        "Dicembre": "12"
    }

    parts = date_str.split()
    if len(parts) == 3:
        giorno, mese_nome, anno = parts
        mese = mesi.get(mese_nome, "01")
        return f"{anno}-{mese}-{int(giorno):02d}"
    return None


def extract_article_data(url):
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    # Titolo
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(strip=True)
    else:
        title = soup.find("title").get_text(strip=True)

    # Contenuto
    paragraphs = soup.find_all("p")
    content = "\n".join(p.get_text(strip=True) for p in paragraphs)

    # Data
    date_div = soup.find("div", class_="the_content_wrapper postdate")
    if date_div:
        raw_date = date_div.get_text(strip=True)
        raw_date = raw_date.replace("Articolo pubblicato il", "").strip()
        date_text = parse_italian_date(raw_date)
    else:
        date_text = None

    return {
        "title": title,
        "date": date_text,
        "content": clean_footer(content)
    }
