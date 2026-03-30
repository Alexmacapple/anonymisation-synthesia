#!/bin/bash
# ============================================================
# Installation complète — anonymisation-synthesia
# ============================================================
# Usage : bash install.sh
# Prérequis : Python 3.12+, pip
# ============================================================

set -e

echo "============================================================"
echo "  Anonymisation-synthesia — Installation"
echo "============================================================"
echo ""

# --- Vérification Python ---
PYTHON=""
for cmd in python3.12 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        version=$("$cmd" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "ERREUR : Python 3.10+ requis. Installez Python 3.12 :"
    echo "  brew install python@3.12    (macOS)"
    echo "  apt install python3.12      (Ubuntu/Debian)"
    exit 1
fi

echo "Python : $($PYTHON --version)"

# --- Création du venv ---
if [ ! -d ".venv" ]; then
    echo ""
    echo "Création de l'environnement virtuel..."
    $PYTHON -m venv .venv
    echo "  .venv créé"
else
    echo ""
    echo "Environnement virtuel existant (.venv)"
fi

# --- Installation des dépendances ---
echo ""
echo "Installation des dépendances..."
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt -q

# Dépendances supplémentaires non dans requirements.txt
.venv/bin/pip install python-multipart sse-starlette urllib3 requests -q

echo "  Dépendances installées"

# --- Vérification des dictionnaires ---
echo ""
if [ -f "data/noms.json" ] && [ -f "data/prenoms.json" ]; then
    noms=$(python3 -c "import json; print(len(json.load(open('data/noms.json'))))" 2>/dev/null || echo "?")
    prenoms=$(python3 -c "import json; print(len(json.load(open('data/prenoms.json'))))" 2>/dev/null || echo "?")
    echo "Dictionnaires : $noms noms, $prenoms prénoms"
else
    echo "ERREUR : dictionnaires manquants dans data/"
    echo "  Copiez-les depuis Pseudonymus : cp -r /chemin/pseudonymus/data/ data/"
    exit 1
fi

# --- Téléchargement du modèle GLiNER2 ---
echo ""
echo "Téléchargement du modèle GLiNER2 (première fois uniquement)..."
.venv/bin/python3 -c "
from gliner2 import GLiNER2
print('  Chargement du modèle fastino/gliner2-base-v1...')
model = GLiNER2.from_pretrained('fastino/gliner2-base-v1')
result = model.extract_entities('Test Jean Dupont', ['personne'], include_confidence=True)
entites = sum(len(v) for v in result.get('entities', {}).values())
print(f'  Modèle chargé et testé ({entites} entité(s) détectée(s))')
" 2>/dev/null || {
    echo "  ATTENTION : le modèle GLiNER2 n'a pas pu être chargé."
    echo "  Le mode regex fonctionnera sans GLiNER2."
    echo "  Pour résoudre : vérifiez votre connexion internet et relancez install.sh"
}

# --- Création du répertoire confidentiel ---
mkdir -p confidentiel
chmod 700 confidentiel
echo ""
echo "Répertoire confidentiel/ créé (chmod 700)"

# --- Lancement des tests ---
echo ""
echo "Lancement des tests..."
.venv/bin/python3 -m pytest tests/ -q --tb=line 2>&1

# --- Résumé ---
echo ""
echo "============================================================"
echo "  Installation terminée"
echo "============================================================"
echo ""
echo "  Lancer le serveur :"
echo "    .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8091"
echo ""
echo "  Interface web : http://127.0.0.1:8091"
echo "  Swagger API   : http://127.0.0.1:8091/docs"
echo ""
echo "  CLI :"
echo "    .venv/bin/python3 cli.py fichier.json --pseudo --mode hybrid"
echo "    .venv/bin/python3 cli.py --help"
echo ""
echo "============================================================"
