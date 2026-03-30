# Guide CLI

L'outil s'utilise en ligne de commande pour traiter des fichiers sans passer par l'interface web.

---

## Syntaxe

```bash
.venv/bin/python3 cli.py [FICHIER] [OPTIONS]
```

---

## Commandes principales

### Pseudonymiser un fichier

```bash
# Document non structuré (DOCX, PDF, TXT) — pas besoin de mapping
.venv/bin/python3 cli.py document.docx --pseudo --mode hybrid

# Fichier structuré avec mapping
.venv/bin/python3 cli.py export.json --mapping mapping.json --pseudo --mode hybrid

# Anonymisation irréversible (*** au lieu de [PERSONNE_1])
.venv/bin/python3 cli.py export.json --mapping mapping.json --anon --mode hybrid
```

Le fichier anonymisé est écrit à côté du fichier source avec le suffixe `_PSEUDO` (ex: `export_PSEUDO.json`).
Les correspondances sont sauvegardées dans `confidentiel/correspondances.csv`.

### Aperçu (dry-run)

Traite 100 enregistrements sans écrire de fichier. Utile pour vérifier avant de lancer sur un gros fichier.

```bash
.venv/bin/python3 cli.py export.json --mapping mapping.json --dry-run --mode hybrid
```

### Scoring RGPD

Évalue le risque sans anonymiser.

```bash
.venv/bin/python3 cli.py export.json --mapping mapping.json --score-only
```

### Générer un mapping

Inspecte le fichier et propose un mapping squelette basé sur les noms de colonnes.

```bash
.venv/bin/python3 cli.py export.json --mapping-generate
```

Le mapping est affiché en JSON sur la sortie standard. Redirigez-le dans un fichier :

```bash
.venv/bin/python3 cli.py export.json --mapping-generate > mapping.json
```

### Traiter un dossier entier

```bash
.venv/bin/python3 cli.py --input-dir dossier/ --mapping mapping.json --pseudo --mode hybrid
```

Traite tous les fichiers supportés du dossier (JSON, CSV, XLSX, DOCX, PDF, etc.).

---

## Modes de détection

| Option | Mode | Description |
|--------|------|-------------|
| `--mode hybrid` | Hybrid (défaut) | Regex + GLiNER2 combinés — couverture maximale |
| `--mode regex` | Regex seul | Patterns + dictionnaires — très rapide |
| `--mode ner` | NER seul | GLiNER2 — détection contextuelle |

---

## Options

| Option | Description |
|--------|-------------|
| `--mapping fichier.json` | Fichier de mapping (voir [mapping.md](mapping.md)) |
| `--pseudo` | Pseudonymisation réversible (jetons `[PERSONNE_1]`) |
| `--anon` | Anonymisation irréversible (`***`) |
| `--dry-run` | Aperçu sur 100 enregistrements, pas de fichier écrit |
| `--score-only` | Scoring RGPD sans pseudonymiser |
| `--mapping-generate` | Générer un mapping squelette |
| `--fort` | Mode fort : prénoms isolés, salutations, dates de naissance, plaques |
| `--tech` | Détection technique : IPv4/v6, MAC, JWT, clés API |
| `--input-dir dossier/` | Traiter tous les fichiers d'un dossier |
| `--mode regex\|ner\|hybrid` | Mode de détection (défaut : hybrid) |

---

## Exemples concrets

### Fichier JSON simple

```bash
# Fichier : clients.json
# [{"nom": "Dupont", "email": "jean@test.fr", "commentaire": "Bonjour..."}]

# Générer le mapping
.venv/bin/python3 cli.py clients.json --mapping-generate > mapping-clients.json

# Vérifier sur 10 enregistrements
.venv/bin/python3 cli.py clients.json --mapping mapping-clients.json --dry-run

# Traiter tout le fichier
.venv/bin/python3 cli.py clients.json --mapping mapping-clients.json --pseudo --mode hybrid
```

### Fichier CSV

```bash
# Même principe — le format est détecté automatiquement
.venv/bin/python3 cli.py export.csv --mapping mapping.json --pseudo --mode hybrid
```

### Fichier SignalConso (JSON avec unwrap)

```bash
# Le mapping doit inclure la section "structure.unwrap"
.venv/bin/python3 cli.py confidentiel/CourrierSRC.json \
  --mapping mapping-signalconso.json \
  --pseudo --mode hybrid
```

### Document Word ou PDF

```bash
# Pas de mapping nécessaire — tout le texte est scanné
.venv/bin/python3 cli.py rapport.docx --pseudo --mode hybrid
.venv/bin/python3 cli.py courrier.pdf --pseudo --mode hybrid
```

### Mode fort + technique

```bash
# Détection maximale : noms isolés + IP + JWT + MAC
.venv/bin/python3 cli.py fichier.json --mapping mapping.json --pseudo --fort --tech
```

### Dossier entier

```bash
# Traiter tous les fichiers d'un dossier
.venv/bin/python3 cli.py --input-dir exports/ --mapping mapping.json --pseudo

# Sans mapping (tous les fichiers sont traités comme du texte brut)
.venv/bin/python3 cli.py --input-dir documents/ --pseudo --mode hybrid
```

---

## Sortie

### Fichier anonymisé

Le fichier de sortie est écrit à côté du fichier source :

```
export.json       →  export_PSEUDO.json
rapport.docx      →  rapport_PSEUDO.docx
donnees.csv       →  donnees_PSEUDO.csv
courrier.pdf      →  courrier_PSEUDO.txt  (PDF → texte)
```

### Correspondances CSV

Sauvegardées dans `confidentiel/correspondances.csv` (chmod 600) :

```csv
type;jeton;valeur_originale
personne;[PERSONNE_1];Jean Dupont
email;[EMAIL_1];jean@test.fr
tel;[TEL_1];06 12 34 56 78
```

### Rapport de traitement

Affiché sur stderr :

```
============================================================
RAPPORT DE TRAITEMENT
============================================================
Enregistrements : 100/31891 traités

Remplacements par type :
  email                     :    100
  nom                       :    100
  personne                  :    204
  prenom                    :    100
  tel                       :     75
  TOTAL                     :    579

Score RGPD moyen : 35.9 (CRITIQUE)
============================================================
```

---

## Fonctionnalités non disponibles en CLI (web uniquement)

| Fonctionnalité | Alternative CLI |
|----------------|----------------|
| Upload de fichier | Utiliser le chemin local directement |
| Téléchargement du résultat | Le fichier est écrit sur disque |
| Batch dossier (web) | `--input-dir` en CLI |
| Comparaison des moteurs (`/ner/compare`) | À venir (`--compare`) |
| Extraction sans anonymisation (`/ner/extract`) | À venir (`--extract`) |
| Validation post-anonymisation (`/ner/validate`) | À venir (`--validate`) |
| Analyse de structure (`/fichier/analyze`) | À venir (`--analyze`) |
| Restauration (`/ner/deanonymize`) | À venir (`--restore`) |

Ces fonctionnalités sont accessibles via l'API REST (voir [api-reference.md](api-reference.md)) ou le Swagger (`/docs`).
