# Guide d'installation

## Prérequis

| Élément | Version minimum | Vérification |
|---------|----------------|-------------|
| Python | 3.10+ (recommandé 3.12) | `python3 --version` |
| pip | dernière version | `pip3 --version` |
| Git | toute version récente | `git --version` |
| Espace disque | ~2 Go (modèle GLiNER2 + dictionnaires) | - |
| RAM | 4 Go minimum, 8 Go recommandé | - |

**Systèmes testés** : macOS (Apple Silicon M1/M2/M4), Linux. Windows non testé mais devrait fonctionner.

---

## Installation rapide

```bash
git clone [url-du-depot]
cd anonymisation-synthesia
bash install.sh
```

Le script `install.sh` fait tout automatiquement :
1. Vérifie la version de Python
2. Crée un environnement virtuel (`.venv/`)
3. Installe toutes les dépendances
4. Télécharge le modèle GLiNER2 (~800 Mo, une seule fois)
5. Lance les tests pour vérifier l'installation

---

## Installation manuelle

Si le script ne fonctionne pas sur votre système :

```bash
# 1. Créer l'environnement virtuel
python3 -m venv .venv

# 2. Installer les dépendances
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install python-multipart sse-starlette

# 3. Vérifier l'installation
.venv/bin/python3 -m pytest tests/ -v

# 4. Lancer le serveur
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8091
```

---

## Premier lancement

Au premier lancement, le modèle GLiNER2 est téléchargé automatiquement depuis HuggingFace (~800 Mo). Cela prend 1 à 5 minutes selon la connexion.

```
Chargement du modèle GLiNER2 fastino/gliner2-base-v1...
Modèle chargé en 4.9s sur mps
```

Les lancements suivants utilisent le cache local (`~/.cache/huggingface/`). Pas besoin d'internet.

---

## Mode hors ligne (air-gap)

Pour les environnements sans accès internet :

1. **Sur une machine connectée** : lancez le serveur une fois pour télécharger le modèle
2. **Copiez le cache** : `~/.cache/huggingface/hub/models--fastino--gliner2-base-v1/`
3. **Sur la machine air-gap** : collez le dossier au même emplacement
4. **Lancez avec** : `HF_HUB_OFFLINE=1 .venv/bin/uvicorn app.main:app --port 8091`

---

## Dépendances

### Obligatoires

| Package | Rôle |
|---------|------|
| `gliner2` | Modèle NER (détection contextuelle) |
| `torch` | Backend ML (MPS sur Apple Silicon, CPU sinon) |
| `fastapi` | API REST |
| `uvicorn` | Serveur ASGI |
| `pydantic-settings` | Configuration typée |

### Formats de fichiers (optionnels)

| Package | Format |
|---------|--------|
| `openpyxl` | XLSX / XLS |
| `odfpy` | ODS / ODT |
| `python-docx` | DOCX |
| `pdfplumber` | PDF (lecture) |
| `ijson` | JSON streaming (gros fichiers) |

Toutes les dépendances sont installées automatiquement par `install.sh` ou `pip install -r requirements.txt`.

---

## Vérification de l'installation

```bash
# Lancer les tests
.venv/bin/python3 -m pytest tests/ -v

# Résultat attendu : 50 passed, 0 failed
```

Si les tests passent, l'installation est complète.

---

## Résolution des problèmes

### Le modèle ne se charge pas

```
ModuleNotFoundError: No module named 'gliner2'
```

Solution : `pip install gliner2 torch`

### Port déjà utilisé

```
[Errno 48] Address already in use
```

Solution : changer le port `--port 8092` ou tuer le processus sur le port `lsof -ti:8091 | xargs kill`

### Pas de GPU / MPS

Le modèle fonctionne aussi en CPU (plus lent mais fonctionnel). Le device est détecté automatiquement.

### Import de fichier : 0 remplacements

Si vous traitez un fichier JSON structuré (comme SignalConso), vous devez fournir un mapping. Cliquez sur "Générer le mapping automatiquement" dans l'interface.
