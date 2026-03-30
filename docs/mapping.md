# Guide du mapping

Le mapping est un fichier JSON qui décrit la structure de votre fichier à anonymiser. Il indique quels champs contiennent des données personnelles et comment les traiter.

**Le mapping est nécessaire uniquement pour les fichiers structurés** (JSON, CSV, XLSX). Pour les documents non structurés (DOCX, PDF, TXT), tout le texte est scanné automatiquement sans mapping.

---

## Générer un mapping automatiquement

### Depuis l'interface web

1. Ouvrir l'onglet **Import fichier**
2. Renseigner le chemin du fichier
3. Cliquer sur **Générer le mapping automatiquement**
4. Vérifier et ajuster le mapping proposé

### Depuis la CLI

```bash
.venv/bin/python3 cli.py export.json --mapping-generate
```

### Depuis l'API

```bash
curl -X POST "http://127.0.0.1:8091/mapping/generate?path=/chemin/fichier.json"
```

---

## Structure du mapping

```json
{
  "description": "Description du fichier",
  "champs_sensibles": {
    "nom_du_champ": {
      "type": "type_de_donnee",
      "jeton": "PREFIXE"
    }
  },
  "texte_libre": ["champ1", "champ2"],
  "lookup_noms": {
    "prenom": "champ_prenom",
    "nom": "champ_nom"
  },
  "whitelist": ["MOT1", "MOT2"],
  "blacklist": []
}
```

---

## Champs sensibles

Les champs dont la valeur sera remplacée par un jeton.

| Clé | Description |
|-----|-------------|
| `type` | Type de donnée : `nom`, `prenom`, `email`, `tel`, `cp`, `id`, `uuid`, `genre`, `iban`, `nir`, `cb` |
| `jeton` | Préfixe du jeton : `NOM`, `PRENOM`, `EMAIL`, `TEL`, `CP`, etc. |

**Exemple :**

```json
{
  "champs_sensibles": {
    "nom_famille": {"type": "nom", "jeton": "NOM"},
    "prenom": {"type": "prenom", "jeton": "PRENOM"},
    "email": {"type": "email", "jeton": "EMAIL"},
    "telephone": {"type": "tel", "jeton": "TEL"}
  }
}
```

Résultat : `"Dupont"` → `[NOM_1]`, `"Marie"` → `[PRENOM_1]`, etc.

---

## Texte libre

Les champs contenant du texte à scanner par les moteurs de détection (regex + NER). Le texte n'est pas remplacé entièrement — seules les entités PII détectées sont masquées.

```json
{
  "texte_libre": ["commentaire", "description", "notes"]
}
```

---

## Notation pointée (JSON imbriqué)

Pour accéder à des champs dans un JSON imbriqué :

```json
{
  "champs_sensibles": {
    "client.nom": {"type": "nom", "jeton": "NOM"},
    "client.contact.email": {"type": "email", "jeton": "EMAIL"}
  }
}
```

Fonctionne avec des objets imbriqués :
```json
{"client": {"nom": "Dupont", "contact": {"email": "jean@test.fr"}}}
```

---

## Arrays (notation `[]`)

Pour scanner les éléments d'un tableau :

```json
{
  "texte_libre": ["Details[].Value"]
}
```

Scanne le champ `Value` de chaque élément du tableau `Details` :
```json
{"Details": [{"Label": "Question", "Value": "texte à scanner..."}]}
```

---

## Unwrap (JSON stringifié)

Pour les fichiers dont un champ contient du JSON sérialisé en string (comme SignalConso) :

```json
{
  "structure": {
    "unwrap": {
      "field": "RCLMFicheReportJsonSC"
    }
  },
  "champs_sensibles": {
    "Report.Firstname": {"type": "prenom", "jeton": "PRENOM"}
  }
}
```

L'outil dépaquète le JSON stringifié, applique les remplacements, puis le re-sérialise.

---

## Lookup noms

Indique les champs contenant le prénom et le nom du déclarant. Ces valeurs sont recherchées dans les champs de texte libre pour une détection supplémentaire.

```json
{
  "lookup_noms": {
    "prenom": "Report.Firstname",
    "nom": "Report.Lastname"
  }
}
```

---

## Whitelist et blacklist

| Paramètre | Rôle | Exemple |
|-----------|------|---------|
| `whitelist` | Mots à ne jamais anonymiser | Noms d'entreprises : `["ORANGE", "SFR", "FREE"]` |
| `blacklist` | Mots à toujours anonymiser | Noms spécifiques que les moteurs pourraient rater |

---

## Exemples complets

### JSON plat (CSV, XLSX)

```json
{
  "description": "Export clients",
  "champs_sensibles": {
    "nom": {"type": "nom", "jeton": "NOM"},
    "prenom": {"type": "prenom", "jeton": "PRENOM"},
    "email": {"type": "email", "jeton": "EMAIL"},
    "telephone": {"type": "tel", "jeton": "TEL"}
  },
  "texte_libre": ["commentaire"],
  "whitelist": ["ORANGE"],
  "blacklist": []
}
```

### JSON imbriqué avec unwrap (SignalConso)

```json
{
  "description": "Réclamations SignalConso",
  "structure": {
    "unwrap": {"field": "RCLMFicheReportJsonSC"}
  },
  "champs_sensibles": {
    "Report.Firstname": {"type": "prenom", "jeton": "PRENOM"},
    "Report.Lastname": {"type": "nom", "jeton": "NOM"},
    "Report.Email": {"type": "email", "jeton": "EMAIL"},
    "Report.ConsumerPhone": {"type": "tel", "jeton": "TEL"},
    "Report.PostalCode": {"type": "cp", "jeton": "CP"}
  },
  "texte_libre": [
    "Report.Question",
    "Report.Details[].Value"
  ],
  "lookup_noms": {
    "prenom": "Report.Firstname",
    "nom": "Report.Lastname"
  },
  "whitelist": ["ORANGE", "SFR", "FREE", "BOUYGUES"]
}
```

---

## Valider un mapping

### Depuis l'API

```bash
curl -X POST http://127.0.0.1:8091/mapping/validate \
  -H "Content-Type: application/json" \
  -d '{"champs_sensibles": {"nom": {"type": "nom", "jeton": "NOM"}}}'
```

L'API vérifie la structure et signale les erreurs ou avertissements.
