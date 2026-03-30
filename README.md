# Anonymisation-synthesia

![Python](https://img.shields.io/badge/Python-3.12-blue) ![Licence](https://img.shields.io/badge/Licence-GPL%20v3-green) ![Tests](https://img.shields.io/badge/Tests-75%20passed-brightgreen) ![Routes](https://img.shields.io/badge/API-19%20routes-orange)

API locale d'anonymisation de données personnelles (PII) combinant deux moteurs de détection complémentaires :

- **GLiNER2** (NER contextuel) — modèle d'intelligence artificielle qui comprend le contexte sémantique
- **Regex + dictionnaires** — 40+ patterns avec validateurs mathématiques (Luhn, mod-97, checksum NIR) + 884 000 noms de famille + 169 000 prénoms

**100 % local.** Aucune donnée personnelle ne transite par internet. Le modèle tourne sur votre machine (CPU ou GPU/MPS).

---

## Installation

```bash
git clone [url-du-depot]
cd anonymisation-synthesia

# Installation complète (venv + dépendances + modèle GLiNER2 + tests)
bash install.sh
```

Prérequis : Python 3.10+

Au premier lancement, le modèle GLiNER2 (~800 Mo) est téléchargé depuis HuggingFace. Les lancements suivants utilisent le cache local.

---

## Démarrage rapide

### Interface web

```bash
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8091
```

Ouvrir http://127.0.0.1:8091 dans le navigateur.

### CLI

```bash
# Pseudonymiser un document (DOCX, PDF, TXT — pas besoin de mapping)
.venv/bin/python3 cli.py document.docx --pseudo --mode hybrid

# Pseudonymiser un fichier structuré avec mapping
.venv/bin/python3 cli.py export.json --mapping mapping.json --pseudo --mode hybrid

# Générer un mapping automatiquement
.venv/bin/python3 cli.py export.json --mapping-generate

# Aperçu sur 100 enregistrements
.venv/bin/python3 cli.py export.json --mapping mapping.json --dry-run

# Scoring RGPD sans anonymiser
.venv/bin/python3 cli.py export.json --mapping mapping.json --score-only
```

### API REST

Swagger : http://127.0.0.1:8091/docs

```bash
# Anonymiser du texte
curl -X POST http://127.0.0.1:8091/ner/anonymize \
  -H "Content-Type: application/json" \
  -d '{"text": "Jean Dupont, email jean@test.fr, tel 06 12 34 56 78"}'
```

---

## Fonctionnalités

### 3 modes de détection

| Mode | Détection | Vitesse | Usage |
|------|-----------|---------|-------|
| **hybrid** (défaut) | Regex + GLiNER2 | ~0.5s/texte | Couverture maximale |
| **regex** | Patterns + dictionnaires | ~0.01s/texte | Fichiers volumineux |
| **ner** | GLiNER2 seul | ~0.2s/texte | Texte libre, noms ambigus |

### 4 modes d'anonymisation

| Mode | Résultat | Réversible |
|------|----------|------------|
| `mask` | `[PERSONNE_1]`, `[EMAIL_1]` | Oui (correspondances CSV) |
| `anon` | `***` | Non |
| `redact` | `████████` | Non |
| `hash` | `a1b2c3d4` | Non |

### 11 formats supportés

JSON, CSV, TSV, XLSX, XLS, ODS, DOCX, ODT, PDF, TXT, MD

### 19 routes API

- `/ner/anonymize` — anonymiser du texte
- `/ner/extract` — extraire les entités sans anonymiser
- `/ner/deanonymize` — restaurer avec le mapping
- `/ner/compare` — comparer regex vs NER vs hybrid
- `/ner/validate` — vérifier qu'un texte anonymisé ne contient plus de PII
- `/fichier/anonymise` — traiter un fichier complet
- `/fichier/upload` — téléverser un fichier
- `/fichier/score` — scoring RGPD sans anonymiser
- `/mapping/generate` — générer un mapping automatiquement
- Et 10 autres — voir le Swagger `/docs`

### 8 pages dans l'interface web

Pseudonymisation, Import fichier, Analyse, Scoring RGPD, Correspondances, Restauration, Diagnostic, Documentation

---

## Documentation

| Document | Contenu |
|----------|---------|
| [Installation](docs/installation.md) | Prérequis, installation rapide et manuelle, mode air-gap, troubleshooting |
| [Guide utilisateur](docs/guide-utilisateur.md) | 6 parcours documentés pas à pas |
| [CLI](docs/cli.md) | Commandes, options, exemples concrets |
| [API REST](docs/api-reference.md) | 19 routes avec exemples curl |
| [Mapping](docs/mapping.md) | Guide complet (plat, imbriqué, unwrap, arrays, whitelist) |
| [Types d'entités](docs/types-entites.md) | 20+ types détectés, scoring RGPD, faux positifs connus |
| [Sécurité](docs/securite.md) | Cycle de vie PII, logs, correspondances, mode air-gap |
| [Performances](docs/performances.md) | Temps de traitement, mémoire, recommandations par volume |
| [Exemples](docs/exemples.md) | Fichiers de test prêts à copier-coller |
| [Spécifications fonctionnelles](docs/specifications-fonctionnelles.md) | Ce que l'outil fait (point de vue métier) |
| [Spécifications techniques](docs/specifications-techniques.md) | Comment il le fait (point de vue développeur) |
| [Modèle GLiNER2](docs/modele-gliner2.md) | Fonctionnement du modèle NER, stockage, singleton, air-gap |

---

## Tests

```bash
# 75 tests unitaires et d'intégration
.venv/bin/python3 -m pytest tests/ -v
```

---

## Architecture

```
app/
├── main.py                # FastAPI (19 routes + Swagger)
├── moteur/
│   ├── regex.py           # 40+ regex en détecteurs de spans
│   ├── ner_gliner.py      # Singleton GLiNER2 (lazy loading, MPS)
│   ├── detecteur.py       # Fusion hybrid regex + NER
│   ├── substitution.py    # TokenTable (jetons dédupliqués)
│   ├── scoring.py         # Scoring RGPD
│   ├── pipeline.py        # Traitement par enregistrement
│   └── dictionnaires.py   # 884k noms + 169k prénoms
├── formats/
│   └── base.py            # Multi-format (11 formats)
└── interface/             # Frontend DSFR (8 pages)
```

---

## Origine et crédits

Ce projet s'est fortement inspiré de [Pseudonymus v2](https://forge.apps.education.fr/vibe-edu/pseudonymus2/), application JavaScript de pseudonymisation côté client développée sur la Forge des Communs Numériques Éducatifs.

[Pseudonymus standalone](https://github.com/Alexmacapple/pseudonymus-standalone) en reprend les dictionnaires (patronymes INSEE, prénoms) et la logique de détection par regex, mais constitue une réécriture complète :

- Portage en **Python** avec CLI complète (modes pseudo, anon, dry-run, scoring, batch, streaming)
- Interface web **DSFR** (Design System de l'État) avec serveur local
- Gestion native du **JSON structuré** : notation pointée, unwrap de JSON imbriqué, mappings configurables
- Support **multi-format** : CSV, XLSX, ODS, DOCX, ODT, PDF, TXT, MD

Anonymisation-synthesia ajoute à cet héritage un **moteur NER contextuel** basé sur [GLiNER2](https://github.com/fastino-ai/GLiNER2), grâce à l'inspiration et aux travaux de [Loïc Baconnier](https://github.com/bacoco) :

- **GLiNER2 v1.2.5** — modèle NER zero-shot (205M paramètres) pour la détection contextuelle des données personnelles. Loïc a contribué à cette version avec 4 pull requests d'optimisation runtime (vectorisation preprocessing, batching post-encodeur, fp16, torch.compile), délivrant un speedup de 1.2x à 2x
- **[Synthesia-API](https://github.com/bacoco/Synthesia-API)** — l'architecture des routes NER (extract, anonymize, deanonymize) et l'intégration GLiNER en singleton avec lazy loading sont inspirées du service NER de cette API

L'architecture hybride (regex + NER → fusion par spans sur le texte original) permet une couverture supérieure à chaque moteur pris isolément : les regex garantissent la fiabilité sur les données structurées (IBAN, NIR, carte bancaire avec validateurs mathématiques), tandis que GLiNER2 détecte les noms et entités dans le texte libre que les regex ne peuvent pas attraper.

---

## Licence

GPL v3 — voir [LICENSE](LICENSE)
