// URL base del tuo backend Flask
const API_BASE_URL = 'http://127.0.0.1:5000';

// Elementi del DOM
const resultsContainer = document.getElementById('results-container');
const alertContainer = document.getElementById('alert-container');

// Memoria globale per gli articoli aperti nel modal
let currentArticles = [];

// Funzione Helper per mostrare messaggi
function showAlert(message, type = 'success') {
    alertContainer.innerHTML = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    setTimeout(() => { alertContainer.innerHTML = ''; }, 5000);
}

// Caricamento degli ultimi articoli all'avvio della pagina
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch(`${API_BASE_URL}/latest`);
        const data = await response.json();

        if (response.ok && data.results.length > 0) {
            displayResults(data.results);
        } else {
            resultsContainer.innerHTML = '<div class="col-12 text-muted"><em>Nessun articolo nel database. Inizia caricandone uno!</em></div>';
        }
    } catch (error) {
        console.error(error);
        showAlert('Impossibile contattare il server. Flask è acceso?', 'danger');
    }
});

// Funzione che viene chiamata cliccando su una keyword
window.triggerSearch = function(keyword) {
    document.getElementById('searchInput').value = keyword;
    document.getElementById('btn-search').click();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// 1. RICERCA ARTICOLI
document.getElementById('form-search').addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = document.getElementById('searchInput').value;
    const btn = document.getElementById('btn-search');

    btn.innerHTML = 'Ricerca...';
    btn.disabled = true;

    try {
        const response = await fetch(`${API_BASE_URL}/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();

        if (response.ok) {
            displayResults(data.results);
            if (data.results.length === 0) {
                showAlert(`Nessun articolo trovato per la keyword: ${query}`, 'warning');
            } else {
                showAlert(`Trovati ${data.results.length} risultati per "${query}"`, 'success');
            }
        } else {
            showAlert(data.error || 'Errore durante la ricerca', 'danger');
        }
    } catch (error) {
        showAlert('Impossibile contattare il server.', 'danger');
    } finally {
        btn.innerHTML = 'Cerca';
        btn.disabled = false;
    }
});

// 2. UPLOAD AUTOMATICO (SCRAPING)
document.getElementById('form-upload-auto').addEventListener('submit', async (e) => {
    e.preventDefault();
    const url = document.getElementById('urlInput').value;
    const btn = document.getElementById('btn-auto');
    btn.innerHTML = 'Estrazione in corso...';
    btn.disabled = true;

    try {
        const response = await fetch(`${API_BASE_URL}/upload`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url })
        });
        const data = await response.json();

        if (response.ok) {
            showAlert(`Successo! ${data.message} (${data.data.title})`);
            document.getElementById('urlInput').value = '';
            // Ricarica la lista cercando la prima keyword
            triggerSearch(data.data.keywords[0] || '');
        } else {
            showAlert(data.error || 'Errore durante l\'estrazione', 'danger');
        }
    } catch (error) {
        showAlert('Impossibile contattare il server.', 'danger');
    } finally {
        btn.innerHTML = 'Estrai e Salva';
        btn.disabled = false;
    }
});

// 3. UPLOAD MANUALE
document.getElementById('form-upload-manual').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('btn-manual');
    const articleData = {
        title: document.getElementById('manualTitle').value,
        date: document.getElementById('manualDate').value,
        author: document.getElementById('manualAuthor').value,
        content: document.getElementById('manualContent').value
    };
    btn.innerHTML = 'Salvataggio...';
    btn.disabled = true;

    try {
        const response = await fetch(`${API_BASE_URL}/upload_manual`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(articleData)
        });
        const data = await response.json();

        if (response.ok) {
            showAlert(`Successo! ${data.message}`);
            document.getElementById('form-upload-manual').reset();
            triggerSearch(articleData.title.split(' ')[0]);
        } else {
            showAlert(data.error || 'Errore durante il salvataggio', 'danger');
        }
    } catch (error) {
        showAlert('Impossibile contattare il server.', 'danger');
    } finally {
        btn.innerHTML = 'Salva Manualmente';
        btn.disabled = false;
    }
});

// Funzione per mostrare gli articoli (Card Cliccabile)
function displayResults(articles) {
    currentArticles = articles;
    resultsContainer.innerHTML = '';

    articles.forEach((article, index) => {
        // Aggiungiamo event.stopPropagation() per non aprire il modal se clicchiamo sul badge
        const keywordsHtml = article.keywords.map(kw =>
            `<span class="badge bg-info text-dark keyword-badge" style="cursor: pointer; position: relative; z-index: 2;" onclick="event.stopPropagation(); triggerSearch('${kw}')">${kw}</span>`
        ).join('');

        // Creiamo un div invisibile per estrarre solo il testo puro dall'HTML
        const tempDiv = document.createElement("div");
        tempDiv.innerHTML = article.content || "";
        const cleanText = tempDiv.textContent || tempDiv.innerText || "";

        const shortContent = cleanText.length > 150
            ? cleanText.substring(0, 150) + '...'
            : cleanText;

        const imageHtml = article.image_url
            ? `<img src="${article.image_url}" class="card-img-top" alt="Copertina" style="height: 200px; object-fit: cover;">`
            : '';

        // onClick="openArticleModal(index)" sulla card intera
        const cardHtml = `
            <div class="col-md-12 mb-4">
                <div class="card article-card shadow-sm h-100" style="cursor: pointer;" onclick="openArticleModal(${index})">
                    ${imageHtml}
                    <div class="card-body">
                        <h5 class="card-title text-primary">${article.title}</h5>
                        <h6 class="card-subtitle mb-2 text-muted">
                            📅 ${article.date || 'Data sconosciuta'} | ✍️ ${article.author || 'Sconosciuto'}
                        </h6>
                        <p class="card-text">${shortContent}</p>
                        
                        <div class="d-flex justify-content-between align-items-center mt-3">
                            <div>${keywordsHtml || '<span class="text-muted">Nessuna keyword estratta</span>'}</div>
                            <span class="btn btn-outline-primary btn-sm text-nowrap ms-2">
                                Leggi tutto 📖
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        `;
        resultsContainer.innerHTML += cardHtml;
    });
}

// Funzione per aprire il Modal con l'articolo completo
window.openArticleModal = function(index) {
    const article = currentArticles[index];

    document.getElementById('articleModalLabel').innerText = article.title;
    document.getElementById('articleModalMeta').innerText = `📅 ${article.date || 'Sconosciuta'} | ✍️ ${article.author || 'Sconosciuto'} | 🏷️ Metodo: ${article.upload_method}`;

    // Usiamo innerHTML per dire al browser di interpretare i tag!
    document.getElementById('articleModalContent').innerHTML = article.content || "Nessun contenuto disponibile.";

    const modalImage = document.getElementById('articleModalImage');
    if (article.image_url) {
        modalImage.src = article.image_url;
        modalImage.style.display = 'block';
    } else {
        modalImage.style.display = 'none';
    }

    const sourceDiv = document.getElementById('articleModalSourceDiv');
    const sourceLink = document.getElementById('articleModalLink');
    if (article.source_url) {
        sourceLink.href = article.source_url;
        sourceDiv.style.display = 'block';
    } else {
        sourceDiv.style.display = 'none';
    }

    const modal = new bootstrap.Modal(document.getElementById('articleModal'));
    modal.show();
}