
const API_BASE_URL = '';
let currentArticles = [];
document.getElementById('today-date').textContent =
    new Date().toLocaleDateString('it-IT', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.1/firebase-app.js";
import { getAuth, signInWithEmailAndPassword, createUserWithEmailAndPassword, signOut, onAuthStateChanged, getIdToken } from "https://www.gstatic.com/firebasejs/10.8.1/firebase-auth.js";
const firebaseConfig = {
  apiKey: "AIzaSyCvGOe2EufQWm0Gkietyv_Fryl-0HvvCek",
  authDomain: "sistemi-distribuiti-nuovo.firebaseapp.com",
  projectId: "sistemi-distribuiti-nuovo",
  storageBucket: "sistemi-distribuiti-nuovo.firebasestorage.app",
  messagingSenderId: "114166266178",
  appId: "1:114166266178:web:65a54756401549eb21b0db",
  measurementId: "G-7GB2X0Q72F"
};
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = String(str);
    return div.innerHTML;
}
function updateLoginState(user) {
    if (user) {
        document.getElementById('btn-open-login').style.display = 'none';
        document.getElementById('user-menu').style.display = 'flex';
        document.getElementById('upload-sections').style.display = 'block';
        document.getElementById('masthead-user-name').textContent = user.email.split('@')[0];
    } else {
        document.getElementById('btn-open-login').style.display = 'inline-block';
        document.getElementById('user-menu').style.display = 'none';
        document.getElementById('upload-sections').style.display = 'none';
        document.getElementById('masthead-user-name').textContent = '';
    }
}
onAuthStateChanged(auth, (user) => {
    updateLoginState(user);
    if (document.getElementById('results-grid')) goHome();
});
document.getElementById('btn-open-login').addEventListener('click', () => {
    document.getElementById('loginModal').classList.add('open');
});
function closeLoginModal() {
    document.getElementById('loginModal').classList.remove('open');
}
document.getElementById('login-modal-close-btn').addEventListener('click', closeLoginModal);
document.getElementById('loginModal').addEventListener('click', (e) => {
    if (e.target === document.getElementById('loginModal')) closeLoginModal();
});

document.getElementById('btn-register-mode').addEventListener('click', () => {
    document.getElementById('form-login').style.display = 'none';
    document.getElementById('form-register').style.display = 'block';
    document.getElementById('loginModalLabel').textContent = 'Registrazione';
    document.getElementById('login-description').textContent = 'Crea un nuovo account per salvare e proteggere i tuoi articoli.';
    document.getElementById('login-alert-container').innerHTML = '';
});

document.getElementById('btn-login-mode').addEventListener('click', () => {
    document.getElementById('form-register').style.display = 'none';
    document.getElementById('form-login').style.display = 'block';
    document.getElementById('loginModalLabel').textContent = 'Accesso';
    document.getElementById('login-description').textContent = 'Inserisci le tue credenziali per autenticarti o crea un nuovo account.';
    document.getElementById('login-alert-container').innerHTML = '';
});

document.getElementById('form-register').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('regEmailInput').value.trim();
    const password = document.getElementById('regPasswordInput').value;
    if (firebaseConfig.apiKey.includes("INSERISCI_LA_TUA_API_KEY")) {
        console.warn("API KEY non impostata! Uso fallback locale fittizio.");
        localStorage.setItem('fake_token', email);
        updateLoginState({ email: email });
        closeLoginModal();
        showAlert(`Account creato (Fallback locale), ${email}!`, 'success');
        return;
    }
    try {
        const userCredential = await createUserWithEmailAndPassword(auth, email, password);
        document.getElementById('regEmailInput').value = '';
        document.getElementById('regPasswordInput').value = '';
        closeLoginModal();
        showAlert(`Account creato con successo, benvenuto ${userCredential.user.email}!`, 'success');
    } catch (error) {
        if (error.code === 'auth/email-already-in-use') {
            showModalAlert('Questa email è già registrata. Usa il Login.', 'warning');
        } else if (error.code === 'auth/weak-password') {
            showModalAlert('La password deve essere di almeno 6 caratteri.', 'warning');
        } else {
            showModalAlert(`Errore di registrazione: ${error.message}`, 'danger');
        }
    }
});
document.getElementById('form-login').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('usernameInput').value.trim();
    const password = document.getElementById('passwordInput').value;
    if (firebaseConfig.apiKey.includes("INSERISCI_LA_TUA_API_KEY")) {
        console.warn("API KEY non impostata! Uso fallback locale fittizio.");
        localStorage.setItem('fake_token', email);
        updateLoginState({ email: email });
        closeLoginModal();
        showAlert(`Benvenuto (Fallback), ${email}!`, 'success');
        return;
    }
    try {
        const userCredential = await signInWithEmailAndPassword(auth, email, password);
        document.getElementById('usernameInput').value = '';
        document.getElementById('passwordInput').value = '';
        closeLoginModal();
        showAlert(`Benvenuto, ${userCredential.user.email}!`, 'success');
    } catch (error) {
        if (error.code === 'auth/invalid-credential' || error.code === 'auth/user-not-found' || error.code === 'auth/wrong-password') {
            showModalAlert('Credenziali non valide.', 'danger');
        } else {
            showModalAlert(`Errore di accesso: ${error.message}`, 'danger');
        }
    }
});
document.getElementById('btn-logout').addEventListener('click', async () => {
    if (firebaseConfig.apiKey.includes("INSERISCI_LA_TUA_API_KEY")) {
        localStorage.removeItem('fake_token');
        updateLoginState(null);
    } else {
        await signOut(auth);
    }
    showAlert('Logout effettuato con successo', 'info');
    goHome();
});
async function loadMyArticles() {
    const isFallback = firebaseConfig.apiKey.includes("INSERISCI_LA_TUA_API_KEY");
    const hasAccess = isFallback ? localStorage.getItem('fake_token') : auth.currentUser;
    if (!hasAccess) {
        showAlert('Devi effettuare il login per vedere i tuoi articoli.', 'warning');
        return;
    }
    document.getElementById('searchInput').value = '';
    showEmptyState('Caricamento dei tuoi articoli…');
    try {
        const res = await fetch(`${API_BASE_URL}/api/user/articles`, { headers: await getHeaders(null) });
        const data = await res.json();
        if (res.ok && data.results.length > 0) {
            displayResults(data.results);
            showAlert(`I tuoi articoli — ${data.count} trovati`, 'info');
        } else if (res.ok) {
            showEmptyState('Non hai ancora caricato nessun articolo.');
        } else {
            showAlert(data.message || 'Errore nel caricamento', 'danger');
        }
    } catch (err) {
        console.error("Errore loadMyArticles:", err);
        showAlert('Server non raggiungibile.', 'danger');
    }
}
document.getElementById('btn-my-articles').addEventListener('click', loadMyArticles);
async function getHeaders(contentType = 'application/json') {
    const headers = {};
    if (contentType) headers['Content-Type'] = contentType;
    if (firebaseConfig.apiKey.includes("INSERISCI_LA_TUA_API_KEY")) {
        const token = localStorage.getItem('fake_token');
        if (token) headers['Authorization'] = 'Bearer ' + token;
    } else if (auth.currentUser) {
        const token = await getIdToken(auth.currentUser);
        headers['Authorization'] = 'Bearer ' + token;
    }
    return headers;
}
function showAlert(message, type = 'success') {
    const c = document.getElementById('alert-container');
    c.innerHTML = `
        <div class="alert alert-${type}">
            <span>${escapeHtml(message)}</span>
            <button class="alert-close" onclick="this.parentElement.remove()">×</button>
        </div>`;
    setTimeout(() => { c.innerHTML = ''; }, 5000);
}
function showModalAlert(message, type = 'danger') {
    const c = document.getElementById('login-alert-container');
    if (!c) return;
    c.innerHTML = `
        <div class="alert alert-${type}" style="margin-bottom: 1rem;">
            <span>${escapeHtml(message)}</span>
            <button class="alert-close" onclick="this.parentElement.remove()">×</button>
        </div>`;
}
function showEmptyState(msg) {
    document.getElementById('results-container').innerHTML =
        `<div class="empty-state"><span class="empty-state-icon"></span>${msg}</div>`;
    document.getElementById('results-count').textContent = '';
}
async function loadLatest() {
    try {
        const res = await fetch(`${API_BASE_URL}/latest`, { headers: await getHeaders(null) });
        const data = await res.json();
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
document.addEventListener('DOMContentLoaded', () => {
    if (firebaseConfig.apiKey.includes("INSERISCI_LA_TUA_API_KEY")) {
        const token = localStorage.getItem('fake_token');
        updateLoginState(token ? { email: token } : null);
    }
    loadLatest();
});
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
        const res = await fetch(`${API_BASE_URL}/search?q=${encodeURIComponent(query)}`, { headers: await getHeaders(null) });
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
window.triggerSearch = function (kw) {
    document.getElementById('searchInput').value = kw;
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
    const isPublic = document.getElementById('autoIsPublic').checked;
    const btn = document.getElementById('btn-auto');
    btn.textContent = 'Estrazione…'; btn.disabled = true;
    try {
        const res = await fetch(`${API_BASE_URL}/upload`, {
            method: 'POST', headers: await getHeaders(),
            body: JSON.stringify({ url, is_public: isPublic })
        });
        const data = await res.json();
        if (res.ok) {
            if (res.status === 201) {
                showAlert(`Estratto e salvato: ${data.data.title}`, 'success');
            } else {
                showAlert(`L'articolo era già presente nel database!`, 'info');
            }
            document.getElementById('urlInput').value = '';
            loadMyArticles();
        } else showAlert(data.message || data.error || 'Errore estrazione', 'danger');
    } catch (err) { console.error('Errore upload auto:', err); showAlert('Server non raggiungibile.', 'danger'); }
    finally { btn.textContent = 'Estrai e Salva'; btn.disabled = false; }
});
document.getElementById('form-upload-manual').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('btn-manual');
    const payload = {
        title: document.getElementById('manualTitle').value,
        date: document.getElementById('manualDate').value,
        author: document.getElementById('manualAuthor').value,
        content: document.getElementById('manualContent').value,
        is_public: document.getElementById('manualIsPublic').checked,
    };
    btn.textContent = 'Salvataggio…'; btn.disabled = true;
    try {
        const res = await fetch(`${API_BASE_URL}/upload_manual`, {
            method: 'POST', headers: await getHeaders(),
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok) {
            if (res.status === 201) {
                showAlert(data.message, 'success');
            } else {
                showAlert(`L'articolo era già presente nel database!`, 'info');
            }
            document.getElementById('form-upload-manual').reset();
            loadMyArticles();
        } else showAlert(data.message || data.error || 'Errore salvataggio', 'danger');
    } catch (err) { console.error('Errore upload manuale:', err); showAlert('Server non raggiungibile.', 'danger'); }
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
    const countEl = document.getElementById('results-count');
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
        const plain = tmpDiv.textContent || '';
        const excerpt = plain.length > 160 ? plain.slice(0, 160) + '…' : plain;
        const card = document.createElement('div');
        card.className = 'article-card';
        const body = document.createElement('div');
        body.className = 'article-card-body';
        body.innerHTML = `
            <p class="article-card-meta">${escapeHtml(article.date) || '—'} &nbsp;·&nbsp; ${escapeHtml(article.author) || 'Sconosciuto'}</p>
            <h3 class="article-card-title">${escapeHtml(article.title)}</h3>
            <p class="article-card-excerpt">${escapeHtml(excerpt)}</p>
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
            openPage.addEventListener('click', async (e) => {
                e.stopPropagation();
                if (article.id) {
                    let token = null;
                    if (firebaseConfig.apiKey.includes("INSERISCI_LA_TUA_API_KEY")) {
                        token = localStorage.getItem('fake_token');
                    } else if (auth.currentUser) {
                        token = await getIdToken(auth.currentUser);
                    }
                    let url = `${API_BASE_URL}/article/${article.id}`;
                    if (token) url += `?token=${token}`;
                    window.location.href = url;
                }
            });
            actionsDiv.appendChild(readMore);
            actionsDiv.appendChild(openPage);
            imgWrap.appendChild(actionsDiv);
            card.appendChild(imgWrap);
        }
        card.addEventListener('click', function (e) {
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
        openPageBtn.onclick = async () => {
            let token = null;
            if (firebaseConfig.apiKey.includes("INSERISCI_LA_TUA_API_KEY")) {
                token = localStorage.getItem('fake_token');
            } else if (auth.currentUser) {
                token = await getIdToken(auth.currentUser);
            }
            let url = `${API_BASE_URL}/article/${a.id}`;
            if (token) url += `?token=${token}`;
            window.location.href = url;
        };
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