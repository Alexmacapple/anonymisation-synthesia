/**
 * Anonymisation-synthesia — logique frontend.
 * Appelle les routes FastAPI (/ner/anonymize, /fichier/anonymise, etc.)
 */

const API_BASE = '';  // Meme origine

// --- État global ---
let correspondancesEnMemoire = [];

// --- Navigation ---
document.addEventListener('DOMContentLoaded', () => {
    // Navigation par hash
    window.addEventListener('hashchange', navigateTo);
    navigateTo();

    // Boutons
    document.getElementById('btn-pseudonymise').addEventListener('click', pseudonymiser);
    document.getElementById('btn-clear').addEventListener('click', () => {
        document.getElementById('input-texte').value = '';
        document.getElementById('output-texte').value = '';
        document.getElementById('results-zone').style.display = 'none';
    });
    document.getElementById('btn-traiter-fichier').addEventListener('click', () => traiterFichier(false));
    document.getElementById('btn-dry-run').addEventListener('click', () => traiterFichier(true));

    // Switch upload / chemin local
    document.querySelectorAll('input[name="import-mode"]').forEach(radio => {
        radio.addEventListener('change', () => {
            const mode = document.querySelector('input[name="import-mode"]:checked').value;
            document.getElementById('zone-upload').style.display = mode === 'upload' ? 'block' : 'none';
            document.getElementById('zone-local').style.display = mode === 'local' ? 'block' : 'none';
        });
    });

    // Upload fichier
    document.getElementById('file-upload').addEventListener('change', uploadFichier);

    // Générer mapping
    document.getElementById('btn-generer-mapping').addEventListener('click', genererMapping);

    // Upload mapping JSON
    document.getElementById('mapping-upload').addEventListener('change', chargerMappingFichier);
    document.getElementById('btn-restaurer').addEventListener('click', restaurer);
    document.getElementById('btn-export-csv').addEventListener('click', exportCSV);
    document.getElementById('search-correspondances').addEventListener('input', renderCorrespondances);

    // Analyse
    document.getElementById('btn-analyser').addEventListener('click', analyserFichier);
    document.getElementById('btn-extraire').addEventListener('click', extraireEntites);
    // Extract : upload fichier ou path local → charger dans le textarea
    document.getElementById('extract-file-upload').addEventListener('change', () => {
        const file = document.getElementById('extract-file-upload').files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = function(e) {
            let content = e.target.result;
            if (file.name.endsWith('.json')) {
                try {
                    const data = JSON.parse(content);
                    const first = Array.isArray(data) ? data[0] : data;
                    content = Object.values(first).filter(v => typeof v === 'string').join('\n');
                } catch(err) { /* garder brut */ }
            }
            if (content.length > 10000) content = content.substring(0, 10000) + '\n[… tronqué]';
            document.getElementById('extract-texte').value = content;
            showAlert('analyse-alert', `Fichier ${file.name} chargé.`, 'success');
        };
        reader.readAsText(file);
    });

    document.getElementById('analyse-file-upload').addEventListener('change', async () => {
        const file = document.getElementById('analyse-file-upload').files[0];
        if (!file) return;
        const formData = new FormData();
        formData.append('file', file);
        try {
            const resp = await fetch(API_BASE + '/fichier/upload', { method: 'POST', body: formData });
            if (!resp.ok) throw new Error((await resp.json()).detail || resp.statusText);
            const data = await resp.json();
            document.getElementById('analyse-path').value = data.path;
            showAlert('analyse-alert', `Fichier ${file.name} uploadé. Cliquez sur "Analyser la structure".`, 'success');
        } catch (e) { showAlert('analyse-alert', 'Erreur upload :' + e.message, 'error'); }
    });

    // Scoring
    document.getElementById('btn-scorer-texte').addEventListener('click', scorerTexte);
    document.getElementById('btn-scorer-fichier').addEventListener('click', scorerFichier);

    // Diagnostic
    document.getElementById('btn-comparer').addEventListener('click', comparerMoteurs);
    document.getElementById('btn-valider').addEventListener('click', validerTexte);
    // Upload fichier dans le champ compare
    document.getElementById('compare-file-upload').addEventListener('change', () => {
        const file = document.getElementById('compare-file-upload').files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = function(e) {
            let content = e.target.result;
            // Si c'est du JSON, extraire les valeurs string
            if (file.name.endsWith('.json')) {
                try {
                    const data = JSON.parse(content);
                    const first = Array.isArray(data) ? data[0] : data;
                    content = Object.values(first)
                        .filter(v => typeof v === 'string')
                        .join('\n');
                } catch(err) { /* garder le contenu brut */ }
            }
            // Tronquer à 5000 caractères pour le diagnostic
            if (content.length > 5000) content = content.substring(0, 5000) + '\n[… tronqué à 5000 caractères]';
            document.getElementById('compare-texte').value = content;
            showAlert('diagnostic-alert', `Fichier ${file.name} chargé (${content.length} caractères).`, 'success');
        };
        reader.readAsText(file);
    });

    document.getElementById('btn-exemple-diagnostic').addEventListener('click', () => {
        document.getElementById('compare-texte').value =
            "Bonjour Madame Nathalie GARCIA-LOPEZ, je me permets de vous écrire concernant " +
            "le dossier de M. Jean-Pierre de La Fontaine, né le 12/04/1985, habitant au " +
            "24 rue Victor Hugo, 92130 Issy-les-Moulineaux. Son email est " +
            "jean-pierre.delafontaine@gmail.com et son téléphone est 06 12 34 56 78. " +
            "Il est joignable aussi au +33 6 98 76 54 32. Monsieur de La Fontaine a signalé " +
            "un problème avec sa facture Orange. Alexandra, sa conseillère chez Sosh, lui a " +
            "proposé un tarif à 10,95 euros par mois. Données bancaires : IBAN FR76 3000 " +
            "6000 0112 3456 7890 189, carte 4532 0151 1283 0366 (CVV 456), numéro de " +
            "sécurité sociale 1 85 04 75 123 456 78, SIRET 732 829 320 00074. " +
            "IP: 192.168.1.42, MAC: AA:BB:CC:DD:EE:FF, plaque AB-123-CD. " +
            "Référence dossier n° 2024-78901, page 42, montant 300 euros. " +
            "Cordialement, Pierre Martin pierre.martin@example.com";
        document.getElementById('compare-fort').checked = true;
        document.getElementById('compare-tech').checked = true;
    });

    // Nav links
    document.querySelectorAll('.fr-nav__link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            window.location.hash = link.getAttribute('href');
        });
    });
});

function navigateTo() {
    const hash = window.location.hash.replace('#', '') || 'diagnostic';
    const pages = document.querySelectorAll('.page');
    pages.forEach(p => p.style.display = 'none');

    const target = document.getElementById('page-' + hash);
    if (target) {
        target.style.display = 'block';
    }

    // Mettre a jour la nav
    document.querySelectorAll('.fr-nav__link').forEach(link => {
        const href = link.getAttribute('href').replace('#', '');
        link.setAttribute('aria-current', href === hash ? 'page' : 'false');
    });

    // Mettre à jour le fil d'Ariane
    const breadcrumbLabels = {
        'pseudonymisation': 'Pseudonymisation',
        'import-fichier': 'Import fichier',
        'analyse': 'Analyse',
        'scoring-rgpd': 'Scoring RGPD',
        'correspondances': 'Correspondances',
        'restauration': 'Restauration',
        'diagnostic': 'Diagnostic',
        'documentation': 'Documentation',
    };
    const breadcrumbCurrent = document.getElementById('breadcrumb-current');
    if (breadcrumbCurrent) {
        breadcrumbCurrent.textContent = breadcrumbLabels[hash] || hash;
    }

    // Mettre à jour le titre de la page
    document.title = (breadcrumbLabels[hash] || 'Accueil') + ' — Anonymisation-synthesia';

    // Actualiser les correspondances si on va sur cette page
    if (hash === 'correspondances') {
        renderCorrespondances();
    }
}

// --- Pseudonymisation texte ---
async function pseudonymiser() {
    const texte = document.getElementById('input-texte').value.trim();
    if (!texte) {
        showAlert('alert-zone', 'Collez du texte avant de lancer.', 'warning');
        return;
    }

    const mode = document.querySelector('input[name="output-mode"]:checked').value;
    const detectionMode = document.querySelector('input[name="detection-mode"]:checked').value;
    const fort = document.getElementById('opt-fort').checked;
    const tech = document.getElementById('opt-tech').checked;
    const whitelist = parseList(document.getElementById('whitelist').value);
    const blacklist = parseList(document.getElementById('blacklist').value);

    document.getElementById('btn-pseudonymise').disabled = true;
    document.getElementById('btn-pseudonymise').textContent = 'Traitement...';

    try {
        const resp = await fetch(API_BASE + '/ner/anonymize', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                text: texte,
                mode: mode,
                detection_mode: detectionMode,
                fort: fort,
                tech: tech,
                whitelist: whitelist,
                blacklist: blacklist,
            }),
        });

        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }

        const data = await resp.json();
        document.getElementById('output-texte').value = data.texte_pseudonymise;

        // Stats
        document.getElementById('stat-entites').textContent = data.stats.total;
        document.getElementById('stat-score').textContent = data.score.total;
        document.getElementById('stat-niveau').textContent = data.score.niveau;
        document.getElementById('results-zone').style.display = 'block';

        // Correspondances
        correspondancesEnMemoire = data.correspondances;

        showAlert('alert-zone', `${data.stats.total} entité(s) détectée(s). Score RGPD : ${data.score.total} (${data.score.niveau}).`, 'success');

    } catch (e) {
        showAlert('alert-zone', 'Erreur :' + e.message, 'error');
    } finally {
        document.getElementById('btn-pseudonymise').disabled = false;
        document.getElementById('btn-pseudonymise').textContent = 'Pseudonymiser';
    }
}

// --- État global upload ---
let uploadedFilePath = null;

// --- Charger mapping depuis fichier uploadé ---
function chargerMappingFichier() {
    const fileInput = document.getElementById('mapping-upload');
    const file = fileInput.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const mapping = JSON.parse(e.target.result);
            document.getElementById('mapping-json').value = JSON.stringify(mapping, null, 2);
            showAlert('file-alert', `Mapping ${file.name} chargé avec succès.`, 'success');
        } catch (err) {
            showAlert('file-alert', `Le fichier ${file.name} n'est pas un JSON valide : ${err.message}`, 'error');
        }
    };
    reader.readAsText(file);
}

// --- Générer mapping ---
async function genererMapping() {
    const importMode = document.querySelector('input[name="import-mode"]:checked').value;
    let path;
    if (importMode === 'upload') {
        if (!uploadedFilePath) {
            showAlert('file-alert', 'Téléversez un fichier d\'abord.', 'warning');
            return;
        }
        path = uploadedFilePath;
    } else {
        path = document.getElementById('input-path').value.trim();
        if (!path) {
            showAlert('file-alert', 'Entrez le chemin du fichier.', 'warning');
            return;
        }
    }

    document.getElementById('btn-generer-mapping').disabled = true;
    document.getElementById('btn-generer-mapping').textContent = 'Analyse...';

    try {
        const resp = await fetch(API_BASE + '/mapping/generate?path=' + encodeURIComponent(path), {
            method: 'POST',
        });

        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }

        const mapping = await resp.json();
        document.getElementById('mapping-json').value = JSON.stringify(mapping, null, 2);
        showAlert('file-alert', 'Mapping généré. Vérifiez et ajustez si nécessaire, puis lancez le traitement.', 'success');

    } catch (e) {
        showAlert('file-alert', 'Erreur génération mapping :' + e.message, 'error');
    } finally {
        document.getElementById('btn-generer-mapping').disabled = false;
        document.getElementById('btn-generer-mapping').textContent = 'Générer le mapping automatiquement';
    }
}

// --- Upload fichier ---
async function uploadFichier() {
    const fileInput = document.getElementById('file-upload');
    const file = fileInput.files[0];
    if (!file) return;

    const statusDiv = document.getElementById('upload-status');
    const infoP = document.getElementById('upload-info');
    statusDiv.style.display = 'block';
    infoP.textContent = `Téléversement de ${file.name} (${(file.size / 1024 / 1024).toFixed(1)} Mo)…`;

    try {
        const formData = new FormData();
        formData.append('file', file);

        const resp = await fetch(API_BASE + '/fichier/upload', {
            method: 'POST',
            body: formData,
        });

        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }

        const data = await resp.json();
        uploadedFilePath = data.path;
        infoP.textContent = `${file.name} téléversé (${data.size} octets). Prêt pour le traitement.`;
        showAlert('file-alert', `Fichier ${file.name} téléversé avec succès.`, 'success');

    } catch (e) {
        infoP.textContent = '';
        statusDiv.style.display = 'none';
        uploadedFilePath = null;
        showAlert('file-alert', 'Erreur téléversement :' + e.message, 'error');
    }
}

// --- Traitement fichier ---
async function traiterFichier(dryRun) {
    const importMode = document.querySelector('input[name="import-mode"]:checked').value;

    let path;
    if (importMode === 'upload') {
        if (!uploadedFilePath) {
            showAlert('file-alert', 'Téléversez un fichier d\'abord.', 'warning');
            return;
        }
        path = uploadedFilePath;
    } else {
        path = document.getElementById('input-path').value.trim();
        if (!path) {
            showAlert('file-alert', 'Entrez le chemin du fichier.', 'warning');
            return;
        }
    }

    const mappingPath = document.getElementById('input-mapping-path').value.trim();
    const mappingJson = document.getElementById('mapping-json').value.trim();
    const mode = document.getElementById('file-mode').value;
    const detectionMode = document.getElementById('file-detection').value;
    const limit = document.getElementById('file-limit').value;

    const btnId = dryRun ? 'btn-dry-run' : 'btn-traiter-fichier';
    document.getElementById(btnId).disabled = true;
    document.getElementById(btnId).textContent = 'Traitement...';

    try {
        const fileFort = document.getElementById('file-fort') ? document.getElementById('file-fort').checked : false;
        const fileTech = document.getElementById('file-tech') ? document.getElementById('file-tech').checked : false;
        const body = {
            path: path,
            mode: mode,
            detection_mode: detectionMode,
            dry_run: dryRun,
            fort: fileFort,
            tech: fileTech,
        };
        if (mappingPath) body.mapping_path = mappingPath;
        if (mappingJson) {
            try {
                body.mapping = JSON.parse(mappingJson);
            } catch (e) {
                showAlert('file-alert', 'Le mapping JSON est invalide : ' + e.message, 'error');
                document.getElementById(btnId).disabled = false;
                document.getElementById(btnId).textContent = dryRun ? 'Aperçu (100 enreg.)' : 'Traiter le fichier';
                return;
            }
        }
        if (limit && parseInt(limit) > 0) body.limit = parseInt(limit);

        const resp = await fetch(API_BASE + '/fichier/anonymise', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(body),
        });

        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || resp.statusText);
        }

        const data = await resp.json();

        document.getElementById('file-total').textContent = data.total;
        document.getElementById('file-traites').textContent = data.traites;
        document.getElementById('file-remplacements').textContent = data.remplacements;
        document.getElementById('file-duree').textContent = data.duree_s + 's';
        document.getElementById('file-output-path').textContent = data.output_path ? 'Fichier : ' + data.output_path : 'Aperçu — aucun fichier écrit';
        document.getElementById('file-csv-path').textContent = data.csv_path ? 'Correspondances : ' + data.csv_path : '';
        document.getElementById('file-results').style.display = 'block';

        // Boutons de téléchargement
        const dlZone = document.getElementById('file-download-zone');
        if (dlZone) {
            dlZone.innerHTML = '';
            if (data.output_path) {
                const btnDl = document.createElement('a');
                btnDl.href = API_BASE + '/fichier/download?path=' + encodeURIComponent(data.output_path);
                btnDl.className = 'fr-btn fr-btn--sm fr-mr-2w';
                btnDl.textContent = 'Télécharger le résultat';
                btnDl.download = '';
                dlZone.appendChild(btnDl);
            }
            if (data.csv_path) {
                const btnCsv = document.createElement('a');
                btnCsv.href = API_BASE + '/fichier/download?path=' + encodeURIComponent(data.csv_path);
                btnCsv.className = 'fr-btn fr-btn--secondary fr-btn--sm';
                btnCsv.textContent = 'Télécharger les correspondances';
                btnCsv.download = '';
                dlZone.appendChild(btnCsv);
            }
        }

        showAlert('file-alert', `${data.traites} enregistrements traités, ${data.remplacements} remplacements en ${data.duree_s}s.`, 'success');

    } catch (e) {
        showAlert('file-alert', 'Erreur :' + e.message, 'error');
    } finally {
        document.getElementById(btnId).disabled = false;
        document.getElementById(btnId).textContent = dryRun ? 'Aperçu (100 enreg.)' : 'Traiter le fichier';
    }
}

// --- Restauration ---
async function restaurer() {
    const texte = document.getElementById('input-restauration').value.trim();
    if (!texte) {
        showAlert('page-restauration', 'Collez du texte pseudonymisé.', 'warning');
        return;
    }

    // Construire le mapping depuis les correspondances en memoire
    const mapping = {};
    correspondancesEnMemoire.forEach(c => {
        mapping[c.jeton] = c.valeur;
    });

    if (Object.keys(mapping).length === 0) {
        showAlert('page-restauration', 'Aucune correspondance en mémoire. Pseudonymisez du texte d\'abord.', 'warning');
        return;
    }

    try {
        const resp = await fetch(API_BASE + '/ner/deanonymize', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ text: texte, mapping: mapping }),
        });

        const data = await resp.json();
        document.getElementById('output-restauration').value = data.texte_original;
    } catch (e) {
        showAlert('page-restauration', 'Erreur :' + e.message, 'error');
    }
}

// --- Correspondances ---
function renderCorrespondances() {
    const search = (document.getElementById('search-correspondances').value || '').toLowerCase();
    const tbody = document.getElementById('tbody-correspondances');
    tbody.innerHTML = '';

    const filtered = correspondancesEnMemoire.filter(c =>
        !search || c.type.toLowerCase().includes(search) ||
        c.jeton.toLowerCase().includes(search) ||
        c.valeur.toLowerCase().includes(search)
    );

    filtered.forEach(c => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${escapeHtml(c.type)}</td><td><code>${escapeHtml(c.jeton)}</code></td><td>${escapeHtml(c.valeur)}</td>`;
        tbody.appendChild(tr);
    });
}

function exportCSV() {
    if (!correspondancesEnMemoire.length) return;
    let csv = 'type;jeton;valeur_originale\n';
    correspondancesEnMemoire.forEach(c => {
        csv += `${c.type};${c.jeton};${escapeCSV(c.valeur)}\n`;
    });
    downloadBlob(csv, 'correspondances.csv', 'text/csv');
}

// --- Analyse fichier ---
async function analyserFichier() {
    const path = document.getElementById('analyse-path').value.trim();
    if (!path) { showAlert('analyse-alert', 'Entrez le chemin du fichier.', 'warning'); return; }

    try {
        const resp = await fetch(API_BASE + '/fichier/analyze?path=' + encodeURIComponent(path), { method: 'POST' });
        if (!resp.ok) throw new Error((await resp.json()).detail || resp.statusText);
        const data = await resp.json();

        document.getElementById('analyse-format').textContent = data.format;
        document.getElementById('analyse-total').textContent = data.total_enregistrements;
        document.getElementById('analyse-champs').textContent = Object.keys(data.champs).length;

        const tbody = document.getElementById('tbody-analyse');
        tbody.innerHTML = '';
        for (const [champ, info] of Object.entries(data.champs)) {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td><code>${escapeHtml(champ)}</code></td><td>${escapeHtml(info.type)}</td><td>${escapeHtml(String(info.exemple || info.longueur || '').substring(0, 80))}</td>`;
            tbody.appendChild(tr);
        }
        document.getElementById('analyse-results').style.display = 'block';
    } catch (e) { showAlert('analyse-alert', 'Erreur :' + e.message, 'error'); }
}

async function extraireEntites() {
    let texte = document.getElementById('extract-texte').value.trim();
    // Si pas de texte collé, essayer de charger depuis le path local
    if (!texte) {
        const path = (document.getElementById('extract-path') || {}).value;
        if (path && path.trim()) {
            try {
                const resp = await fetch(API_BASE + '/fichier/analyze?path=' + encodeURIComponent(path.trim()), { method: 'POST' });
                if (resp.ok) {
                    const data = await resp.json();
                    // Extraire les exemples des champs string
                    texte = Object.values(data.champs || {})
                        .filter(c => c.type === 'string' && c.exemple)
                        .map(c => c.exemple).join('\n');
                    document.getElementById('extract-texte').value = texte;
                }
            } catch(e) { /* ignorer */ }
        }
    }
    if (!texte) { showAlert('analyse-alert', 'Collez du texte, chargez un fichier, ou renseignez un chemin local.', 'warning'); return; }

    try {
        const resp = await fetch(API_BASE + '/ner/extract', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                text: texte,
                detection_mode: document.getElementById('extract-mode').value,
                fort: document.getElementById('extract-fort').checked,
                tech: document.getElementById('extract-tech').checked,
            }),
        });
        if (!resp.ok) throw new Error((await resp.json()).detail || resp.statusText);
        const data = await resp.json();

        const tbody = document.getElementById('tbody-extract');
        tbody.innerHTML = '';
        data.entities.forEach(e => {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td>${escapeHtml(e.text)}</td><td>${escapeHtml(e.type)}</td><td>${escapeHtml(e.source)}</td><td>${e.score.toFixed(2)}</td>`;
            tbody.appendChild(tr);
        });
        document.getElementById('extract-results').style.display = 'block';
        showAlert('analyse-alert', `${data.count} entité(s) détectée(s).`, 'success');
    } catch (e) { showAlert('analyse-alert', 'Erreur :' + e.message, 'error'); }
}

// --- Scoring RGPD ---
async function scorerTexte() {
    const texte = document.getElementById('scoring-texte').value.trim();
    if (!texte) { showAlert('scoring-alert', 'Collez du texte.', 'warning'); return; }

    try {
        const resp = await fetch(API_BASE + '/ner/anonymize', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ text: texte, mode: 'mask', detection_mode: 'hybrid' }),
        });
        if (!resp.ok) throw new Error((await resp.json()).detail || resp.statusText);
        const data = await resp.json();

        document.getElementById('scoring-score').textContent = data.score.total;
        document.getElementById('scoring-niveau').textContent = data.score.niveau;
        document.getElementById('scoring-entites').textContent = data.stats.total;

        const tbody = document.getElementById('tbody-scoring');
        tbody.innerHTML = '';
        for (const [cat, count] of Object.entries(data.score.details)) {
            if (count > 0) {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td>${escapeHtml(cat)}</td><td>${count}</td>`;
                tbody.appendChild(tr);
            }
        }
        document.getElementById('scoring-texte-results').style.display = 'block';
    } catch (e) { showAlert('scoring-alert', 'Erreur :' + e.message, 'error'); }
}

async function scorerFichier() {
    const path = document.getElementById('scoring-fichier-path').value.trim();
    if (!path) { showAlert('scoring-alert', 'Entrez le chemin du fichier.', 'warning'); return; }

    const mappingPath = document.getElementById('scoring-mapping-path').value.trim();
    const body = { path: path };
    if (mappingPath) body.mapping_path = mappingPath;

    document.getElementById('btn-scorer-fichier').disabled = true;
    document.getElementById('btn-scorer-fichier').textContent = 'Analyse...';

    try {
        const resp = await fetch(API_BASE + '/fichier/score', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(body),
        });
        if (!resp.ok) throw new Error((await resp.json()).detail || resp.statusText);
        const data = await resp.json();

        document.getElementById('scoring-f-analyses').textContent = data.analyses;
        document.getElementById('scoring-f-moyen').textContent = data.score_moyen.toFixed(1);

        const tbody = document.getElementById('tbody-scoring-distrib');
        tbody.innerHTML = '';
        for (const [niveau, count] of Object.entries(data.distribution)) {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td>${escapeHtml(niveau)}</td><td>${count}</td>`;
            tbody.appendChild(tr);
        }
        document.getElementById('scoring-fichier-results').style.display = 'block';
    } catch (e) { showAlert('scoring-alert', 'Erreur :' + e.message, 'error'); }
    finally {
        document.getElementById('btn-scorer-fichier').disabled = false;
        document.getElementById('btn-scorer-fichier').textContent = 'Scorer le fichier';
    }
}

// --- Diagnostic ---
async function comparerMoteurs() {
    const texte = document.getElementById('compare-texte').value.trim();
    if (!texte) { showAlert('diagnostic-alert', 'Collez du texte.', 'warning'); return; }

    document.getElementById('btn-comparer').disabled = true;
    document.getElementById('btn-comparer').textContent = 'Comparaison...';

    try {
        const fort = document.getElementById('compare-fort').checked;
        const tech = document.getElementById('compare-tech').checked;
        const resp = await fetch(API_BASE + '/ner/compare', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ text: texte, fort: fort, tech: tech }),
        });
        if (!resp.ok) throw new Error((await resp.json()).detail || resp.statusText);
        const data = await resp.json();

        document.getElementById('compare-regex').textContent = data.diagnostic.regex_seul;
        document.getElementById('compare-ner').textContent = data.diagnostic.ner_seul;
        document.getElementById('compare-hybrid').textContent = data.diagnostic.hybrid;
        document.getElementById('compare-apport-ner').textContent = data.diagnostic.apport_ner.length > 0
            ? 'Apport NER : ' + data.diagnostic.apport_ner.join(', ')
            : 'Pas d\'apport NER supplémentaire';
        document.getElementById('compare-apport-regex').textContent = data.diagnostic.apport_regex.length > 0
            ? 'Apport regex : ' + data.diagnostic.apport_regex.join(', ')
            : 'Pas d\'apport regex supplémentaire';

        // Rendus anonymisés (6 modes)
        document.getElementById('rendu-regex').value = data.rendu_regex || '';
        document.getElementById('rendu-regex-fort').value = data.rendu_regex_fort || '';
        document.getElementById('rendu-regex-fort-tech').value = data.rendu_regex_fort_tech || '';
        document.getElementById('rendu-ner').value = data.rendu_ner || '';
        document.getElementById('rendu-hybrid').value = data.rendu_hybrid || '';
        document.getElementById('rendu-hybrid-fort-tech').value = data.rendu_hybrid_fort_tech || '';

        // Tableau comparatif côte à côte
        const tbody = document.getElementById('tbody-compare');
        tbody.innerHTML = '';

        // Indexer par texte
        const regexMap = {};
        data.regex_only.forEach(e => { regexMap[e.text] = e; });
        const nerMap = {};
        data.ner_only.forEach(e => { nerMap[e.text] = e; });
        const hybridMap = {};
        data.hybrid.forEach(e => { hybridMap[e.text] = e; });

        // Collecter toutes les entités uniques (préserver l'ordre hybrid d'abord)
        const seen = new Set();
        const allEntities = [];
        [...data.hybrid, ...data.regex_only, ...data.ner_only].forEach(e => {
            if (!seen.has(e.text)) {
                seen.add(e.text);
                allEntities.push(e.text);
            }
        });

        allEntities.forEach(text => {
            const tr = document.createElement('tr');
            const r = regexMap[text];
            const n = nerMap[text];
            const h = hybridMap[text];
            const dash = '<span style="color:#999">—</span>';
            tr.innerHTML = `<td><strong>${escapeHtml(text)}</strong></td>` +
                `<td>${r ? escapeHtml(r.type) : dash}</td>` +
                `<td>${n ? escapeHtml(n.type) + ' (' + n.score.toFixed(2) + ')' : dash}</td>` +
                `<td>${h ? escapeHtml(h.type) + ' (' + escapeHtml(h.source) + ')' : dash}</td>`;
            tbody.appendChild(tr);
        });

        document.getElementById('compare-results').style.display = 'block';

        // Recommandation dynamique
        const badges = ['badge-regex-fort', 'badge-hybrid-fort-tech'];
        badges.forEach(id => { const el = document.getElementById(id); if (el) el.style.display = 'none'; });
        document.getElementById('col-regex-fort').style.border = 'none';

        const textLength = texte.length;
        const nerApport = data.diagnostic.apport_ner.length;
        const regexApport = data.diagnostic.apport_regex.length;

        // Si le NER apporte beaucoup de détections en plus → hybrid recommandé
        // Si le NER apporte peu ou rien → regex+fort suffit (plus rapide, moins de faux positifs)
        if (nerApport > 2 && nerApport > regexApport) {
            const badge = document.getElementById('badge-hybrid-fort-tech');
            if (badge) badge.style.display = 'inline';
        } else {
            const badge = document.getElementById('badge-regex-fort');
            if (badge) badge.style.display = 'inline';
            document.getElementById('col-regex-fort').style.border = '2px solid var(--background-action-high-blue-france)';
            document.getElementById('col-regex-fort').style.borderRadius = '4px';
            document.getElementById('col-regex-fort').style.paddingTop = '0.5rem';
        }

    } catch (e) { showAlert('diagnostic-alert', 'Erreur :' + e.message, 'error'); }
    finally {
        document.getElementById('btn-comparer').disabled = false;
        document.getElementById('btn-comparer').textContent = 'Comparer';
    }
}

async function validerTexte() {
    const texte = document.getElementById('validate-texte').value.trim();
    if (!texte) { showAlert('diagnostic-alert', 'Collez du texte anonymisé.', 'warning'); return; }

    try {
        const resp = await fetch(API_BASE + '/ner/validate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ text: texte }),
        });
        if (!resp.ok) throw new Error((await resp.json()).detail || resp.statusText);
        const data = await resp.json();

        const callout = document.getElementById('validate-callout');
        if (data.clean) {
            callout.className = 'fr-callout fr-callout--green-emeraude';
            callout.innerHTML = '<p>Aucune fuite détectée. Le texte semble correctement anonymisé.</p>';
            document.getElementById('validate-table').style.display = 'none';
        } else {
            callout.className = 'fr-callout fr-callout--red-marianne';
            callout.innerHTML = `<p>${data.fuites.length} fuite(s) détectée(s). Des données personnelles restent visibles.</p>`;
            const tbody = document.getElementById('tbody-validate');
            tbody.innerHTML = '';
            data.fuites.forEach(f => {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td>${escapeHtml(f.text)}</td><td>${escapeHtml(f.type)}</td><td>${f.score.toFixed(2)}</td>`;
                tbody.appendChild(tr);
            });
            document.getElementById('validate-table').style.display = 'block';
        }
        document.getElementById('validate-results').style.display = 'block';
    } catch (e) { showAlert('diagnostic-alert', 'Erreur :' + e.message, 'error'); }
}

// --- Utilitaires ---
function parseList(str) {
    if (!str) return [];
    return str.split(',').map(s => s.trim()).filter(Boolean);
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function escapeCSV(str) {
    if (str.includes(';') || str.includes('"') || str.includes('\n')) {
        return '"' + str.replace(/"/g, '""') + '"';
    }
    return str;
}

function downloadBlob(content, filename, type) {
    const blob = new Blob([content], { type: type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

function showAlert(zoneId, message, type) {
    const zone = document.getElementById(zoneId);
    if (!zone) return;
    const cssClass = type === 'success' ? 'fr-alert--success' :
                     type === 'error' ? 'fr-alert--error' :
                     'fr-alert--warning';
    zone.innerHTML = `<div class="fr-alert ${cssClass} fr-mb-2w"><p>${escapeHtml(message)}</p></div>`;
    setTimeout(() => { zone.innerHTML = ''; }, 8000);
}
