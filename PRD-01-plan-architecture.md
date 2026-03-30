# Plan d'architecture — anonymisation-synthesia

---

## Résumé exécutif

**Problème** : les agents publics et DPO doivent anonymiser des fichiers contenant des données personnelles (RGPD) avant partage ou archivage. Les outils existants sont soit déterministes mais aveugles au contexte (Pseudonymus/regex), soit contextuels mais dépendants du réseau (Synthesia-API/GLiNER distant).

**Solution** : une API locale autonome qui combine les deux approches — détection NER contextuelle (GLiNER2) + regex validées mathématiquement (Luhn, mod-97, checksum NIR) + dictionnaires massifs (884k noms, 169k prénoms). Traitement 100 % local après le téléchargement initial du modèle (~800 Mo, une seule fois).

**Cible** : Mac Studio M1 Ultra 64 Go. FastAPI + Swagger. CLI + interface web DSFR.

**MVP** : 4 routes (`/ner/anonymize`, `/fichier/anonymise`, `/mapping/generate`, `/health`) + CLI. Critère de livraison : anonymiser le fichier SignalConso (112 Mo, 31 891 enregistrements) de bout en bout.

**Hors périmètre MVP** : authentification, routes expérimentales (classify/relations/schema), OCR/images, interface web avancée.

**KPI produit** :

| KPI | Cible | Mesure |
|-----|-------|--------|
| Taux d'anonymisation correcte (recall) | >= 95 % sur le jeu de test golden | Entités PII détectées / entités PII réelles |
| Taux de faux positifs (precision) | <= 5 % | Mots légitimes pseudonymisés à tort / total remplacements |
| Temps moyen par fichier (1 000 enregistrements) | < 2 min (mode hybrid, MPS) | Chronométrage bout en bout |
| Taux de fichiers traités sans intervention | >= 90 % | Fichiers terminés sans erreur / fichiers soumis |
| Restauration (mode mask) | 100 % | Correspondances CSV → texte original identique |

---

## Contexte

- **Pseudonymus** (existant) : excellent sur les formats structurés (JSON, CSV, XLSX), les regex validées avec validateurs mathématiques (IBAN mod-97, NIR checksum, CB Luhn, SIRET Luhn), les dictionnaires massifs (884k noms, 169k prénoms), mais aveugle au contexte sémantique
- **Synthesia-API** (Loïc) : excellent sur la détection contextuelle (GLiNER comprend "Rose Martin" = 2 PII), mais limité au texte brut, pas de multi-format, dépendance réseau
- **Objectif** : combiner les deux en local avec FastAPI

### Environnement cible

| Ressource | Valeur |
|-----------|--------|
| Machine | Mac Studio |
| Processeur | Apple M1 Ultra |
| RAM | 64 Go |
| Device ML | MPS (Metal Performance Shaders) |
| Python | 3.12 (Homebrew) |
| OS | macOS (Darwin) |

Avec 64 Go de RAM, aucune contrainte mémoire : les deux modèles GLiNER2 (base 205M + large 340M si besoin), les dictionnaires (884k noms) et un fichier de 112 Mo tiennent largement. Le M1 Ultra supporte MPS nativement pour l'inférence GPU.

---

## Parcours utilisateur

### Persona

Agent public, DPO ou data analyst qui doit anonymiser un fichier contenant des données personnelles avant de le partager, le stocker ou l'analyser.

### Scénario A — texte brut ou document non structuré (pas de mapping)

L'utilisateur a un texte, un PDF, un Word ou un email. Il ne sait pas ce qu'est un mapping et n'en a pas besoin.

1. Il ouvre `http://127.0.0.1:8090`, colle son texte ou uploade son fichier
2. L'outil détecte automatiquement que c'est du texte non structuré (pas de JSON tabulaire)
3. GLiNER2 + regex scannent le texte complet, sans mapping
4. Il voit le résultat anonymisé avec un score RGPD
5. Il télécharge le fichier anonymisé + correspondances CSV

```bash
# CLI — pas de --mapping, le texte entier est scanné
python cli.py document.docx --pseudo --mode hybrid
python cli.py courrier.pdf --pseudo --mode hybrid
```

**Aucun mapping requis.** L'outil traite le fichier comme un bloc de texte et applique la détection NER + regex sur tout le contenu.

### Scénario B — fichier structuré avec mapping (JSON, CSV, XLSX)

L'utilisateur a un export de base de données (JSON, CSV, XLSX) avec des colonnes identifiées. Le mapping lui permet de cibler les champs sensibles et de configurer whitelist/blacklist.

1. Il ouvre l'interface et importe son fichier structuré
2. Il clique sur "Générer le mapping" — l'outil détecte les colonnes et propose un mapping automatique
3. Il ajuste si besoin (ajouter une whitelist, exclure un champ)
4. Il lance le traitement — barre de progression pour les gros fichiers
5. Il télécharge le fichier anonymisé (même format) + correspondances CSV

```bash
# CLI — avec mapping (structuré)
python cli.py export.json --mapping mapping.json --pseudo --mode hybrid

# CLI — génération auto du mapping
python cli.py export.json --mapping-generate
```

### Scénario C — CLI batch

```bash
# Un dossier entier (les fichiers non structurés sont traités sans mapping)
python cli.py --input-dir dossier/ --pseudo --mode hybrid

# Un dossier avec mapping partagé (fichiers structurés de même format)
python cli.py --input-dir dossier/ --mapping mapping.json --pseudo
```

Le fichier anonymisé et les correspondances sont écrits sur disque. Pas d'interaction.

### Logique de détection du mode

```
Fichier uploadé
    │
    ├── Extension .docx / .pdf / .txt / .md / .odt ?
    │       → Mode texte non structuré (pas de mapping requis)
    │       → Tout le texte est scanné par NER + regex
    │
    ├── Extension .json / .csv / .xlsx / .ods ?
    │       ├── Mapping fourni ? → Mode structuré (champs_sensibles + texte_libre)
    │       └── Pas de mapping ? → Proposer génération auto, ou scanner chaque cellule comme du texte
    │
    └── Texte collé (API /ner/anonymize) ?
            → Mode texte brut, pas de mapping
```

### Critères d'acceptation

| Critère | Seuil |
|---------|-------|
| Un texte de 1 000 car. est anonymisé en moins de 3 secondes (mode hybrid, MPS) | Bloquant |
| Le fichier de sortie est dans le même format que l'entrée | Bloquant |
| Les correspondances CSV permettent de restaurer 100 % du texte original (mode mask) | Bloquant |
| Le score RGPD est calculé pour chaque enregistrement | Bloquant |
| L'outil fonctionne sans connexion internet (après le premier téléchargement du modèle) | Bloquant |
| Le mode hybrid détecte au moins autant d'entités que le meilleur des deux moteurs seuls (voir golden results) | Bloquant |
| L'interface web est utilisable sans formation | Souhaité |

### Golden results — baseline de qualité

Résultats de référence issus du test client API option A (2026-03-29) sur 3 enregistrements SignalConso. Le moteur local doit détecter **au moins** ces entités :

**Enregistrement 1 — DOAR_IDENT=10786453**

| Entité | Type | Détecté par regex | Détecté par NER (API Loïc) |
|--------|------|-------------------|---------------------------|
| jean martin | personne | Oui (dictionnaire) | Oui (0.99) |
| jean.martin@example.com | email | Oui (regex) | Oui (masqué) |
| 09 75 73 94 62 | téléphone | Oui (regex) | Oui (masqué) |
| 94110 | code postal | Oui (regex) | Oui (masqué) |
| 05/09/2023 | date | Non | Oui (0.87) |
| **Total** | | **4** | **5** |

**Enregistrement 2 — DOAR_IDENT=10923955**

| Entité | Type | Détecté par regex | Détecté par NER (API Loïc) |
|--------|------|-------------------|---------------------------|
| Sophie LAMBERT | personne | Oui (dictionnaire) | Oui (0.99) — mais masquage partiel (`[PERSON_1] MARC`) |
| sophie.lambert@example.com | email | Oui (regex) | Oui (masqué) |
| 0296507550 | téléphone | Oui (regex) | Oui (masqué) |
| 19/01/2024 | date | Non | Oui (0.94) |
| **Total** | | **3** | **4** |

**Enregistrement 3 — DOAR_IDENT=10753659**

| Entité | Type | Détecté par regex | Détecté par NER (API Loïc) |
|--------|------|-------------------|---------------------------|
| Pierre Durand | personne | Partiel (Pierre dans prénoms) | Oui (0.99) |
| Alexandra | personne (texte libre) | Non (pas dans les champs structurés) | Oui (0.93) |
| pierre.durand@example.com | email | Oui (regex) | Oui (masqué) |
| 0695222038 | téléphone | Oui (regex) | Oui (masqué) |
| 28/07/2023 | date | Non | Oui (0.84) |
| Sosh | organisation | Non | Oui (0.94) |
| **Total** | | **3** | **6** |

**Synthèse baseline**

| Mode | Enreg. 1 | Enreg. 2 | Enreg. 3 | Total |
|------|----------|----------|----------|-------|
| Regex seul | 4 | 3 | 3 | **10** |
| NER seul (API Loïc) | 5 | 4 | 6 | **15** |
| **Hybrid (cible)** | **>= 5** | **>= 4** | **>= 6** | **>= 15** |

Le mode hybrid doit détecter au minimum 15 entités sur ces 3 enregistrements. Idéalement plus (les regex attrapent des choses que le NER rate : SIRET validé par checksum, codes postaux 5 chiffres).

Défaut connu chez Loïc à corriger : "Sophie LAMBERT" masqué partiellement (`[PERSON_1] MARC`). Notre moteur doit masquer le nom complet.

---

## MVP vs catalogue complet

### MVP (livrable 1) — LIVRÉ le 2026-03-29

| Route MVP | Statut |
|-----------|--------|
| `POST /ner/anonymize` | FAIT |
| `POST /fichier/anonymise` | FAIT |
| `POST /mapping/generate` | FAIT |
| `GET /health` | FAIT |

| Composant MVP | Statut |
|---------------|--------|
| CLI (`cli.py`) avec `--pseudo`, `--mode hybrid`, `--dry-run` | FAIT |
| Interface web DSFR (4 pages) | FAIT |
| 46 tests pytest | FAIT |
| Footer DSFR conforme | FAIT |

**Critère de livraison MVP** : anonymiser le fichier SignalConso de bout en bout → FAIT (testé sur 5 et 100 enregistrements).

### Catalogue complet (livrable 2 — restant)

| Priorité | Route | Statut |
|----------|-------|--------|
| **P1** | `/ner/extract` | FAIT |
| **P1** | `/ner/deanonymize` | FAIT |
| **P1** | `/ner/entity-types` | FAIT |
| **P2** | `/fichier/score` | FAIT |
| **P2** | `/fichier/dry-run` | FAIT |
| **P2** | `/fichier/batch` | FAIT |
| **P2** | `/fichier/analyze` | FAIT |
| **P2** | `/fichier/upload` (multipart) | FAIT |
| **P2** | `/fichier/download` | FAIT (whitelist extensions + vérification chemin) |
| **P2** | `/fichier/progress` (SSE) | FAIT (+ route `/fichier/anonymise-async`) |
| **P2** | `/health/stats` | FAIT |
| **P3** | `/ner/compare` | FAIT |
| **P3** | `/ner/validate` | FAIT |
| **P4** | `/mapping/validate` | FAIT |
| **Retiré** | `/ner/classify` | create_schema() KO en phase 0 |
| **Retiré** | `/ner/relations` | create_schema() KO en phase 0 |
| **Retiré** | `/ner/schema` | create_schema() KO en phase 0 |

### Autres éléments non traités

| Élément | Statut | Faisable maintenant |
|---------|--------|---------------------|
| Route `/mapping/generate` (MVP) | FAIT | - |
| Golden results (100 enregistrements annotés) | PARTIEL — 3 golden + 4 tests non-régression + 100 dry-run | HORS SCOPE SESSION — annotation manuelle nécessaire |
| Métriques precision/recall/F1 formelles | Non mesurées | HORS SCOPE SESSION — nécessite jeu de test annoté |
| Test non-régression vs API Loïc (reco 8) | FAIT — 4 tests golden, Alexandra détectée | - |
| Sécurité : nettoyage mémoire (`gc.collect`) | FAIT | - |
| Sécurité : suppression fichiers temporaires | FAIT — registre + atexit cleanup | - |
| Sécurité : avertissement mode DEBUG | FAIT | - |
| Mode air-gap (`HF_HUB_OFFLINE=1`) | FAIT — testé OK, modèle depuis cache local | - |
| Test performance (31k enreg. < 30 min) | Non mesuré formellement | HORS SCOPE SESSION — estimation ~4.8h hybrid, ~15 min regex |
| README.md | FAIT | - |
| spaCy (`--nlp`) dans le pipeline | Documenté, pas implémenté | GLiNER2 couvre ce besoin |
| Route `/ner/compare` (diagnostic) | FAIT | - |
| Route `/ner/validate` (contrôle qualité) | FAIT | - |

---

## Décisions techniques

| Décision | Justification |
|----------|---------------|
| Package `gliner2` v1.2.5 | API unifiée (NER + classification + extraction structurée + relations), optimisations runtime de Loïc (1.2x-2x speedup), fp16 + torch.compile |
| Regex avant NER dans le pipeline | Les regex financières ont des validateurs mathématiques plus fiables que le NER : IBAN (mod-97), NIR (checksum), CB (Luhn), SIRET (Luhn) |
| FastAPI (pas stdlib HTTP) | Async natif, Pydantic intégré, OpenAPI/Swagger auto, SSE pour progression |
| Pas d'authentification | Usage local uniquement, bind sur `127.0.0.1` |
| Formats éclatés en sous-modules | Chaque format a ses dépendances optionnelles, facilite la maintenance |
| `ijson` pour le streaming + batching NER | Streaming enregistrement par enregistrement avec buffer de 32 textes avant appel GLiNER (un appel NER par enregistrement serait trop lent) |
| Fusion par chevauchement de spans | Test simple `(start1 < end2 and start2 < end1)` sur les positions caractère, plus clair que l'IoU (concept vision) |
| Mode par défaut `hybrid` avec fallback `regex` | Si GLiNER est installé et chargé : mode `hybrid`. Sinon : fallback automatique sur `regex` sans erreur |
| Option `--nlp` (spaCy) conservée | Pseudonymus utilise spaCy `fr_core_news_sm` comme pré-filtre NER pour les noms étrangers/rares hors dictionnaire. GLiNER2 couvre largement ce cas, mais `--nlp` reste disponible comme option complémentaire (dépendance optionnelle) |
| Contexte négatif intégré dans `regex.py` | Les regex de nombres rejettent les faux positifs contextuels : n°, page, article, kg, euros, %, etc. Ce filtrage est critique pour éviter de pseudonymiser "page 42" ou "300 euros". Repris tel quel de Pseudonymus |

---

## Structure de fichiers

```
anonymisation-synthesia/
|-- app/
|   |-- __init__.py
|   |-- main.py                    # FastAPI app, lifespan, montage routes
|   |-- config.py                  # Settings Pydantic (modèles, seuils, device, ports)
|   |
|   |-- api/
|   |   |-- __init__.py
|   |   |-- routes_ner.py          # Routes /ner/* (extract, anonymize, deanonymize, entity-types)
|   |   |-- routes_fichier.py      # Routes /fichier/* (upload, anonymise-fichier, download)
|   |   |-- routes_mapping.py      # Routes /mapping/* (generate, validate)
|   |   |-- routes_health.py       # Route /health
|   |   |-- models.py              # Modèles Pydantic (request/response)
|   |
|   |-- moteur/
|   |   |-- __init__.py
|   |   |-- regex.py               # 40+ regex + validateurs (repris de pseudonymise.py)
|   |   |-- dictionnaires.py       # Chargement noms/prénoms/stopwords/villes
|   |   |-- ner_gliner.py          # Singleton GLiNER2 v1.2.5, lazy-loading, device MPS
|   |   |-- detecteur.py           # Orchestrateur : regex -> NER -> fusion spans
|   |   |-- substitution.py        # TokenTable + remplacement par jetons
|   |   |-- scoring.py             # RiskScorer + Stats (scoring RGPD)
|   |   |-- pipeline.py            # Pipeline complet par enregistrement
|   |   |-- navigation.py          # Notation pointée, unwrap JSON stringifié, arrays
|   |   |-- depseudonymise.py      # Restauration depuis correspondances CSV
|   |
|   |-- formats/
|   |   |-- __init__.py
|   |   |-- base.py                # Interface load/save + dispatch par extension
|   |   |-- csv_handler.py         # CSV/TSV
|   |   |-- excel_handler.py       # XLSX/XLS
|   |   |-- ods_handler.py         # ODS
|   |   |-- docx_handler.py        # DOCX
|   |   |-- odt_handler.py         # ODT
|   |   |-- pdf_handler.py         # PDF (lecture seule)
|   |   |-- txt_handler.py         # TXT/MD
|   |   |-- json_handler.py        # JSON + streaming ijson
|   |
|   |-- interface/                 # Frontend DSFR (repris de Pseudonymus)
|       |-- index.html
|       |-- app.js
|       |-- style.css
|       |-- dsfr/
|
|-- cli.py                         # CLI batch (argparse, streaming, barre de progression)
|-- data/                          # Dictionnaires de référence (copie de Pseudonymus)
|-- confidentiel/                  # Correspondances CSV (gitignoré)
|-- tests/
|   |-- test_regex.py
|   |-- test_ner.py
|   |-- test_detecteur.py
|   |-- test_pipeline.py
|   |-- test_formats.py
|   |-- test_api.py
|   |-- fixtures/
|-- requirements.txt
|-- CLAUDE.md
|-- README.md
```

---

## Flux de données

```
Fichier d'entrée (JSON 112 Mo, CSV, XLSX, DOCX, PDF...)
        |
        v
[formats/] load_file() --> Liste de dicts normalisés
        |
        v
[moteur/pipeline.py] process_record() par enregistrement
   |
   |-- 1. Champs structurés (mapping.champs_sensibles)
   |      Remplacement direct par jetons typés [EMAIL_1], [TEL_1]
   |
   |-- 2. Texte libre (mapping.texte_libre)
   |      |
   |      |-- 2a. Lookup noms déclarant (prénom/nom des champs structurés)
   |      |
   |      |-- 2b. Whitelist/Blacklist protection
   |      |
   |      |-- 2c. Détection regex (40+ patterns, 10 phases)
   |      |        Produit spans [(start, end, type, value, "regex")]
   |      |
   |      |-- 2d. Détection NER GLiNER (si mode hybrid ou ner)
   |      |        Produit spans [(start, end, type, value, score, "ner")]
   |      |
   |      |-- 2e. Fusion et déduplication des spans
   |      |        - Union des deux ensembles
   |      |        - Chevauchements : regex finance > NER > regex heuristique
   |      |        - Déduplication par chevauchement (start1 < end2 and start2 < end1)
   |      |
   |      |-- 2f. Substitution (TokenTable) + scoring RGPD
   |      |
   |      |-- 2g. Propagation (mode fort) + nettoyage
   |
   |-- 3. Re-sérialisation (unwrap JSON stringifié si configuré)
        |
        v
[formats/] save_file() --> Fichier de sortie (même format, anonymisé)
        +
[confidentiel/] correspondances.csv
```

### Diagramme de séquence — mode `hybrid`

```
Client (CLI/API/Web)
    │
    │  texte libre d'un enregistrement
    ▼
detecteur.detect_hybrid(texte)
    │
    ├──────────────────────┐
    │                      │
    ▼                      ▼
regex.detect(texte)    ner.extract(texte)
    │                      │
    │ spans_regex          │ spans_ner
    │ (score=1.0)          │ (score=0.0-1.0)
    │                      │
    └──────┬───────────────┘
           │
           ▼
    fusion(spans_regex, spans_ner)
           │
           │  1. Mapping types NER → Pseudonymus
           │  2. Validation post-NER (dictionnaires)
           │  3. Filtrage whitelist
           │  4. Résolution chevauchements
           │     (regex finance > NER > regex heuristique)
           │  5. Déduplication
           │
           ▼
    spans_unifiés (triés par position)
           │
           ▼
    substitution(texte, spans_unifiés)
           │
           │  1. Remplacement en ordre inverse (positions stables)
           │  2. TokenTable (déduplication jetons)
           │  3. Scoring RGPD
           │
           ▼
    texte anonymisé + mapping + score
```

### Espace disque

| Ressource | Taille estimée |
|-----------|---------------|
| Modèle `gliner2-base-v1` | ~800 Mo (dans `~/.cache/huggingface/`) |
| Modèle `gliner2-large-v1` | ~1,3 Go (optionnel) |
| Dictionnaires (`data/`) | ~14 Mo (noms.json 11,6 Mo + prenoms.json 1,9 Mo + 7 petits fichiers) |
| Code source | < 5 Mo |
| **Total** | ~820 Mo (base) / ~2,1 Go (avec large) |

Le premier lancement télécharge le modèle depuis HuggingFace. Les lancements suivants utilisent le cache local.

### Stratégie de logs

```python
import logging

# Un logger par module
logger = logging.getLogger(__name__)

# Configuration dans main.py
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
```

Niveaux utilisés :
- `INFO` : chargement modèle, début/fin traitement, nombre d'entités détectées
- `WARNING` : fallback NER → regex, entité rejetée par validation dictionnaire
- `ERROR` : échec chargement modèle, fichier illisible
- `DEBUG` : spans détaillés, scores, temps par étape (activable via `--verbose` en CLI)

---

## Composants clés

### Singleton NER (`moteur/ner_gliner.py`)

```python
from gliner2 import GLiNER2

class NERService:
    _instance = None

    def __init__(self):
        self._model = None           # GLiNER2 base (205M) ou large (340M)
        self._device = None          # auto : MPS > CPU
        self._available = False      # True si gliner2 est installé

    def extract(self, text, labels, threshold=0.4) -> list[Entity]:
        """Extraction NER avec chunking pour textes > 10k chars."""

    def extract_batch(self, texts: list[str], labels, threshold=0.4) -> list[list[Entity]]:
        """Extraction NER par lot (buffer de 32 textes pour le streaming)."""

    def extract_with_schema(self, text, schema) -> dict:
        """Extraction multi-tâches via l'API schéma GLiNER2 (NER + classification + relations)."""

    def anonymize(self, text, pii_types, mode="mask") -> tuple[str, dict, int]:
        """Anonymisation complète : extraction + substitution."""

    @property
    def is_available(self) -> bool:
        """True si gliner2 est installé et le device est compatible."""
```

- Lazy loading : modèle chargé au premier appel
- Device auto : `torch.backends.mps.is_available()` pour Apple Silicon
- Optimisations GLiNER2 : `quantize=True` (réduction de précision, type exact à valider en phase 0) + `compile=True` (torch.compile, fusion de kernels) pour accélérer l'inférence
- Chunking : découpage en blocs de 10k chars aux limites de phrases
- Déduplication : même texte + même type + distance < 50 chars = doublon
- Batching : `extract_batch()` pour traiter N textes en un seul appel GPU/MPS
- API schéma : `create_schema()` pour combiner NER + classification + relations en une seule passe
- Fallback gracieux : si `import gliner2` échoue, `is_available = False` et le pipeline bascule automatiquement en mode `regex`
- Mémoire estimée : ~1-2 Go RAM (1 modèle 205M + dictionnaires). Aucun problème sur Mac Studio M1 Ultra 64 Go

### Détecteur hybride (`moteur/detecteur.py`)

Le composant central qui orchestre regex et NER :

```python
@dataclass
class Span:
    start: int
    end: int
    entity_type: str    # "PERSON", "EMAIL", "IBAN", etc.
    value: str
    score: float        # 1.0 pour regex, 0-1 pour NER
    source: str         # "regex" | "ner"

def detect_hybrid(text, mode, fort, whitelist, blacklist) -> list[Span]:
    """Retourne les spans triés par position, sans chevauchements."""
```

Résolution des chevauchements (`start1 < end2 and start2 < end1`) :
- Regex finance (IBAN, NIR, CB, SIRET) toujours prioritaire (validateurs mathématiques)
- NER prioritaire sur regex heuristique (noms ambigus)
- En cas de chevauchement, garder le span le plus long

### Table de mapping des types

Les types Pseudonymus et GLiNER n'utilisent pas les mêmes noms. Table de correspondance pour la fusion :

```python
TYPE_MAP_NER_TO_PSEUDO = {
    "person":        "personne",
    "email":         "email_txt",
    "phone":         "tel_txt",
    "address":       "adresse_txt",
    "iban":          "iban_txt",
    "ssn":           "nir_txt",
    "credit_card":   "cb_txt",
    "ip_address":    "ip_txt",
    "date_of_birth": "date_naiss_txt",
    "organization":  "orga_txt",
    "location":      "ville_txt",
    "date":          "date_txt",
    "money":         "montant_txt",
}
```

### Modèles GLiNER2

| Modèle | Paramètres | Usage |
|--------|------------|-------|
| `fastino/gliner2-base-v1` | 205M | Extraction généraliste zero-shot (personnes, orga, lieux, PII) |
| `fastino/gliner2-large-v1` | 340M | Performance accrue (si la mémoire le permet) |

Un seul modèle chargé (base par défaut). GLiNER2 est zero-shot : on passe les labels PII en paramètre, pas besoin d'un modèle PII séparé.

```python
extractor = GLiNER2.from_pretrained("fastino/gliner2-base-v1", quantize=True)

# Extraction PII — les labels sont passés à la volée
entities = extractor.extract_entities(text, [
    "personne", "email", "téléphone", "adresse",
    "IBAN", "numéro de sécurité sociale", "carte bancaire",
    "adresse IP", "date de naissance", "organisation"
])
```

---

## Routes API

### Routes communes avec Synthesia-API (compatibles)

```
POST /ner/extract         -- Extraction d'entités depuis texte brut
POST /ner/anonymize       -- Anonymisation PII (mask, redact, hash)
POST /ner/deanonymize     -- Restauration avec mapping
GET  /ner/entity-types    -- Types d'entités supportés
```

### Routes exclusives GLiNER2 (absentes chez Loïc)

```
POST /ner/compare         -- Comparer regex vs NER vs hybrid sur le même texte (diagnostic)
POST /ner/validate        -- Vérifier qu'un texte anonymisé ne contient plus de PII détectable
POST /ner/classify        -- [EXPÉRIMENTAL] Classifier la sensibilité RGPD (dépend de create_schema())
POST /ner/relations       -- [EXPÉRIMENTAL] Extraire les relations entre entités (dépend de create_schema())
POST /ner/schema          -- [EXPÉRIMENTAL] Extraction multi-tâches en une passe (dépend de create_schema())
```

Les 3 routes expérimentales dépendent de `GLiNER2.create_schema()` — feature documentée sur PyPI mais jamais testée localement. Elles seront implémentées en phase 6 après validation de `create_schema()` en phase 0. Si la qualité est insuffisante sur du français, elles seront retirées ou remplacées par une approche alternative.

### Routes fichier (héritées de Pseudonymus, absentes chez Loïc)

```
POST /fichier/anonymise   -- Anonymisation fichier complet (multi-format, sortie dans le même format que l'entrée)
POST /fichier/upload      -- Upload fichier (multipart)
GET  /fichier/download    -- Télécharger le résultat
GET  /fichier/progress    -- SSE progression (streaming gros fichiers)
POST /fichier/score       -- Scoring RGPD par enregistrement sans anonymiser
POST /fichier/dry-run     -- Aperçu sur N enregistrements avant traitement complet
POST /fichier/batch       -- Traitement d'un dossier entier en une requête
POST /fichier/analyze     -- Analyser la structure d'un fichier (types détectés, échantillon, scoring)
GET  /health/stats        -- Statistiques dictionnaires (nombre noms, prénoms, stopwords chargés)
```

### Routes mapping (héritées de Pseudonymus, absentes chez Loïc)

```
POST /mapping/generate    -- Auto-détection structure fichier + génération mapping
POST /mapping/validate    -- Validation d'un mapping existant
```

### Infra

```
GET  /health              -- État du service + modèles chargés + device + mémoire
```

Swagger auto sur `/docs`, bind `127.0.0.1` uniquement, pas d'auth.

### Détail des routes exclusives

#### `POST /ner/classify`

Classifie la sensibilité RGPD d'un texte sans extraire les entités individuelles. Utilise `GLiNER2.create_schema().classification()`.

```json
// Requête
{ "text": "Jean Dupont, né le 12/04/1985, IBAN FR76..." }

// Réponse
{ "sensibilite": "critique", "confidence": 0.94, "details": ["identité directe", "financier"] }
```

#### `POST /ner/relations`

Extrait les relations directionnelles entre entités détectées. Utilise `GLiNER2.create_schema().relations()`.

```json
// Requête
{ "text": "Alexandra de Sosh a proposé un tarif à Pierre Durand" }

// Réponse
{
  "relations": [
    { "source": "Alexandra", "relation": "employé_de", "target": "Sosh", "confidence": 0.87 },
    { "source": "Alexandra", "relation": "contacte", "target": "Pierre Durand", "confidence": 0.91 }
  ]
}
```

#### `POST /ner/schema`

Extraction multi-tâches en une seule passe via un schéma JSON configurable. Combine NER + classification + relations.

```json
// Requête
{
  "text": "Jean Dupont de la CNIL a contacté Marie Martin par email...",
  "schema": {
    "entities": { "personne": "nom complet", "organisation": "entreprise ou administration" },
    "classification": { "label": "sensibilite", "classes": ["haute", "moyenne", "basse"] },
    "relations": ["employé_de", "contacte"]
  }
}

// Réponse
{
  "entities": [
    { "text": "Jean Dupont", "label": "personne", "confidence": 0.98 },
    { "text": "CNIL", "label": "organisation", "confidence": 0.96 },
    { "text": "Marie Martin", "label": "personne", "confidence": 0.97 }
  ],
  "classification": { "sensibilite": "haute", "confidence": 0.92 },
  "relations": [
    { "source": "Jean Dupont", "relation": "employé_de", "target": "CNIL", "confidence": 0.89 },
    { "source": "Jean Dupont", "relation": "contacte", "target": "Marie Martin", "confidence": 0.85 }
  ]
}
```

#### `POST /ner/compare`

Diagnostic : compare les résultats des trois moteurs sur le même texte. Utile pour régler les seuils et comprendre les apports de chaque moteur.

```json
// Requête
{ "text": "Bonjour Alexandra, votre IBAN FR7630006000011234567890189..." }

// Réponse
{
  "regex_only": [
    { "text": "FR7630006000011234567890189", "type": "iban", "source": "regex", "score": 1.0 }
  ],
  "ner_only": [
    { "text": "Alexandra", "type": "person", "source": "ner", "score": 0.93 },
    { "text": "FR7630006000011234567890189", "type": "iban", "source": "ner", "score": 0.71 }
  ],
  "hybrid": [
    { "text": "Alexandra", "type": "personne", "source": "ner", "score": 0.93 },
    { "text": "FR7630006000011234567890189", "type": "iban", "source": "regex", "score": 1.0 }
  ],
  "diagnostic": {
    "regex_seul": 1,
    "ner_seul": 2,
    "hybrid": 2,
    "apport_ner": ["Alexandra (personne, non détecté par regex)"],
    "apport_regex": ["IBAN validé par mod-97 (regex plus fiable que NER sur ce type)"]
  }
}
```

#### `POST /ner/validate`

Contrôle qualité post-anonymisation : passe le texte anonymisé dans GLiNER2 pour vérifier qu'il ne reste aucun PII détectable. Retourne les fuites éventuelles.

```json
// Requête
{ "text": "[PERSONNE_1] a contacté [EMAIL_1] depuis le 06 12 34 56 78" }

// Réponse
{
  "clean": false,
  "fuites": [
    { "text": "06 12 34 56 78", "type": "phone", "confidence": 0.95, "message": "Numéro de téléphone non masqué" }
  ]
}
```

#### `POST /fichier/score`

Scoring RGPD par enregistrement sans pseudonymiser. Hérité de Pseudonymus (`--score-only`).

```json
// Requête
{ "path": "/chemin/vers/fichier.json", "mapping": { ... }, "limit": 100 }

// Réponse
{
  "total_enregistrements": 31891,
  "analyses": 100,
  "score_moyen": 42,
  "niveau_moyen": "MODÉRÉ",
  "distribution": { "NUL": 5, "FAIBLE": 23, "MODÉRÉ": 48, "ÉLEVÉ": 19, "CRITIQUE": 5 },
  "top_types": { "email": 95, "personne": 87, "telephone": 62, "iban": 12 }
}
```

#### `POST /fichier/dry-run`

Aperçu sur N enregistrements avant de lancer le traitement complet. Hérité de Pseudonymus (`--dry-run`).

```json
// Requête
{ "path": "/chemin/vers/fichier.json", "mapping": { ... }, "limit": 5, "mode": "hybrid" }

// Réponse
{
  "apercu": [
    {
      "id": 10786453,
      "avant": "Nom : jean martin\nEmail : jean.martin@example.com",
      "apres": "Nom : [PERSONNE_1]\nEmail : [EMAIL_1]",
      "entites": 4,
      "score": 28
    }
  ],
  "estimation_temps_total": "~8 min pour 31891 enregistrements"
}
```

#### `POST /fichier/batch`

Traitement d'un dossier entier en une seule requête. Hérité de Pseudonymus (`--input-dir`).

```json
// Requête
{ "input_dir": "/chemin/vers/dossier/", "mapping": { ... }, "mode": "hybrid" }

// Réponse
{
  "fichiers_traites": 12,
  "total_enregistrements": 45230,
  "erreurs": 0,
  "resultats": [
    { "fichier": "export-2024.json", "enregistrements": 31891, "entites": 89234, "duree_s": 480 },
    { "fichier": "export-2023.csv", "enregistrements": 13339, "entites": 37102, "duree_s": 195 }
  ]
}
```

---

## CLI

```bash
# Pseudonymiser un fichier
python cli.py fichier.json --mapping mapping.json --pseudo --mode hybrid

# Modes de détection
python cli.py fichier.json --mapping mapping.json --pseudo --mode regex    # Pseudonymus seul
python cli.py fichier.json --mapping mapping.json --pseudo --mode ner      # GLiNER seul
python cli.py fichier.json --mapping mapping.json --pseudo --mode hybrid   # Les deux combinés

# Options
python cli.py fichier.json --mapping mapping.json --pseudo --fort --tech
python cli.py fichier.json --mapping mapping.json --dry-run
python cli.py fichier.json --mapping mapping.json --score-only
python cli.py fichier.json --mapping-generate

# Streaming gros fichiers
python cli.py gros-fichier.json --mapping mapping.json --pseudo --chunk-size 5000

# Batch dossier
python cli.py --input-dir dossier/ --mapping mapping.json --pseudo
```

---

## Dépendances

```
# NER
gliner2>=1.2.5
torch

# API
fastapi>=0.115
uvicorn[standard]>=0.34
pydantic-settings

# Formats (optionnels)
openpyxl        # XLSX
odfpy           # ODS/ODT
python-docx     # DOCX
pdfplumber      # PDF
ijson           # JSON streaming
spacy           # NLP optionnel (--nlp, complément à GLiNER2)

# CLI
tqdm

# Tests
pytest
pytest-asyncio
httpx
```

GLiNER2 v1.2.5 inclut les optimisations de Loïc (vectorisation preprocessing, batching post-encodeur, fp16, torch.compile).

---

## Phases d'implémentation

### Vue d'ensemble

| Phase | Contenu | Effort estimé | Point de décision |
|-------|---------|---------------|-------------------|
| 0 | Validation GLiNER2 sur MPS | 1h | Bloquant — si tests 1-2 échouent, tout change |
| 1 | Extraction Pseudonymus en spans | 3-4 sessions | Refactoring de paradigme (in-place → spans) sur 450+ lignes + portage de 208 tests. C'est la phase la plus lourde |
| 2 | Moteur NER + détecteur hybride | 1-2 sessions | Le hybrid détecte-t-il plus que chaque moteur seul ? |
| 3 | Pipeline complet + formats | 1-2 sessions | Le fichier SignalConso 112 Mo passe-t-il bout en bout ? |
| 4 | API FastAPI (MVP) | 1 session | Les 4 routes MVP fonctionnent-elles ? |
| 5 | CLI | 0.5 session | - |
| 6 | Interface DSFR + routes catalogue | 1-2 sessions | Quelles routes prioriser après le MVP ? |

Une "session" = une conversation Claude Code. Le MVP (phases 0 à 5) représente **8-11 sessions** (la phase 1 représente à elle seule ~40 % de l'effort total).

### Phase 0 — Validation GLiNER2 sur MPS (pré-requis bloquant)

7 tests à passer avant d'avancer :

0. Installer `gliner2` + `torch` dans le venv
1. **Chargement modèle** : `GLiNER2.from_pretrained("fastino/gliner2-base-v1")` charge sans erreur sur MPS
2. **Extraction de base** : `extract_entities("Jean Dupont, email jean@test.fr", ["person", "email"])` retourne 2 entités
3. **Labels français vs anglais** : comparer `extract_entities(texte, ["person"])` vs `extract_entities(texte, ["personne"])` — même résultat ? Si les labels français sont moins performants, utiliser les labels anglais + table de traduction pour l'affichage
4. **Batching** : tester si GLiNER2 supporte le traitement par lot (plusieurs textes en un appel). Si non, documenter et boucler en Python
5. **Optimisations** : tester `quantize=True`, `compile=True` — mesurer le speedup
6. **`create_schema()`** : tester `.entities({...}).classification(...)` — si ça fonctionne, les 3 routes expérimentales sont validées. Si non, les décaler ou les retirer
7. **Benchmark** : mesurer le temps par texte (1 000 car.) sur MPS. Calculer l'estimation pour 31 891 enregistrements

**Si les tests 1-2 échouent, tout le plan change.** Ne pas avancer sans validation.
Les tests 3-6 sont informatifs : ils orientent les décisions mais ne bloquent pas.

### Phase 1 — Fondations (extraction Pseudonymus)

**Attention — refactoring profond, pas du copier-coller.**

`pseudonymise_texte()` fait 450 lignes avec des variables partagées entre phases, des closures imbriquées (`_replace`, `_propag_apres`), et des effets de bord sur `TokenTable`. Le découper en un module `regex.py` qui **produit des spans** (au lieu de modifier le texte in-place) est un changement de paradigme :

- **Avant** (Pseudonymus) : chaque phase modifie le texte → positions décalées → impossible de fusionner avec NER
- **Après** (notre architecture) : chaque phase détecte et retourne des spans `(start, end, type, value)` sur le texte original → fusion possible

Concrètement, chaque regex passe de :
```python
# AVANT : modification in-place
result = RX_EMAIL.sub(lambda m: tokens.get_typed_token(...), result)

# APRÈS : production de spans
for m in RX_EMAIL.finditer(text):
    spans.append(Span(m.start(), m.end(), "email", m.group(), 1.0, "regex"))
```

Ce refactoring touche les 10 phases. Prévoir que cette étape prenne plus de temps que les autres. Porter les 208 tests de Pseudonymus pour valider la non-régression à chaque module extrait.

4. Créer la structure de fichiers et `requirements.txt`
5. Copier les dictionnaires (`data/`) depuis Pseudonymus
6. Extraire `moteur/regex.py` : convertir les 40+ regex de substitution in-place en détecteurs de spans + validateurs (Luhn/NIR/SIRET)
7. Extraire `moteur/dictionnaires.py` (chargement des sets noms/prénoms/stopwords)
8. Extraire `moteur/substitution.py` : adapter `TokenTable` pour travailler avec des spans au lieu de modifier le texte directement
9. Extraire `moteur/scoring.py` (classes `RiskScorer` + `Stats`)
10. Extraire `moteur/navigation.py` (notation pointée, unwrap, arrays)
11. Tests unitaires pour chaque module extrait — porter les tests de Pseudonymus comme baseline de non-régression

### Phase 2 — Moteur NER

12. Implémenter `moteur/ner_gliner.py` : singleton GLiNER2, lazy-loading, device MPS, fallback CPU, quantize+compile
13. Implémenter `extract_batch()` pour le batching (buffer 32 textes)
14. Implémenter le chunking (découpage > 10k chars) et la déduplication
15. Implémenter la table de mapping des types (NER → Pseudonymus)
16. Implémenter `moteur/detecteur.py` : orchestration regex → NER → fusion spans
17. Gestion d'erreur NER : si GLiNER échoue sur un texte, fallback sur regex seul (pas de crash)
18. Tests d'intégration : détection hybride sur des textes PII variés

### Phase 3 — Pipeline complet

19. Implémenter `moteur/pipeline.py` : reprendre `process_record()` avec détecteur hybride
20. Extraire `formats/` depuis `formats.py` de Pseudonymus (un module par format)
21. Implémenter `moteur/depseudonymise.py`
22. Intégrer le batching NER dans le streaming `ijson` (buffer de 32 enregistrements)
23. Tests bout-en-bout sur échantillon du fichier SignalConso 112 Mo

### Phase 4 — API FastAPI

24. Créer `app/main.py` avec lifespan (pré-chargement modèles)
25. Implémenter les routes NER (compatibles API Synthesia)
26. Implémenter les routes fichier (upload + traitement local + SSE progression)
27. Implémenter les routes mapping
28. Tests API avec `httpx.AsyncClient`

### Phase 5 — CLI

29. Implémenter `cli.py` : argparse, modes, options, streaming, batch
30. Tests CLI

### Phase 6 — Interface web DSFR

31. Copier l'interface de Pseudonymus et adapter pour FastAPI
32. Ajouter sélecteur de mode (regex/ner/hybrid)
33. Ajouter indicateur de chargement des modèles NER

---

## Fichiers source à réutiliser

| Composant | Source Pseudonymus | Lignes |
|-----------|-------------------|--------|
| 40+ regex + validateurs | `pseudonymise.py` | 62-160 |
| Dictionnaires (chargement) | `pseudonymise.py` | 33-55 |
| TokenTable | `pseudonymise.py` | 289-349 |
| RiskScorer + Stats | `pseudonymise.py` | 351-424 |
| Notation pointée, unwrap | `pseudonymise.py` | 896-953 |
| process_record() | `pseudonymise.py` | 965-1093 |
| pseudonymise_texte() (10 phases) | `pseudonymise.py` | 427-893 |
| Formats (load/save) | `formats.py` | 1-395 |
| Dépseudonymisation | `depseudonymise.py` | 1-67 |
| Contexte négatif (n°, page, €, kg, %) | `pseudonymise.py` | RX_CTX_NB_AVANT, RX_CTX_NB_APRES |
| Analyse fichier (types détectés, échantillon) | `serveur.py` | _handle_analyze |
| Stats dictionnaires | `serveur.py` | _handle_stats |
| NLP spaCy (load_nlp, detecter_personnes_nlp) | `pseudonymise.py` | optionnel |
| Dictionnaires JSON | `data/*.json` | 9 fichiers |

| Composant | Source Synthesia-API | Fichier |
|-----------|---------------------|---------|
| Singleton NER + lazy loading | `ner_service.py` | Pattern complet |
| Routes NER (Pydantic models) | `ner_routes.py` | 7 routes |
| Modèles de données NER | `ner_models.py` | Entity, Request, Response |
| Chunking + déduplication | `ner_service.py` | _split_text, _deduplicate_entities |
| Nettoyage markdown | `ner_service.py` | _clean_markdown |

---

## Vérification

Pour valider que l'implémentation fonctionne :

1. **Phase 0 — chargement** : `GLiNER2.from_pretrained("fastino/gliner2-base-v1")` charge sur MPS
2. **Phase 0 — extraction** : `extract_entities("Jean Dupont, email jean@test.fr", ["person","email"])` retourne 2 entités
3. **Phase 0 — labels français** : comparer `["person"]` vs `["personne"]` — documenter le résultat
4. **Phase 0 — batching** : tester le traitement par lot (plusieurs textes en un appel)
5. **Phase 0 — create_schema()** : tester `.entities({...}).classification(...)` pour valider les routes expérimentales
6. **Phase 0 — benchmark** : temps par texte sur MPS, estimation temps total sur 31 891 enregistrements
7. **Tests unitaires** : `pytest tests/` — tous verts
8. **Test hybride** : comparer détection regex seul vs NER seul vs hybride sur le même texte
9. **Test fichier SignalConso** : anonymiser 10 enregistrements du fichier 112 Mo, vérifier le JSON de sortie + correspondances CSV
10. **Test API** : `uvicorn app.main:app` puis `curl -X POST http://127.0.0.1:8090/ner/anonymize`
11. **Test CLI** : `python cli.py confidentiel/CourrierSRC*.json --mapping mapping.json --pseudo --mode hybrid`
12. **Test mémoire** : vérifier la consommation RAM (cible raisonnable, pas de contrainte sur 64 Go)

---

## Sécurité des données PII

Un outil d'anonymisation manipule des données personnelles sensibles. La sécurité n'est pas un bonus — c'est un prérequis.

### Cycle de vie des PII en mémoire

```
Fichier chargé → texte en RAM → spans détectés (contiennent les PII) → substitution → texte anonymisé
                                                                          ↓
                                                                   mapping (PII en clair)
                                                                          ↓
                                                                   correspondances.csv
```

Les PII existent en clair à 3 endroits : le texte original en RAM, les spans détectés, et le mapping/CSV. Chaque point doit être sécurisé.

### Mesures de protection

| Mesure | Implémentation |
|--------|----------------|
| **Nettoyage mémoire** | Après traitement de chaque enregistrement, les variables contenant le texte original et les spans sont explicitement supprimées (`del`) et le garbage collector est invoqué (`gc.collect()`) |
| **Fichiers temporaires** | Les uploads multipart sont stockés dans un répertoire temporaire dédié (`/tmp/anonymisation-{session}/`) avec suppression automatique après traitement (via `finally` ou `atexit`) |
| **Correspondances CSV** | Écrites dans `confidentiel/` (chmod 700, gitignoré). Politique de rétention : l'utilisateur est responsable de la suppression. L'API ne persiste rien entre les requêtes |
| **Logs sécurisés** | Les niveaux INFO et WARNING ne loguent JAMAIS de PII. Seuls les métadonnées sont loguées (nombre d'entités, types, scores). Le niveau DEBUG est désactivé par défaut et affiche un avertissement au démarrage s'il est activé : `ATTENTION : le mode DEBUG peut afficher des données personnelles dans les logs` |
| **Swagger en production** | Le Swagger (`/docs`) est activé par défaut pour le développement. En production, désactivable via `DISABLE_DOCS=true` pour éviter l'exposition des schémas d'API |
| **Isolation des requêtes** | Chaque requête API crée ses propres instances `TokenTable`, `Stats`, `RiskScorer`. Pas d'état partagé entre requêtes. Le singleton `NERService` ne stocke aucune donnée utilisateur |
| **Bind localhost** | Le serveur écoute sur `127.0.0.1` uniquement. Pas d'accès réseau par défaut |

### Logging sécurisé — règles

```python
# BON — métadonnées uniquement
logger.info(f"Traitement terminé : {len(entities)} entités détectées en {time_ms}ms")
logger.warning(f"Entité rejetée par validation dictionnaire (type={entity.label}, score={entity.score:.2f})")

# INTERDIT — PII en clair
logger.debug(f"Span détecté : {span.value}")  # ← FUITE PII
logger.info(f"Email trouvé : {entity.text}")   # ← FUITE PII
```

### Mode air-gap (hors ligne complet)

Pour les environnements sans accès internet :

1. Télécharger le modèle une fois sur une machine connectée : `python -c "from gliner2 import GLiNER2; GLiNER2.from_pretrained('fastino/gliner2-base-v1')"`
2. Le modèle est caché dans `~/.cache/huggingface/hub/models--fastino--gliner2-base-v1/`
3. Copier ce dossier sur la machine air-gap
4. Lancer avec `HF_HUB_OFFLINE=1` pour empêcher toute tentative de connexion

---

## Stratégie de test

### Baseline élargie (golden results)

Les 3 enregistrements golden actuels (SignalConso) sont un point de départ, pas un jeu de test complet. La baseline doit être élargie avant la livraison MVP :

| Catégorie | Nombre minimum | Exemples |
|-----------|---------------|----------|
| Enregistrements SignalConso représentatifs | 50 | Sélection aléatoire stratifiée dans les 31 891 enregistrements |
| Textes avec noms composés | 10 | "Jean-Pierre de La Fontaine", "Ben Ali Mohamed" |
| Textes avec noms étrangers | 10 | Noms arabes, asiatiques, slaves, africains |
| Textes avec faux positifs connus | 10 | "Rose" (prénom ou fleur), "Martin" (nom ou animal), "Orange" (entreprise ou fruit) |
| Textes avec PII partiellement masquées | 5 | Emails obfusqués, téléphones avec espaces inhabituels |
| Textes vides ou sans PII | 5 | Doit retourner 0 entité, score RGPD = 0 |
| Formats non-JSON (CSV, DOCX, PDF) | 5 | Un fichier par format, avec PII connues |
| Textes en français familier/SMS | 5 | "Jai la preuve", "mdr jpeux pas", typique des réclamations SignalConso |
| **Total** | **100** | Jeu de test annoté manuellement avec entités attendues |

### Métriques de qualité

| Métrique | Seuil d'acceptation | Calcul |
|----------|---------------------|--------|
| Recall (taux de détection) | >= 95 % | Entités détectées / entités annotées |
| Precision (taux de vrais positifs) | >= 90 % | Vrais positifs / (vrais positifs + faux positifs) |
| F1-score | >= 92 % | 2 * (precision * recall) / (precision + recall) |
| Restauration | 100 % | Texte restauré == texte original (mode mask) |

Ces métriques sont mesurées par mode (regex / ner / hybrid) pour quantifier l'apport de chaque moteur.

### Test de performance

| Scénario | Seuil | Mesure |
|----------|-------|--------|
| 1 texte court (1 000 car.) | < 3s | Chronométrage API |
| 100 enregistrements SignalConso | < 1 min | Chronométrage CLI |
| 31 891 enregistrements (fichier complet) | < 30 min | Chronométrage CLI avec `--chunk-size` |
| Mémoire RAM max pendant traitement | < 4 Go | Mesure `psutil` |

---

## Risques identifiés

| Risque | Impact | Mitigation |
|--------|--------|-----------|
| GLiNER ne tourne pas sur MPS | Bloquant | Tester en phase 0. Fallback CPU (plus lent mais fonctionnel) |
| Mémoire insuffisante (modèle + fichier) | Basse | Mac Studio M1 Ultra 64 Go — aucune contrainte. Peut charger base + large simultanément |
| Batching NER lent sur CPU | Moyenne | Réduire le buffer (32 → 8), ou désactiver NER pour les gros fichiers |
| Conflits types regex/NER | Basse | Table de mapping explicite, tests de non-régression |
| Spans désalignés regex/NER | Haute | Voir recommandation 1 ci-dessous |
| Concurrence FastAPI + GLiNER synchrone | Moyenne | `run_in_executor` pour les appels NER (voir recommandation 6) |
| Labels français moins performants que anglais | Moyenne | Tester en phase 0. Si confirmé, utiliser labels anglais + table de traduction pour l'affichage |
| Routes expérimentales (classify/relations/schema) non fonctionnelles | Moyenne | Tester `create_schema()` en phase 0. Si échec, retirer les 3 routes sans impact sur le reste |
| API batch GLiNER2 inexistante | Moyenne | Tester en phase 0. Si pas de batch natif, boucle Python (fonctionnel mais plus lent) |

---

## Recommandations prioritaires (analyse connus-inconnus)

### 1. Regex et NER doivent tourner sur le texte original

**Problème** : Pseudonymus modifie le texte phase par phase (phase 4 remplace un email, phase 5 voit `[EMAIL_1]` au lieu du texte original). Si NER tourne sur le texte déjà modifié par les regex, les positions (spans) sont décalées et la détection NER est dégradée.

**Solution** : les deux moteurs tournent sur le **texte brut original**, indépendamment. Chacun produit une liste de spans. La fusion intervient après, puis une seule passe de substitution.

```
texte original
    ├── regex.detect(texte) → spans_regex
    ├── ner.extract(texte)  → spans_ner
    └── fusion(spans_regex, spans_ner) → spans_unifiés
            └── substitution(texte, spans_unifiés) → texte anonymisé
```

C'est un **changement architectural** par rapport à Pseudonymus. À implémenter dès la phase 2 (`detecteur.py`).

### 2. Ajouter `source` et `score` dans les correspondances CSV

**Format actuel** (Pseudonymus) :
```
type;jeton;valeur_originale
```

**Format enrichi** :
```
type;jeton;valeur_originale;source;score
personne;[PERSONNE_1];Jean Dupont;ner;0.99
email;[EMAIL_1];jean@test.fr;regex;1.0
```

Permet de tracer d'où vient chaque détection et de mesurer la contribution de chaque moteur.

### 3. Estimer le temps total avant de lancer sur 31 891 enregistrements

Après la phase 0, calculer :

```
temps_unitaire × (31891 / taille_batch) = temps_total_estimé
```

Exemple : 500 ms par texte, batch de 32 → `500 × (31891/32) ≈ 8 min`. Si > 30 min, proposer un mode `regex` pour les gros fichiers avec NER en option.

### 4. Pinner la version du modèle

Ne pas dépendre de HuggingFace à chaque lancement. Télécharger le modèle une fois, stocker dans `~/.cache/huggingface/`, et épingler la version dans `config.py` :

```python
MODEL = "fastino/gliner2-base-v1"          # modèle unique du projet
MODEL_REVISION = "main"                     # ou un hash de commit spécifique
```

Note : on utilise `fastino/gliner2-base-v1` (GLiNER2, 205M) comme modèle unique. Les références à `knowledgator/gliner-pii-large-v1.0` (GLiNER v1) dans la documentation de référence concernent l'API de Loïc, pas notre projet.

Alternative : `--local-model /path/to/model` en CLI pour un fonctionnement 100 % hors ligne après le premier téléchargement.

### 5. Tester la whitelist avec GLiNER

**Deux approches possibles** :

- **Whitelist avant NER** : remplacer les mots whitelistés par des placeholders (`__WL0__`) avant d'appeler GLiNER. Risque : le tokenizer NER voit un texte altéré, la détection peut se dégrader
- **Whitelist après NER** : laisser GLiNER voir le texte complet, puis filtrer les spans qui tombent sur un mot whitelisté. Plus sûr pour la qualité NER

Tester les deux en phase 2 sur un texte contenant un mot whitelisté (ex: "ORANGE" qui est une entreprise, pas un PII).

**Recommandation** : whitelist **après** NER (filtrage des spans) pour ne pas altérer l'entrée du modèle.

### 6. Gérer la concurrence FastAPI + GLiNER synchrone

GLiNER est synchrone (bloque le thread pendant l'inférence). FastAPI est async. Avec 2 requêtes simultanées, le deuxième appel attend.

**Solution** : exécuter les appels NER dans un `ThreadPoolExecutor` :

```python
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=1)  # 1 seul worker NER (GPU/MPS non thread-safe)

@app.post("/ner/extract")
async def extract(request: NERExtractRequest):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, ner_service.extract, request.text, request.labels)
    return result
```

Un seul worker car le GPU/MPS ne supporte pas le parallélisme.

### 7. Exploiter les dictionnaires comme validation post-NER

Les dictionnaires (884k noms, 169k prénoms) peuvent servir de **filtre de confiance** :

- GLiNER détecte "garage" comme `person` (score 0.46) → pas dans PATRONYMES ni PRENOMS → rejeté
- GLiNER détecte "Martin" comme `person` (score 0.85) → présent dans PATRONYMES → confirmé
- GLiNER détecte "Alexandra" comme `person` (score 0.93) → présent dans PRENOMS → confirmé

```python
def validate_ner_entity(entity, dictionnaires):
    if entity.label == "person" and entity.score < 0.7:
        name = entity.text.upper()
        if name not in dictionnaires.patronymes and name not in dictionnaires.prenoms:
            return False  # faux positif probable
    return True
```

Seuil suggéré : rejeter les `person` avec score < 0.7 ET absents des dictionnaires.

### 8. Utiliser le client API (option A) comme test de non-régression

Le `documentation/client_synthesia.py` a produit des résultats connus sur 3 enregistrements. Sauvegarder ces résultats comme **golden file** et comparer avec la sortie du moteur local :

```python
# test_non_regression.py
def test_vs_api_loic():
    """Le moteur local doit détecter au moins les mêmes entités que l'API de Loïc."""
    golden = load_json("tests/fixtures/resultats-api-loic.json")
    local = moteur.extract(golden["texte_original"])
    for entity in golden["entities"]:
        assert any(e.text == entity["text"] for e in local), f"Entité manquante : {entity}"
```

---

## Protocole de co-construction

### Rythme de travail

Chaque phase suit le même cycle :

```
1. Aligner    — je présente l'approche, tu valides ou corriges
2. Coder      — j'implémente, tu observes (ou tu codes, je revois)
3. Vérifier   — on lance les tests ensemble, on constate les résultats
4. Commiter   — un commit par étape majeure (protection anti-perte)
5. Décider    — si un résultat est surprenant, on s'arrête et on décide ensemble
```

### Ce dont j'ai besoin de toi

| Moment | Ce que j'attends |
|--------|-----------------|
| Phase 0 (validation GLiNER2) | Que tu me dises si les temps de réponse et la qualité de détection te semblent acceptables sur tes données réelles |
| Phase 1 (refactoring regex) | Que tu valides que le comportement est identique à Pseudonymus — tu connais les cas limites mieux que moi |
| Phase 2 (fusion hybrid) | Que tu arbitres quand regex et NER sont en désaccord — quel résultat est le bon ? |
| Toute phase | Que tu me montres un nouveau fichier d'entrée si le format diffère de SignalConso — je ne peux pas deviner les structures |

### Ce que tu peux attendre de moi

- Un commit à chaque étape majeure (pas de perte en cas d'interruption)
- Un test avant chaque avancée (pas de code non vérifié qui s'empile)
- Une alerte immédiate si un résultat de phase 0 remet en cause le plan
- Pas de sur-ingénierie : MVP d'abord, catalogue complet ensuite

### Points de décision

Les moments où on doit s'arrêter et décider ensemble :

1. **Fin phase 0** : les résultats GLiNER2 sont-ils satisfaisants ? Labels français ou anglais ? `create_schema()` fonctionne-t-il ?
2. **Fin phase 1** : le refactoring regex en spans produit-il les mêmes résultats que Pseudonymus ?
3. **Fin phase 2** : la fusion hybrid détecte-t-elle strictement plus que chaque moteur seul ?
4. **Fin phase 3** : le fichier SignalConso 112 Mo est-il traité correctement de bout en bout ?
5. **Après MVP** : quelles routes du catalogue complet prioriser ?

---

Date de création : 2026-03-29
Dernière mise à jour : 2026-03-29 (v3 — résumé exécutif, KPI, sécurité PII, baseline 100 enreg., estimations révisées, incohérences corrigées)
