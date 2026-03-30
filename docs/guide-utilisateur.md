# Guide utilisateur

## Lancer l'application

```bash
cd anonymisation-synthesia
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8091
```

Ouvrir http://127.0.0.1:8091 dans le navigateur.

---

## Parcours 1 — Anonymiser du texte (30 secondes)

1. Ouvrir l'onglet **Pseudonymisation**
2. Coller du texte contenant des données personnelles dans le champ de gauche
3. Choisir le mode de détection (hybrid par défaut)
4. Cliquer sur **Pseudonymiser**
5. Le texte anonymisé apparaît à droite avec le score RGPD

Les correspondances (jeton → valeur originale) sont sauvegardées en mémoire. Aller dans l'onglet **Correspondances** pour les consulter ou les exporter en CSV.

---

## Parcours 2 — Anonymiser un fichier complet

### Document non structuré (DOCX, PDF, TXT)

1. Ouvrir l'onglet **Import fichier**
2. Choisir le fichier (upload ou chemin local)
3. **Pas besoin de mapping** — tout le texte est scanné automatiquement
4. Cliquer sur **Traiter le fichier**
5. Télécharger le résultat

### Fichier structuré (JSON, CSV, XLSX)

1. Ouvrir l'onglet **Import fichier**
2. Choisir le fichier
3. Cliquer sur **Générer le mapping automatiquement** — l'outil détecte les colonnes
4. Vérifier et ajuster le mapping si nécessaire
5. Cliquer sur **Traiter le fichier**
6. Télécharger le fichier anonymisé + les correspondances CSV

### Fichier avec JSON imbriqué (type SignalConso)

Pour les fichiers dont un champ contient du JSON stringifié (ex: `RCLMFicheReportJsonSC`), le mapping doit inclure la section `structure.unwrap` :

```json
{
  "structure": {
    "unwrap": {
      "field": "RCLMFicheReportJsonSC"
    }
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
  "whitelist": ["ORANGE", "SFR", "FREE"]
}
```

---

## Parcours 3 — Restaurer un texte pseudonymisé

1. Ouvrir l'onglet **Restauration**
2. Coller le texte pseudonymisé (avec les jetons `[PERSONNE_1]`, `[EMAIL_1]`, etc.)
3. Cliquer sur **Restaurer**
4. Le texte original apparaît à droite

Les correspondances utilisées sont celles de la dernière pseudonymisation. Si vous avez un fichier CSV de correspondances, importez-le d'abord.

---

## Parcours 4 — Évaluer le risque RGPD sans anonymiser

1. Ouvrir l'onglet **Scoring RGPD**
2. Coller du texte ou renseigner un chemin de fichier
3. Cliquer sur **Évaluer le risque** ou **Scorer le fichier**
4. Le score s'affiche avec le détail par catégorie (direct, finance, technique, indirect)

| Niveau | Score | Signification |
|--------|-------|---------------|
| NUL | 0 | Aucune donnée personnelle détectée |
| FAIBLE | 1-9 | Quelques données indirectes |
| MODÉRÉ | 10-49 | Données personnelles directes |
| ÉLEVÉ | 50-99 | Données sensibles (finance, santé) |
| CRITIQUE | 100+ | Données hautement sensibles |

---

## Parcours 5 — Comparer les moteurs de détection

1. Ouvrir l'onglet **Diagnostic**
2. Coller du texte dans "Comparer les moteurs"
3. Cliquer sur **Comparer**
4. Voir les résultats : combien d'entités détectées par regex seul, NER seul, et hybrid
5. La section "Apport NER" montre ce que GLiNER2 détecte et que les regex ratent

---

## Parcours 6 — Vérifier la qualité de l'anonymisation

1. Ouvrir l'onglet **Diagnostic**
2. Coller un texte déjà anonymisé dans "Vérifier un texte anonymisé"
3. Cliquer sur **Vérifier**
4. Si des données personnelles restent visibles, elles sont listées comme "fuites"

---

## Options de détection

### Modes

| Mode | Quand l'utiliser |
|------|-----------------|
| **Hybrid** (défaut) | Usage général — combine regex et NER |
| **Regex seul** | Fichiers volumineux (> 10 000 enregistrements) — très rapide |
| **NER seul** | Texte libre avec noms ambigus ("Rose" prénom ou fleur ?) |

### Options complémentaires

| Option | Ce qu'elle fait |
|--------|----------------|
| **Mode fort** | Prénoms isolés, salutations ("Bonjour Marie"), dates de naissance, plaques d'immatriculation |
| **Détection technique** | Adresses IPv4/IPv6, MAC, tokens JWT, clés API |
| **Whitelist** | Mots à ne jamais anonymiser (noms d'entreprises : ORANGE, SFR) |
| **Blacklist** | Mots à toujours anonymiser (noms que les moteurs pourraient rater) |

---

## Ligne de commande (CLI)

```bash
# Pseudonymiser un document
.venv/bin/python3 cli.py document.docx --pseudo --mode hybrid

# Pseudonymiser un fichier structuré
.venv/bin/python3 cli.py export.json --mapping mapping.json --pseudo --mode hybrid

# Options
--fort           # Mode fort
--tech           # Détection technique
--dry-run        # Aperçu sans écriture (100 enregistrements)
--score-only     # Scoring RGPD sans anonymiser
--mapping-generate  # Générer un mapping automatiquement
--input-dir DIR  # Traiter un dossier entier
--mode regex     # Mode regex seul (rapide)
```

---

## Sécurité

- **100 % local** : aucune donnée ne quitte votre machine (après le téléchargement initial du modèle)
- **Correspondances** : sauvegardées dans `confidentiel/` (chmod 700, gitignoré)
- **Logs** : aucune donnée personnelle dans les logs (métadonnées uniquement)
- **Nettoyage mémoire** : `gc.collect()` après chaque traitement
