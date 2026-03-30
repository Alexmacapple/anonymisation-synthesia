# Spécifications techniques

**Projet** : anonymisation-synthesia
**Version** : 0.1.0
**Date** : 2026-03-29
**Statut** : livré

---

## 1. Stack technique

| Composant | Technologie | Version |
|-----------|-------------|---------|
| Langage | Python | 3.12 |
| Framework API | FastAPI | >= 0.115 |
| Serveur ASGI | Uvicorn | >= 0.34 |
| Modèle NER | GLiNER2 (`gliner2`) | 1.2.5 |
| Backend ML | PyTorch | >= 2.11 |
| Frontend | HTML5 + JavaScript vanilla | - |
| Design System | DSFR (Design System de l'État) | embarqué |
| Validation | Pydantic | >= 2.12 |
| Tests | pytest | >= 9.0 |

---

## 2. Architecture des modules

```
app/
├── main.py              # Point d'entrée FastAPI, lifespan, routes NER/mapping/health
├── config.py             # Variables de configuration (HOST, PORT, MODEL_NAME, etc.)
├── api/
│   ├── models.py         # 6 modèles Pydantic (request/response)
│   └── routes_fichier.py # 9 routes /fichier/*, upload, download, SSE, async
├── moteur/
│   ├── regex.py          # 40+ regex compilées, Span dataclass, validateurs, detect_regex()
│   ├── ner_gliner.py     # Singleton NERService, lazy-loading, chunking, déduplication
│   ├── detecteur.py      # detect_hybrid(), fusion spans, whitelist/blacklist, validation dico
│   ├── pipeline.py       # process_text(), process_record(), orchestration complète
│   ├── substitution.py   # TokenTable (28 préfixes), normaliser_personne(), substituer_spans()
│   ├── scoring.py        # RiskScorer (4 catégories, 5 niveaux), Stats
│   ├── navigation.py     # get_path(), set_path(), get_text_fields(), unwrap/rewrap JSON
│   ├── dictionnaires.py  # Singleton Dictionnaires (9 datasets)
│   └── depseudonymise.py # charger_correspondances(), depseudonymiser_texte/fichier()
├── formats/
│   └── base.py           # load_file(), save_file(), 11 formats, dispatch par extension
└── interface/
    ├── index.html        # 8 pages DSFR, formulaires, navigation hash
    ├── app.js            # 20+ fonctions JS, SPA routing, état global
    ├── style.css         # Styles complémentaires DSFR
    └── dsfr/             # Assets DSFR (CSS, JS, fonts, icônes)
```

---

## 3. Modèles de données

### 3.1 Span (unité de détection)

```python
@dataclass
class Span:
    start: int            # Position début dans le texte (0-indexed)
    end: int              # Position fin (exclusive)
    entity_type: str      # "email_txt", "tel_txt", "personne", etc.
    value: str            # Texte extrait
    score: float          # 1.0 (regex) ou 0-1 (NER)
    source: str           # "regex" | "ner" | "blacklist"
    risk_type: str        # "direct" | "finance" | "tech" | "indirect"
```

Invariants :
- `0 <= start < end <= len(texte)`
- `texte[start:end] == value`
- Les spans retournés par `detect_hybrid()` sont triés par `start` croissant et sans chevauchement

### 3.2 TokenTable (correspondances)

```python
class TokenTable:
    _counters: dict[str, int]                          # Compteur par type
    _typed: dict[str, dict[str, tuple[int, str]]]     # {type: {key_normalisée: (num, valeur_originale)}}
    _personnes: dict[str, tuple[str, str]]             # {key_normalisée: (pid, valeur_originale)}
```

28 préfixes de jetons :
```
ID, UUID, PRENOM, NOM, EMAIL, TEL, CP, GENRE, IBAN, NIR, CB, CVV, SIRET, SIREN,
ID_FISCAL, URL, VOIE, ORGANISATION, VILLE, DATE_NAISSANCE, ADRESSE, IP, IPV4, IPV6,
MAC, JWT, API_KEY, PLAQUE, GPS, DATE, MONTANT, PERSONNE
```

Déduplication : même valeur (normalisée en lowercase) = même jeton.

### 3.3 RiskScorer

```python
class RiskScorer:
    POINTS = {'finance': 5, 'direct': 3, 'tech': 2, 'indirect': 1}
    score: int
    details: dict[str, int]   # {'direct': n, 'finance': n, 'tech': n, 'indirect': n}
```

### 3.4 Modèles Pydantic (API)

| Modèle | Champs principaux |
|--------|-------------------|
| `NERAnonymizeRequest` | text (1-500k), mode (mask/anon/redact/hash), detection_mode, fort, tech, whitelist, blacklist |
| `NERAnonymizeResponse` | texte_original, texte_pseudonymise, correspondances, stats, score |
| `NERExtractRequest` | text, labels, detection_mode, fort, tech, threshold (0-1) |
| `NERExtractResponse` | entities, count, detection_mode |
| `NERDeanonymizeRequest` | text, mapping (dict) |
| `NERDeanonymizeResponse` | texte_original, remplacements |
| `HealthResponse` | status, version, ner (dict), dictionnaires (dict) |
| `FichierAnonymiseRequest` | path, mapping_path, mapping, mode, detection_mode, fort, tech, dry_run, limit |
| `FichierAnonymiseResponse` | output_path, csv_path, total, traites, remplacements, score_moyen, niveau, duree_s, correspondances |

---

## 4. Pipeline de traitement

### 4.1 Texte brut (`process_text`)

```
Entrée: texte brut
    │
    ▼
detect_hybrid(texte, mode, fort, tech, whitelist, blacklist)
    ├── regex.detect_regex(texte)        → spans_regex
    ├── ner.extract(texte)               → spans_ner
    └── fusion + déduplication + filtrage → spans_unifiés
    │
    ▼
substituer_spans(texte, spans, tokens)   → texte anonymisé
    │
    ▼
Sortie: {texte_pseudonymise, correspondances, stats, score}
```

### 4.2 Enregistrement structuré (`process_record`)

```
Entrée: record (dict) + mapping
    │
    ├── Unwrap JSON stringifié (si structure.unwrap configuré)
    │
    ├── Phase 1 : champs sensibles
    │   Pour chaque champ dans mapping.champs_sensibles :
    │   - Résoudre le chemin (notation pointée)
    │   - Remplacer la valeur par un jeton typé
    │
    ├── Phase 2 : texte libre
    │   Pour chaque champ dans mapping.texte_libre :
    │   - Résoudre le chemin (supporte arrays avec [])
    │   - Ajouter les noms du déclarant (lookup_noms) à la blacklist
    │   - detect_hybrid() sur le texte
    │   - substituer_spans()
    │
    ├── Rewrap JSON stringifié
    │
    └── gc.collect()
    │
    ▼
Sortie: record modifié
```

### 4.3 Fusion des spans

```python
def _fusionner_spans(spans_regex, spans_ner) -> list[Span]:
    tous = spans_regex + spans_ner
    tous.sort(key=lambda s: (s.start, -s.end))

    resultat = [tous[0]]
    for span in tous[1:]:
        if chevauchement(resultat[-1], span):
            gagnant = résoudre(resultat[-1], span)
            resultat[-1] = gagnant
        else:
            resultat.append(span)
    return resultat
```

Priorités de résolution :
1. Regex finance (IBAN, NIR, CB, SIRET) > tout
2. NER > regex heuristique
3. Span le plus long en cas d'égalité

---

## 5. Moteur NER

### 5.1 Singleton

```python
class NERService:
    _instance = None           # Singleton
    _model = None              # GLiNER2 (chargé au premier appel)
    _device = None             # "mps" | "cpu" (auto-détecté)
    _available = False         # True si gliner2 est installé
```

### 5.2 Modèle

- Identifiant : `fastino/gliner2-base-v1`
- Paramètres : 205M
- Encodeur : `microsoft/deberta-v3-base`
- Cache : `~/.cache/huggingface/hub/models--fastino--gliner2-base-v1/`

### 5.3 Labels PII (français)

```python
DEFAULT_PII_LABELS = [
    "personne", "email", "téléphone", "adresse",
    "IBAN", "numéro de sécurité sociale", "carte bancaire",
    "adresse IP", "date de naissance", "organisation",
    "lieu", "date",
]
```

### 5.4 Mapping types NER → internes

```python
TYPE_MAP_NER = {
    "personne": "personne",     "email": "email_txt",
    "téléphone": "tel_txt",     "adresse": "adresse_txt",
    "IBAN": "iban_txt",         "numéro de sécurité sociale": "nir_txt",
    "carte bancaire": "cb_txt", "adresse IP": "ip_txt",
    "date de naissance": "date_naiss_txt",
    "organisation": "orga_txt", "lieu": "ville_txt",
    "date": "date_txt",
}
```

### 5.5 Chunking

Textes > 10 000 caractères : découpage aux limites de phrases (`(?<=[.!?])\s+`), extraction par chunk, ajustement des offsets, déduplication par proximité (même texte + même type + distance < 50 caractères).

---

## 6. Moteur regex

### 6.1 Groupes de patterns

| Groupe | Regex | Validateur | Catégorie risque |
|--------|-------|-----------|-----------------|
| Finance | RX_IBAN | `iban_check()` (mod-97) | finance |
| Finance | RX_CB | `luhn_check()` | finance |
| Finance | RX_NIR | `nir_check()` (checksum) | finance |
| Finance | RX_CVV | - | finance |
| Finance | RX_SIRET | `siret_check()` (Luhn) | indirect |
| Finance | RX_NUM_FISCAL | contexte négatif | finance |
| Email | RX_MAILTO, RX_EMAIL_OBFUSCATED, RX_EMAIL_AVEC, RX_EMAIL_ESPACE, RX_EMAIL | - | direct |
| Téléphone | RX_TEL_FUZZY, RX_TEL_PREFIXE, RX_TEL | - | direct |
| URL | RX_URL | - | indirect |
| Organisation | RX_ORGA_AGRESSIF | - | indirect |
| Adresse | RX_VOIE_NUM, RX_VOIE_SANS | - | indirect |
| Code postal | RX_CP | contexte négatif | indirect |
| Personne | RX_SALUTATION, RX_TITRE, RX_PRENOM_NOM_MAJ, RX_PRENOM_NOM | - | direct |
| Fort | RX_DATE_NAISS, RX_GPS, RX_PLAQUE, RX_PRENOM_ISOLE, RX_PREFIXES, RX_MAJ_LONG, RX_VILLE_COMPOSEE | - | variable |
| Tech | RX_IPV4, RX_IPV6, RX_MAC, RX_JWT, RX_API_KEY | - | tech |

### 6.2 Contexte négatif

Patterns rejetés avant et après un nombre :
- Avant : `n°`, `page`, `article`, `kg`, `€`, `%`, `degrés`
- Après : `kg`, `€`, `%`, `exemplaires`, `pages`

### 6.3 Déduplication interne

Quand plusieurs regex matchent la même zone (ex: RX_EMAIL et RX_EMAIL_ESPACE), le span le plus long est conservé.

---

## 7. Dictionnaires

| Fichier | Contenu | Entrées |
|---------|---------|---------|
| `noms.json` | Patronymes INSEE (UPPERCASE) | 884 314 |
| `prenoms.json` | Prénoms INSEE M+F (UPPERCASE) | 169 244 |
| `stopwords-capitalises.json` | Mots capitalisés à ne jamais pseudonymiser | 242 |
| `stopwords-minuscules.json` | Mots minuscules à ne jamais pseudonymiser | 151 |
| `majuscules-garder.json` | Mots en majuscules à préserver | 94 |
| `villes-france.json` | Top villes françaises | 97 |
| `mots-organisations.json` | Mots-clés organisations | 38 |
| `contexte-institution.json` | Mots contexte institutionnel | 60 |
| `acronymes-garder.json` | Acronymes à préserver | 12 |

Chargés au démarrage en singleton. Temps de chargement : ~0.1s.

---

## 8. Formats de fichiers

### 8.1 Dispatch

```python
FORMAT_LOADERS = {
    '.json': json.load,   '.csv': load_csv,     '.tsv': load_csv(delimiter='\t'),
    '.xlsx': load_xlsx,    '.xls': load_xlsx,    '.ods': load_ods,
    '.docx': load_docx,   '.odt': load_odt,     '.pdf': load_pdf,
    '.txt': load_txt,     '.md': load_txt,
}
```

### 8.2 Convention de sortie

- Entrée : `export.json` → Sortie : `export_PSEUDO.json`
- Entrée : `rapport.pdf` → Sortie : `rapport_PSEUDO.txt` (pas de réécriture PDF)
- Format JSON : indenté 2 espaces, `ensure_ascii=False`

### 8.3 Documents non structurés

Les formats DOCX, ODT, PDF, TXT, MD retournent un seul enregistrement :
```python
[{"texte": "contenu complet du document", "_source": "nom_fichier.ext"}]
```

---

## 9. API REST

### 9.1 Routes

| Méthode | Route | Module | Description |
|---------|-------|--------|-------------|
| POST | `/ner/anonymize` | main.py | Anonymiser du texte |
| POST | `/ner/extract` | main.py | Extraire les entités |
| POST | `/ner/deanonymize` | main.py | Restaurer |
| GET | `/ner/entity-types` | main.py | Types supportés |
| POST | `/ner/compare` | main.py | Comparer les moteurs |
| POST | `/ner/validate` | main.py | Vérifier post-anonymisation |
| POST | `/mapping/generate` | main.py | Générer mapping |
| POST | `/mapping/validate` | main.py | Valider mapping |
| GET | `/health` | main.py | État du service |
| GET | `/health/stats` | main.py | Stats dictionnaires |
| POST | `/fichier/anonymise` | routes_fichier.py | Anonymiser fichier |
| POST | `/fichier/upload` | routes_fichier.py | Upload multipart |
| GET | `/fichier/download` | routes_fichier.py | Télécharger résultat |
| POST | `/fichier/score` | routes_fichier.py | Scoring fichier |
| POST | `/fichier/dry-run` | routes_fichier.py | Aperçu |
| POST | `/fichier/batch` | routes_fichier.py | Dossier entier |
| POST | `/fichier/analyze` | routes_fichier.py | Structure fichier |
| GET | `/fichier/progress/{job_id}` | routes_fichier.py | SSE progression |
| POST | `/fichier/anonymise-async` | routes_fichier.py | Traitement asynchrone |

### 9.2 Sécurité des routes

- Bind : `127.0.0.1` uniquement
- Pas d'authentification (usage local)
- Upload : 400 Mo max, chmod 600, nettoyage atexit
- Download : whitelist extensions (.json, .csv, .xlsx, etc.) + vérification chemin (confidentiel/ ou _PSEUDO)
- CORS : `*` (localhost)

### 9.3 Lifespan

Au démarrage :
1. Avertissement si DEBUG activé
2. Chargement des dictionnaires (singleton)
3. Initialisation du service NER (vérification disponibilité, pas de chargement modèle)

Le modèle GLiNER2 est chargé au premier appel NER (lazy loading).

---

## 10. Frontend

### 10.1 Architecture

SPA (Single Page Application) avec navigation par hash (`#pseudonymisation`, `#import-fichier`, etc.). Pas de framework JavaScript — vanilla JS.

### 10.2 État global

```javascript
let correspondancesEnMemoire = [];  // Correspondances de la dernière pseudonymisation
let uploadedFilePath = null;        // Chemin du fichier uploadé
```

### 10.3 Composants DSFR utilisés

Header, navigation, fil d'Ariane, formulaires (input, textarea, select, radio, checkbox, upload), boutons, tiles, tableaux, callouts, alertes, accordéons, footer, summary (sommaire).

---

## 11. CLI

### 11.1 Arguments

```
cli.py [FICHIER] [OPTIONS]

Positional:
  input                  Fichier à traiter

Options:
  --mapping PATH         Fichier de mapping JSON
  --input-dir DIR        Traiter un dossier entier
  --pseudo               Pseudonymisation réversible (exclusif)
  --anon                 Anonymisation irréversible (exclusif)
  --dry-run              Aperçu 100 enregistrements (exclusif)
  --score-only           Scoring RGPD (exclusif)
  --mapping-generate     Générer mapping squelette (exclusif)
  --mode {regex,ner,hybrid}  Mode de détection (défaut: hybrid)
  --fort                 Mode fort
  --tech                 Détection technique
```

### 11.2 Sortie

- Fichier : `{nom}_PSEUDO.{ext}` à côté du fichier source
- Correspondances : `confidentiel/correspondances.csv`
- Rapport : stderr (remplacements par type, score RGPD, échantillons)
- Progression : `{n}/{total} ({speed} enreg/s, ETA {s}s)`

---

## 12. Tests

### 12.1 Couverture

| Fichier | Tests | Couvre |
|---------|-------|-------|
| `test_regex.py` | 25 | Validateurs, détection email/tel/URL, contexte négatif, modes fort/tech, déduplication |
| `test_pipeline.py` | 11 | process_text, process_record, unwrap, whitelist, jetons, restauration |
| `test_api.py` | 8 | Routes health, anonymize, extract, deanonymize, whitelist, validation |
| `test_golden.py` | 4 | Non-régression vs API Loïc, Alexandra dans texte libre, hybrid >= regex |
| `test_formats.py` | 12 | Détection format, load JSON/CSV/TXT, save JSON/CSV |
| `test_detecteur.py` | 9 | Hybrid, regex seul, whitelist, blacklist, fort, tech, chevauchements |
| **Total** | **71** (zéro échec) | |

---

## 13. Configuration

| Variable | Défaut | Description |
|----------|--------|-------------|
| `HOST` | `127.0.0.1` | Adresse d'écoute |
| `PORT` | `8090` | Port (config), `8091` (usage courant) |
| `MODEL_NAME` | `fastino/gliner2-base-v1` | Modèle GLiNER2 |
| `NER_THRESHOLD` | `0.4` | Seuil de confiance NER |
| `HF_HUB_OFFLINE` | non défini | `1` pour mode air-gap |

---

## 14. Dépendances

### Obligatoires

| Package | Version min | Rôle |
|---------|-------------|------|
| `gliner2` | 1.2.5 | Modèle NER |
| `torch` | 2.11 | Backend ML |
| `fastapi` | 0.115 | API REST |
| `uvicorn` | 0.34 | Serveur ASGI |
| `pydantic-settings` | - | Configuration |
| `python-multipart` | - | Upload fichier |
| `sse-starlette` | - | Server-Sent Events |

### Formats (optionnels)

| Package | Format |
|---------|--------|
| `openpyxl` | XLSX |
| `odfpy` | ODS/ODT |
| `python-docx` | DOCX |
| `pdfplumber` | PDF |
| `ijson` | JSON streaming |
