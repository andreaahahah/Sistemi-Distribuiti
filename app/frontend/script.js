const API_BASE_URL = 'http://127.0.0.1:5000';
let currentArticles = [];

document.getElementById('today-date').textContent =
    new Date().toLocaleDateString('it-IT', { weekday:'long', day:'numeric', month:'long', year:'numeric' });

function showAlert(message, type = 'success') {
    const c = document.getElementById('alert-container');
    c.innerHTML = `
        <div class="alert alert-${type}">
            <span>${message}</span>
            <button class="alert-close" onclick="this.parentElement.remove()">×</button>
        </div>`;
    setTimeout(() => { c.innerHTML = ''; }, 5000);
}

function showEmptyState(msg) {
    document.getElementById('results-container').innerHTML =
        `<div class="empty-state"><span class="empty-state-icon"></span>${msg}</div>`;
    document.getElementById('results-count').textContent = '';
}

async function loadLatest() {
    console.log("loadLatest chiamata");
    try {
        const res  = await fetch(`${API_BASE_URL}/latest`);
        console.log("Risposta ricevuta:", res);
        const data = await res.json();
        console.log("Data:", data);
        if (res.ok && data.results.length > 0) {
            displayResults(data.results);
        } else {
            showEmptyState('Nessun articolo nel database. Inizia caricandone uno!');
        }
    } catch (err) {
        console.error("Errore loadLatest:", err);
        showAlert('Impossibile contattare il server. Flask è acceso?', 'danger');
    }
}

document.addEventListener('DOMContentLoaded', loadLatest);

async function goHome() {
    document.getElementById('searchInput').value = '';
    showEmptyState('Caricamento...');
    await loadLatest();
    showAlert('Home — ultimi articoli', 'info');
}
document.getElementById('btn-clear').addEventListener('click', goHome);
document.getElementById('logo-home').addEventListener('click', e => { e.preventDefault(); goHome(); });


async function executeSearch(query) {
    if (!query) return;

    const btn = document.getElementById('btn-search');
    btn.textContent = '…';
    btn.disabled = true;

    try {
        const res = await fetch(`${API_BASE_URL}/search?q=${encodeURIComponent(query)}`);
        const data = await res.json();
        if (res.ok) {
            displayResults(data.results);
            if (!data.results.length) showAlert(`Nessun risultato per "${query}"`, 'warning');
            else showAlert(`${data.results.length} risultati per "${query}"`, 'success');
        } else {
            showAlert(data.error || 'Errore ricerca', 'danger');
        }
    } catch (err) {
        showAlert('Server non raggiungibile. Flask è attivo?', 'danger');
    } finally {
        btn.textContent = 'Cerca';
        btn.disabled = false;
    }
}

window.triggerSearch = function(kw) {
    document.getElementById('searchInput').value = kw;
    //window.scrollTo({ top: 0, behavior: 'smooth' });
    executeSearch(kw);
};


document.getElementById('form-search').addEventListener('submit', (e) => {
    e.preventDefault();
    const q = document.getElementById('searchInput').value.trim();
    if (!q) {
        goHome();
    } else {
        executeSearch(q);
    }
});


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
            window.triggerSearch(data.data.title || '');
        } else showAlert(data.error || 'Errore estrazione', 'danger');
    } catch { showAlert('Server non raggiungibile.', 'danger'); }
    finally { btn.textContent = 'Estrai e Salva'; btn.disabled = false; }
});

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
            window.triggerSearch(payload.title);
        } else showAlert(data.error || 'Errore salvataggio', 'danger');
    } catch { showAlert('Server non raggiungibile.', 'danger'); }
    finally { btn.textContent = 'Salva Manualmente'; btn.disabled = false; }
});

function displayResults(articles) {
    articles.sort((a, b) => {
        const dateA = a.date ? new Date(a.date) : new Date(0);
        const dateB = b.date ? new Date(b.date) : new Date(0);
        return dateB - dateA;
    });

    currentArticles = articles;
    const container = document.getElementById('results-container');
    const countEl   = document.getElementById('results-count');
    countEl.textContent = articles.length
        ? `${articles.length} articol${articles.length === 1 ? 'o' : 'i'}` : '';

    if (!articles.length) { showEmptyState('Nessun risultato trovato.'); return; }

    container.innerHTML = '';
    const grid = document.createElement('div');
    grid.className = 'results-grid';
    grid.id = 'results-grid';
    container.appendChild(grid);

    articles.forEach((article, index) => {
        const tmpDiv = document.createElement('div');
        tmpDiv.innerHTML = article.content || '';
        const plain   = tmpDiv.textContent || '';
        const excerpt = plain.length > 160 ? plain.slice(0, 160) + '…' : plain;

        const card = document.createElement('div');
        card.className = 'article-card';

const body = document.createElement('div');
        body.className = 'article-card-body';
        body.innerHTML = `
            <p class="article-card-meta">${article.date || '—'} &nbsp;·&nbsp; ${article.author || 'Sconosciuto'}</p>
            <h3 class="article-card-title">${article.title}</h3>
            <p class="article-card-excerpt">${excerpt}</p>
        `;

const footer = document.createElement('div');
        footer.className = 'article-card-footer';

        if (article.keywords && article.keywords.length > 0) {
            article.keywords.forEach(kw => {
                const badge = document.createElement('span');
                badge.className = 'kw-badge';
                badge.textContent = kw;

                badge.addEventListener('click', (e) => {
                    e.stopPropagation();
                    window.triggerSearch(kw);
                });

                footer.appendChild(badge);
            });
} else {
            footer.innerHTML = '<span style="font-size:.75rem;color:var(--muted)">Nessuna keyword</span>';
        }

        body.appendChild(footer);
        card.appendChild(body);

        if (article.image_url) {
            const imgWrap = document.createElement('div');
            imgWrap.className = 'article-card-image-wrap';

            const img = document.createElement('img');
            img.src = article.image_url;
            img.className = 'article-card-image';
            img.loading = 'lazy';
            imgWrap.appendChild(img);

            const actionsDiv = document.createElement('div');
            actionsDiv.className = 'card-actions';

            const readMore = document.createElement('span');
            readMore.className = 'read-more';
            readMore.textContent = 'Anteprima';
            readMore.addEventListener('click', (e) => {
                e.stopPropagation();
                openModal(index);
            });

            const openPage = document.createElement('span');
            openPage.className = 'read-more';
            openPage.textContent = 'Leggi';
            openPage.addEventListener('click', (e) => {
                e.stopPropagation();
                if (article.id) window.location.href = `${API_BASE_URL}/article/${article.id}`;
            });

            actionsDiv.appendChild(readMore);
            actionsDiv.appendChild(openPage);
            imgWrap.appendChild(actionsDiv);
            card.appendChild(imgWrap);
        }

        card.addEventListener('click', function(e) {
            if (!e.target.closest('.read-more')) openModal(index);
        });

        grid.appendChild(card);
    });
}

function openModal(index) {
    const a = currentArticles[index];
    if (!a) return;
    
    document.getElementById('articleModalLabel').textContent = a.title;
    document.getElementById('articleModalContent').innerHTML = a.content || 'Nessun contenuto disponibile.';

    const img = document.getElementById('articleModalImage');
    if (a.image_url) { img.src = a.image_url; img.style.display = 'block'; }
    else img.style.display = 'none';

    const srcDiv = document.getElementById('articleModalSourceDiv');
    if (a.source_url) {
        document.getElementById('articleModalLink').href = a.source_url;
        srcDiv.style.display = 'block';
    } else srcDiv.style.display = 'none';

    const openPageBtn = document.getElementById('modal-open-page');
    if (a.id) {
        openPageBtn.style.display = 'inline-block';
        openPageBtn.onclick = () => { window.location.href = `${API_BASE_URL}/article/${a.id}`; };
    } else {
        openPageBtn.style.display = 'none';
    }

    document.getElementById('articleModal').classList.add('open');
    document.body.style.overflow = 'hidden';
    document.querySelector('.modal-box').scrollTop = 0;
}

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