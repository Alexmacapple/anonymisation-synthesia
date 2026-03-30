# Référence API

Swagger interactif : http://127.0.0.1:8091/docs

---

## Anonymisation

### `POST /ner/anonymize`

Anonymise du texte brut.

```bash
curl -X POST http://127.0.0.1:8091/ner/anonymize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Jean Dupont, email jean@test.fr, tel 06 12 34 56 78",
    "mode": "mask",
    "detection_mode": "hybrid",
    "fort": false,
    "tech": false,
    "whitelist": ["ORANGE"],
    "blacklist": []
  }'
```

**Réponse :**

```json
{
  "texte_original": "Jean Dupont, email jean@test.fr, tel 06 12 34 56 78",
  "texte_pseudonymise": "[PERSONNE_1], email [EMAIL_1], tel [TEL_1]",
  "correspondances": [
    {"type": "personne", "jeton": "[PERSONNE_1]", "valeur": "Jean Dupont"},
    {"type": "email_txt", "jeton": "[EMAIL_1]", "valeur": "jean@test.fr"},
    {"type": "tel_txt", "jeton": "[TEL_1]", "valeur": "06 12 34 56 78"}
  ],
  "stats": {"total": 3, "par_type": {"personne": 1, "email_txt": 1, "tel_txt": 1}},
  "score": {"total": 9, "niveau": "FAIBLE", "details": {"direct": 3}}
}
```

**Paramètres :**

| Champ | Type | Défaut | Description |
|-------|------|--------|-------------|
| `text` | string | (obligatoire) | Texte à anonymiser |
| `mode` | string | `mask` | `mask`, `anon`, `redact`, `hash` |
| `detection_mode` | string | `hybrid` | `regex`, `ner`, `hybrid` |
| `fort` | bool | `false` | Mode fort (prénoms isolés, dates de naissance) |
| `tech` | bool | `false` | Détection technique (IPv4, MAC, JWT) |
| `whitelist` | list | `[]` | Mots à ne jamais anonymiser |
| `blacklist` | list | `[]` | Mots à toujours anonymiser |

---

### `POST /ner/extract`

Extraire les entités sans anonymiser.

```bash
curl -X POST http://127.0.0.1:8091/ner/extract \
  -H "Content-Type: application/json" \
  -d '{"text": "Jean Dupont travaille à la CNIL"}'
```

---

### `POST /ner/deanonymize`

Restaurer un texte anonymisé avec le mapping.

```bash
curl -X POST http://127.0.0.1:8091/ner/deanonymize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "[PERSONNE_1], email [EMAIL_1]",
    "mapping": {"[PERSONNE_1]": "Jean Dupont", "[EMAIL_1]": "jean@test.fr"}
  }'
```

---

### `POST /ner/compare`

Comparer les résultats regex vs NER vs hybrid sur le même texte.

```bash
curl -X POST http://127.0.0.1:8091/ner/compare \
  -H "Content-Type: application/json" \
  -d '{"text": "Alexandra de Sosh a proposé un tarif à Pierre Durand"}'
```

---

### `POST /ner/validate`

Vérifier qu'un texte anonymisé ne contient plus de PII.

```bash
curl -X POST http://127.0.0.1:8091/ner/validate \
  -H "Content-Type: application/json" \
  -d '{"text": "[PERSONNE_1] a contacté [EMAIL_1] depuis le 06 12 34 56 78"}'
```

---

## Fichiers

### `POST /fichier/anonymise`

Anonymiser un fichier complet (multi-format).

```bash
curl -X POST http://127.0.0.1:8091/fichier/anonymise \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/chemin/vers/fichier.json",
    "mapping_path": "/chemin/vers/mapping.json",
    "mode": "pseudo",
    "detection_mode": "hybrid",
    "limit": 100
  }'
```

### `POST /fichier/upload`

Téléverser un fichier (multipart, 400 Mo max).

```bash
curl -X POST http://127.0.0.1:8091/fichier/upload \
  -F "file=@export.json"
```

### `POST /fichier/score`

Scoring RGPD par enregistrement sans anonymiser.

### `POST /fichier/analyze`

Analyser la structure d'un fichier.

### `POST /fichier/batch`

Traiter un dossier entier.

---

## Mapping

### `POST /mapping/generate`

Générer un mapping automatiquement depuis la structure d'un fichier.

```bash
curl -X POST "http://127.0.0.1:8091/mapping/generate?path=/chemin/fichier.json"
```

### `POST /mapping/validate`

Valider un mapping JSON.

---

## Système

### `GET /health`

État du service.

### `GET /health/stats`

Statistiques des dictionnaires chargés.

### `GET /ner/entity-types`

Types d'entités supportés.
