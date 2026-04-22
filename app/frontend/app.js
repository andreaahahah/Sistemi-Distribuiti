const API_BASE_URL = 'http://127.0.0.1:5000';
let currentArticles = [];

document.getElementById('today-date').textContent =
    new Date().toLocaleDateString('it-IT', { weekday:'long', day:'numeric', month:'long', year:'numeric' });

// ── ALERTS ──
function showAlert(message, type = 'success') {
    const c = document.getElementById('alert-container');
    c.innerHTML = `
        <div class="alert alert-${type}">
            <span>${message}</span>
            <button class="alert-close" onclick="this.parentElement.remove()">×</button>
        </div>`;
    setTimeout(() => { c.innerHTML = ''; }, 5000);
}

// ── EMPTY STATE ──
function showEmptyState(msg) {
    document.getElementById('results-container').innerHTML =
        `<div class="empty-state"><span class="empty-state-icon">📭</span>${msg}</div>`;
    document.getElementById('results-count').textContent = '';
}

// ── LOAD LATEST ──
async function loadLatest() {
    try {
        const res  = await fetch(`${API_BASE_URL}/latest`);
        const data = await res.json();
        if (res.ok && data.results.length > 0) {
            displayResults(data.results);
        } else {
            showEmptyState('Nessun articolo nel database. Inizia caricandone uno!');
        }
    } catch {
        showAlert('Impossibile contattare il server. Flask è acceso?', 'danger');
    }
}

document.addEventListener('DOMContentLoaded', loadLatest);

// ── HOME ──
async function goHome() {
    document.getElementById('searchInput').value = '';
    showEmptyState('Caricamento...');
    await loadLatest();
    showAlert('Home — ultimi articoli', 'info');
}
document.getElementById('btn-clear').addEventListener('click', goHome);
document.getElementById('logo-home').addEventListener('click', e => { e.preventDefault(); goHome(); });

// ── SEARCH ──
window.triggerSearch = function(kw) {
    document.getElementById('searchInput').value = kw;
    document.getElementById('form-search').dispatchEvent(new Event('submit'));
    window.scrollTo({ top: 0, behavior: 'smooth' });
};

document.getElementById('form-search').addEventListener('submit', async (e) => {
    e.preventDefault();
    const q = document.getElementById('searchInput').value.trim();
    if (!q) return;
    const btn = document.getElementById('btn-search');
    btn.textContent = '…'; btn.disabled = true;
    try {
        const res  = await fetch(`${API_BASE_URL}/search?q=${encodeURIComponent(q)}`);
        const data = await res.json();
        if (res.ok) {
            displayResults(data.results);
            if (!data.results.length) showAlert(`Nessun risultato per "${q}"`, 'warning');
            else showAlert(`${data.results.length} risultati per "${q}"`, 'success');
        } else showAlert(data.error || 'Errore ricerca', 'danger');
    } catch { showAlert('Server non raggiungibile.', 'danger'); }
    finally { btn.textContent = 'Cerca'; btn.disabled = false; }
});

// ── UPLOAD AUTOMATICO ──
document.getElementById('form-upload-auto').addEventListener('submit', async (e) => {
    e.preventDefault();
    const url = document.getElementById('urlInput').value;
    const btn = document.getElementById('btn-auto');
    btn.textContent = 'Estrazione…'; btn.disabled = true;
    try {
        const res = await fetch(`${API_BASE_URL}/upload`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });
        const data = await res.json();
        if (res.ok) {
            showAlert(`Salvato: ${data.data.title}`);
            document.getElementById('urlInput').value = '';
            triggerSearch(data.data.title || '');
        } else showAlert(data.error || 'Errore estrazione', 'danger');
    } catch { showAlert('Server non raggiungibile.', 'danger'); }
    finally { btn.textContent = 'Estrai e Salva'; btn.disabled = false; }
});

// ── UPLOAD MANUALE ──
document.getElementById('form-upload-manual').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('btn-manual');
    const payload = {
        title:   document.getElementById('manualTitle').value,
        date:    document.getElementById('manualDate').value,
        author:  document.getElementById('manualAuthor').value,
        content: document.getElementById('manualContent').value,
    };
    btn.textContent = 'Salvataggio…'; btn.disabled = true;
    try {
        const res = await fetch(`${API_BASE_URL}/upload_manual`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok) {
            showAlert(data.message);
            document.getElementById('form-upload-manual').reset();
            triggerSearch(payload.title);
        } else showAlert(data.error || 'Errore salvataggio', 'danger');
    } catch { showAlert('Server non raggiungibile.', 'danger'); }
    finally { btn.textContent = 'Salva Manualmente'; btn.disabled = false; }
});

// ── DISPLAY RESULTS ──
// ── DISPLAY RESULTS ──
function displayResults(articles) {
    // 👇 NUOVO BLOCCO: Ordina gli articoli per data (dal più recente al più vecchio)
    articles.sort((a, b) => {
        // Se manca la data, assegniamo una data molto vecchia (1 Jan 1970) per metterli in fondo
        const dateA = a.date ? new Date(a.date) : new Date(0);
        const dateB = b.date ? new Date(b.date) : new Date(0);
        return dateB - dateA; // Ordine decrescente
    });

    currentArticles = articles;
    const container = document.getElementById('results-container');
    const countEl   = document.getElementById('results-count');
    countEl.textContent = articles.length
        ? `${articles.length} articol${articles.length === 1 ? 'o' : 'i'}` : '';

    if (!articles.length) { showEmptyState('Nessun risultato trovato.'); return; }

    container.innerHTML = '<div class="results-grid" id="results-grid"></div>';
    const grid = document.getElementById('results-grid');

    articles.forEach((article, index) => {
        const kwHtml = (article.keywords || []).map(kw =>
            `<span class="kw-badge" onclick="event.stopPropagation(); triggerSearch('${kw}')">${kw}</span>`
        ).join('');

        const tmpDiv = document.createElement('div');
        tmpDiv.innerHTML = article.content || '';
        const plain   = tmpDiv.textContent || '';
        const excerpt = plain.length > 160 ? plain.slice(0, 160) + '…' : plain;

        const imgHtml = article.image_url
            ? `<img src="${article.image_url}" class="article-card-image" alt="" loading="lazy">`
            : '';

        const card = document.createElement('div');
        card.className = 'article-card';
        card.innerHTML = `
            <div class="article-card-body">
                <p class="article-card-meta">📅 ${article.date || '—'} &nbsp;·&nbsp; ✍️ ${article.author || 'Sconosciuto'}</p>
                <h3 class="article-card-title">${article.title}</h3>
                <p class="article-card-excerpt">${excerpt}</p>
                <div class="article-card-footer">
                    ${kwHtml || '<span style="font-size:.75rem;color:var(--muted)">Nessuna keyword</span>'}
                    <span class="read-more">Leggi</span>
                </div>
            </div>
            ${imgHtml}
        `;
        card.addEventListener('click', () => openModal(index));
        grid.appendChild(card);
    });
}
// ── MODAL OPEN ──
function openModal(index) {
    const a = currentArticles[index];
    document.getElementById('articleModalLabel').textContent = a.title;
    document.getElementById('articleModalMeta').textContent  =
        `📅 ${a.date || 'Data sconosciuta'} · ✍️ ${a.author || 'Sconosciuto'} · 🏷 ${a.upload_method || '—'}`;
    document.getElementById('articleModalContent').innerHTML = a.content || 'Nessun contenuto disponibile.';

    const img = document.getElementById('articleModalImage');
    if (a.image_url) { img.src = a.image_url; img.style.display = 'block'; }
    else img.style.display = 'none';

    const srcDiv = document.getElementById('articleModalSourceDiv');
    if (a.source_url) {
        document.getElementById('articleModalLink').href = a.source_url;
        srcDiv.style.display = 'block';
    } else srcDiv.style.display = 'none';

    document.getElementById('articleModal').classList.add('open');
    document.body.style.overflow = 'hidden';

    // 👇 NUOVA RIGA: Resetta lo scorrimento all'inizio dell'articolo
    document.querySelector('.modal-box').scrollTop = 0;
}

// ── MODAL CLOSE ──
function closeModal() {
    document.getElementById('articleModal').classList.remove('open');
    document.body.style.overflow = '';
}
document.getElementById('modal-close-btn').addEventListener('click', closeModal);
document.getElementById('modal-footer-close').addEventListener('click', closeModal);
document.getElementById('articleModal').addEventListener('click', e => {
    if (e.target === document.getElementById('articleModal')) closeModal();
});
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });