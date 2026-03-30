# Changelog

## v0.1.0 (2026-03-29 — 2026-03-30)

Première version complète. 60 commits de développement.

### Architecture

- Moteur hybride de détection PII : regex (40+ patterns avec validateurs Luhn, mod-97, checksum NIR) + GLiNER2 v1.2.5 (NER contextuel, 205M paramètres)
- Pipeline par spans : regex et NER tournent sur le texte original, fusion par chevauchement, substitution en une passe
- Singleton NER avec lazy loading (modèle chargé au premier appel ~5s, réutilisé ensuite ~0.2s)
- Device auto : MPS (Apple Silicon) > CPU
- Fallback gracieux : si GLiNER2 absent, bascule automatique sur regex

### Détection

- 3 modes : regex, NER, hybrid (défaut)
- 4 modes d'anonymisation : mask (`[PERSONNE_1]`), anon (`***`), redact (`████`), hash (MD5)
- Mode fort : prénoms isolés, salutations, titres, dates de naissance, plaques, GPS
- Mode tech : IPv4/v6, MAC, JWT, clés API
- Whitelist / blacklist configurables
- Contexte négatif : "page 42", "300 euros", "n° 12345" ne sont pas anonymisés
- Validation post-NER par dictionnaires (884k noms, 169k prénoms)

### API REST (19 routes)

- `/ner/anonymize`, `/ner/extract`, `/ner/deanonymize`, `/ner/compare`, `/ner/validate`, `/ner/entity-types`
- `/fichier/anonymise`, `/fichier/upload`, `/fichier/download`, `/fichier/score`, `/fichier/dry-run`, `/fichier/batch`, `/fichier/analyze`, `/fichier/progress/{job_id}`, `/fichier/anonymise-async`
- `/mapping/generate`, `/mapping/validate`
- `/health`, `/health/stats`

### Interface web DSFR (8 pages)

- Diagnostic (page d'accueil) : comparaison 6 modes côte à côte, upload fichier, texte d'exemple, badge recommandé dynamique
- Pseudonymisation, Import fichier, Analyse, Scoring RGPD, Correspondances, Restauration, Documentation

### CLI

- `--pseudo`, `--anon`, `--dry-run`, `--score-only`, `--mapping-generate`
- `--fort`, `--tech`, `--mode regex|ner|hybrid`, `--input-dir`
- Sans mapping : scanne toutes les valeurs string
- Progression temps réel avec vitesse et ETA

### Formats

JSON, CSV, TSV, XLSX, XLS, ODS, DOCX, ODT, PDF (→ TXT), TXT, MD

### Tests

- 75 tests pytest (0 échec)
- Tests de non-régression (golden results)
- 21 manifestes E2E

### Sécurité

- 100 % local, nettoyage mémoire, logs sans PII, air-gap validé, correspondances CSV chmod 600

### Documentation (13 fichiers)

Installation, guide utilisateur, CLI, API, mapping, sécurité, types d'entités, performances, exemples, modèle GLiNER2, textes de test, spécifications fonctionnelles et techniques

### Origine

- Pseudonymus v2 / standalone : dictionnaires, regex, DSFR
- GLiNER2 v1.2.5 (Fastino Labs) + optimisations Loïc Baconnier
- Synthesia-API (bacoco) : architecture NER

### Licence

GPL v3
