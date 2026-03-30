# Exemples de fichiers de test

Exemples prêts à copier-coller pour tester l'outil rapidement.

---

## Texte simple (page Pseudonymisation)

Collez ce texte dans le champ "Texte source" et cliquez sur "Pseudonymiser" :

```
Bonjour, je suis Pierre Durand, habitant au 12 rue Victor Hugo, 92130 Issy-les-Moulineaux.
Mon email est pierre.durand@example.com et mon téléphone est 06 95 22 20 38.
J'ai contacté Sosh le 8 juin par téléphone. Alexandra m'a proposé un tarif pour le mobile
à 10,95 par mois. Mon numéro de client est 12345678.
```

**Résultat attendu** : Pierre Durand, l'email, le téléphone et Alexandra sont masqués. Sosh reste visible (organisation, pas une personne).

---

## Fichier JSON simple

Créez un fichier `test.json` :

```json
[
  {"nom": "Dupont", "prenom": "Marie", "email": "marie.dupont@example.com", "commentaire": "La cliente est satisfaite du service"},
  {"nom": "Martin", "prenom": "Pierre", "email": "p.martin@example.com", "commentaire": "Pierre a signalé un problème de facturation"},
  {"nom": "Lambert", "prenom": "Sophie", "email": "sophie@example.com", "commentaire": "Appel du 15 mars, Sophie demande un remboursement"}
]
```

Mapping (`mapping-test.json`) :

```json
{
  "champs_sensibles": {
    "nom": {"type": "nom", "jeton": "NOM"},
    "prenom": {"type": "prenom", "jeton": "PRENOM"},
    "email": {"type": "email", "jeton": "EMAIL"}
  },
  "texte_libre": ["commentaire"],
  "lookup_noms": {"prenom": "prenom", "nom": "nom"}
}
```

**CLI** :
```bash
.venv/bin/python3 cli.py test.json --mapping mapping-test.json --pseudo --mode hybrid
```

---

## Fichier CSV

Créez un fichier `contacts.csv` :

```csv
nom,prenom,email,telephone,commentaire
Dupont,Marie,marie@example.com,06 12 34 56 78,Appel le 15 mars
Martin,Pierre,pierre@example.com,01 23 45 67 89,Réclamation en cours
```

Mapping (`mapping-csv.json`) :

```json
{
  "champs_sensibles": {
    "nom": {"type": "nom", "jeton": "NOM"},
    "prenom": {"type": "prenom", "jeton": "PRENOM"},
    "email": {"type": "email", "jeton": "EMAIL"},
    "telephone": {"type": "tel", "jeton": "TEL"}
  },
  "texte_libre": ["commentaire"]
}
```

---

## Texte pour le scoring RGPD

Collez dans la page "Scoring RGPD" pour voir les différents niveaux :

**Score faible** (données indirectes) :
```
Le dossier concerne la ville de Paris, référence 2024-1234.
```

**Score modéré** (données directes) :
```
Marie Dupont, email marie@example.com, habitant au 12 rue de la Paix, 75002 Paris.
```

**Score critique** (données financières) :
```
Jean Martin, né le 12/04/1985, IBAN FR76 3000 6000 0112 3456 7890 189,
numéro de sécurité sociale 1 85 04 75 123 456 78, carte 4532 0151 1283 0366.
Email : jean@example.com, téléphone : 06 12 34 56 78.
```

---

## Texte pour le diagnostic (comparaison moteurs)

Collez dans la page "Diagnostic" pour voir la différence entre regex, NER et hybrid :

```
Bonjour Alexandra, je vous écris concernant le dossier de Pierre Durand.
Rose Martin a contacté notre service le 8 juin pour signaler un problème
avec sa facture Orange. Son email est rose.martin@example.com.
```

**Ce que vous verrez** :
- **Regex** : détecte l'email et potentiellement le téléphone
- **NER** : détecte Alexandra, Pierre Durand, Rose Martin (noms dans le texte libre)
- **Hybrid** : combine les deux — couverture maximale

"Rose" est un cas intéressant : c'est à la fois un prénom et un nom de fleur. GLiNER2 comprend par le contexte que c'est un prénom ici.
