# Anonymisation-synthesia

**Dépôt** : à créer (github)
**Branche principale** : `main`
**Python** : 3.12+
**Port** : 8090

---

## Description

API locale d'anonymisation/pseudonymisation de données personnelles combinant deux moteurs de détection PII :

- **GLiNER** (NER contextuel) — modèle entraîné, comprend le contexte sémantique, détecte les noms ambigus et les entités dans le texte libre
- **Regex + dictionnaires** (hérité de Pseudonymus) — déterministe, validateurs mathématiques (Luhn, NIR, SIRET), 884k noms, 169k prénoms

100 % local, zéro dépendance réseau. Aucune donnée ne transite vers un service externe.

**Utilisateurs cibles** : agents publics, DPO, équipes data manipulant des données personnelles (RGPD).

**Origine** : fusion de Pseudonymus standalone (regex) et Synthesia-API (GLiNER) en un outil autonome.

---

## Architecture

```
anonymisation-synthesia/
├── app/
│   ├── main.py                # FastAPI app, lifespan, montage routes
│   ├── config.py              # Settings Pydantic (modèles, seuils, device)
│   ├── api/
│   │   ├── routes_ner.py      # Routes /ner/* (extract, anonymize, deanonymize)
│   │   ├── routes_fichier.py  # Routes /fichier/* (upload, anonymise, download)
│   │   ├── routes_mapping.py  # Routes /mapping/* (generate, validate)
│   │   ├── routes_health.py   # Route /health
│   │   └── models.py          # Modèles Pydantic (request/response)
│   ├── moteur/
│   │   ├── regex.py           # 40+ regex + validateurs (Luhn, NIR, SIRET)
│   │   ├── dictionnaires.py   # Chargement noms/prénoms/stopwords/villes
│   │   ├── ner_gliner.py      # Singleton GLiNER, lazy-loading, device MPS
│   │   ├── detecteur.py       # Orchestrateur : regex -> NER -> fusion spans
│   │   ├── substitution.py    # TokenTable + remplacement par jetons
│   │   ├── scoring.py         # RiskScorer + Stats (scoring RGPD)
│   │   ├── pipeline.py        # Pipeline complet par enregistrement
│   │   ├── navigation.py      # Notation pointée, unwrap JSON stringifié
│   │   └── depseudonymise.py  # Restauration depuis correspondances CSV
│   ├── formats/
│   │   ├── base.py            # Interface load/save + dispatch par extension
│   │   ├── json_handler.py    # JSON + streaming ijson
│   │   ├── csv_handler.py     # CSV/TSV
│   │   ├── excel_handler.py   # XLSX/XLS
│   │   └── ...                # ODS, DOCX, ODT, PDF, TXT, MD
│   └── interface/             # Frontend DSFR
├── cli.py                     # CLI batch (argparse, streaming, progression)
├── install.sh                 # Script d'installation complet
├── data/                      # Dictionnaires de référence (9 fichiers JSON)
├── confidentiel/              # Correspondances CSV (gitignoré, chmod 700)
├── notes-internes/             # Recherche exploratoire, références, archives
├── tests/                     # 50 tests (regex, pipeline, API, golden)
├── e2e-tests/                 # Tests E2E (manifestes YAML)
├── PRD-01-plan-architecture.md       # PRD (100 % implémenté)
├── requirements.txt           # Dépendances
├── README.md                  # Documentation rapide
└── CLAUDE.md                  # Ce fichier
```

---

## Commandes essentielles

```bash
# Installation complète (venv + dépendances + modèle GLiNER2 + tests)
bash install.sh

# Lancer l'API
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8091

# Interface web : http://127.0.0.1:8091
# Swagger API   : http://127.0.0.1:8091/docs

# CLI : pseudonymiser un fichier
.venv/bin/python cli.py fichier.json --mapping mapping.json --pseudo --mode hybrid

# Modes de détection
--mode regex     # Regex + dictionnaires uniquement (rapide, déterministe)
--mode ner       # GLiNER uniquement (contextuel)
--mode hybrid    # Les deux combinés (par défaut si GLiNER disponible)

# Options
--fort           # Mode fort (prénoms isolés, propagation, majuscules)
--tech           # Détection technique (IPv4/v6, MAC, JWT, API keys)
--dry-run        # Aperçu sans écriture (100 enregistrements max)
--score-only     # Scoring RGPD sans pseudonymiser
--chunk-size N   # Streaming par paquets (gros fichiers)

# Lancer les tests
.venv/bin/pytest tests/
```

---

## Dépendances

| Package | Rôle |
|---------|------|
| `gliner2` | Détection NER/PII (modèle local, zero-shot, v1.2.5) |
| `torch` | Backend ML (MPS sur Apple Silicon) |
| `fastapi` | API REST avec Swagger auto |
| `uvicorn` | Serveur ASGI |
| `pydantic-settings` | Configuration typée |
| `ijson` | Streaming JSON (gros fichiers) |
| `tqdm` | Barre de progression CLI |
| `openpyxl` | Format XLSX (optionnel) |
| `odfpy` | Formats ODS/ODT (optionnel) |
| `python-docx` | Format DOCX (optionnel) |
| `pdfplumber` | Format PDF (optionnel) |

---

## Modèle GLiNER2

| Modèle | Paramètres | Usage |
|--------|------------|-------|
| `fastino/gliner2-base-v1` | 205M | Extraction généraliste zero-shot (PII, personnes, organisations, lieux) |
| `fastino/gliner2-large-v1` | 340M | Performance accrue (si la mémoire le permet) |

Un seul modèle chargé (base par défaut). Zero-shot : les labels PII sont passés en paramètre, pas besoin de modèle PII séparé. Optimisations : `quantize=True` (fp16) + `compile=True` (torch.compile).

Chargement en singleton, lazy-loading au premier appel. Device auto : MPS (Apple Silicon) > CPU.

---

## Modes d'anonymisation

| Mode | Résultat | Réversible |
|------|----------|------------|
| `mask` | `[PERSON_1]`, `[EMAIL_2]` | Oui (via mapping CSV) |
| `redact` | `████████` | Non |
| `hash` | `a1b2c3d4` (MD5 court) | Non |
| `anon` | `***` (hérité Pseudonymus) | Non |

---

## Conventions

- Langue : français (commits, docs, messages, interface)
- Git : forme nominale (voir règles workspace parent)
- Code Python : type hints, docstrings en français, variables en anglais
- Pas de credentials en clair

---

## Points d'attention

- **GLiNER** tourne en local — aucune donnée envoyée à l'extérieur
- **`confidentiel/`** ne doit jamais être versionné (chmod 700, gitignoré)
- **Fichiers > 100 Mo** : utiliser `--chunk-size` en CLI ou le mode chemin local en API
- **Mémoire** : les deux modèles GLiNER + dictionnaires consomment ~2-3 Go RAM
- **Premier appel NER** : le chargement du modèle prend 10-30s, les appels suivants sont rapides
- **Fallback** : si GLiNER n'est pas installé, le mode bascule automatiquement sur `regex`

---


## État du projet

| Métrique | Valeur |
|----------|--------|
| Routes API | 19 (toutes testées 200) |
| Pages UI | 8 (DSFR conformes) |
| Tests pytest | 75 (0 échec) |
| Tests E2E | 21 manifestes générés |
| Documentation | 11 fichiers (docs/) |
| PRD | 100 % implémenté |

---

## Documentation

- [Installation](docs/installation.md) — prérequis, rapide, manuelle, air-gap
- [Guide utilisateur](docs/guide-utilisateur.md) — 6 parcours pas à pas
- [CLI](docs/cli.md) — commandes, options, exemples
- [API REST](docs/api-reference.md) — 19 routes avec curl
- [Mapping](docs/mapping.md) — guide complet
- [Types d'entités](docs/types-entites.md) — 20+ types, scoring RGPD
- [Sécurité](docs/securite.md) — cycle de vie PII, logs
- [Performances](docs/performances.md) — temps, mémoire
- [Exemples](docs/exemples.md) — fichiers de test
- [Spécifications fonctionnelles](docs/specifications-fonctionnelles.md)
- [Spécifications techniques](docs/specifications-techniques.md)
- [Modèle GLiNER2](docs/modele-gliner2.md) — fonctionnement, stockage, singleton, air-gap, fallback
