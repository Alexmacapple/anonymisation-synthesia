# Types d'entités détectées

L'outil détecte plus de 20 types de données personnelles (PII), répartis en 4 catégories de risque RGPD.

---

## Catégories de risque

| Catégorie | Points RGPD | Description |
|-----------|-------------|-------------|
| **Finance** | 5 points par détection | Données financières et régaliennes |
| **Direct** | 3 points par détection | Identifiants directs d'une personne |
| **Tech** | 2 points par détection | Données techniques identifiantes |
| **Indirect** | 1 point par détection | Données indirectement identifiantes |

Le score RGPD total détermine le niveau de risque :

| Niveau | Score | Signification |
|--------|-------|---------------|
| NUL | 0 | Aucune donnée personnelle |
| FAIBLE | 1-9 | Quelques données indirectes |
| MODÉRÉ | 10-49 | Données personnelles directes |
| ÉLEVÉ | 50-99 | Données sensibles |
| CRITIQUE | 100+ | Données hautement sensibles |

---

## Détection standard (toujours active)

### Finance (5 points)

| Type | Jeton | Détection | Validateur | Exemples |
|------|-------|-----------|-----------|----------|
| IBAN | `[IBAN_1]` | Regex | mod-97 | `FR76 3000 6000 0112 3456 7890 189` |
| Carte bancaire | `[CB_1]` | Regex | Luhn | `4532 0151 1283 0366` |
| CVV | `[CVV_1]` | Regex | - | `cvv 123`, `cvc 4567` |
| NIR (n° sécu) | `[NIR_1]` | Regex | Checksum NIR | `1 85 01 75 123 456 78` |
| N° fiscal | `[ID_FISCAL_1]` | Regex | Contexte négatif | `0123456789012` |

### Direct (3 points)

| Type | Jeton | Détection | Exemples |
|------|-------|-----------|----------|
| Personne | `[PERSONNE_1]` | NER + dictionnaires | `Jean Dupont`, `Alexandra` (dans le texte libre) |
| Email | `[EMAIL_1]` | Regex (5 variantes) | `jean@test.fr`, `jean [at] test [dot] fr` |
| Téléphone | `[TEL_1]` | Regex (3 variantes) | `06 12 34 56 78`, `+33 6 12 34 56 78` |
| Date de naissance | `[DATE_NAISSANCE_1]` | Regex (mode fort) | `né le 12/04/1985` |

### Indirect (1 point)

| Type | Jeton | Détection | Exemples |
|------|-------|-----------|----------|
| SIRET/SIREN | `[SIRET_1]` | Regex | Luhn | `732 829 320 00074` |
| Code postal | `[CP_1]` | Regex + contexte négatif | `94110` (pas `page 42`) |
| Adresse postale | `[VOIE_1]` | Regex | `12 rue Victor Hugo` |
| Ville | `[VILLE_1]` | NER | `Paris`, `Issy-les-Moulineaux` |
| Organisation | `[ORGANISATION_1]` | NER + regex | `Sosh`, `Orange SA` |
| URL | `[URL_1]` | Regex | `https://www.example.com` |
| Date | `[DATE_1]` | NER | `8 juin`, `19/01/2024` |

---

## Détection mode fort (`--fort`)

Activée avec l'option "Mode fort" dans l'interface ou `--fort` en CLI.

| Type | Jeton | Description |
|------|-------|-------------|
| Prénom isolé | `[PERSONNE_X]` | "Marie" seul dans le texte (sans nom de famille) |
| Salutation | `[PERSONNE_X]` | "Bonjour Marie", "Cher Monsieur Dupont" |
| Titre + nom | `[PERSONNE_X]` | "M. Dupont", "Mme Lambert" |
| Prénom + NOM MAJ | `[PERSONNE_X]` | "Marie DUPONT" |
| Préfixes arabes | `[PERSONNE_X]` | "Ben Ali", "El Khouri", "Abdel Rahman" |
| Date de naissance | `[DATE_NAISSANCE_1]` | "née le 12/04/1985" |
| Coordonnées GPS | `[GPS_1]` | `48.8566, 2.3522` |
| Plaque d'immatriculation | `[PLAQUE_1]` | `AB-123-CD`, `1234 AA 75` |
| Ville composée | `[VILLE_1]` | `SAINT-DENIS-SUR-MER` (en majuscules) |
| Mots majuscules longs | Variable | Mots entièrement en majuscules (potentiels noms propres) |

---

## Détection technique (`--tech`)

Activée avec l'option "Détection technique" dans l'interface ou `--tech` en CLI.

| Type | Jeton | Exemples |
|------|-------|----------|
| IPv4 | `[IPV4_1]` | `192.168.1.1` |
| IPv6 | `[IPV6_1]` | `::1`, `fe80::1` |
| Adresse MAC | `[MAC_1]` | `AA:BB:CC:DD:EE:FF` |
| Token JWT | `[JWT_1]` | `eyJhbGciOiJIUzI1NiIs...` |
| Clé API | `[API_KEY_1]` | `sk_test_EXEMPLE...`, `pk_test_xyz789...` |

---

## Contexte négatif

L'outil ne pseudonymise **pas** les nombres dans un contexte non personnel :

| Contexte rejeté | Exemple | Raison |
|----------------|---------|--------|
| Numéro de page | `page 42` | Ce n'est pas un identifiant personnel |
| Article de loi | `article 3` | Référence juridique |
| Montant | `300 euros` | Montant financier, pas un identifiant |
| Quantité | `5 kg` | Mesure, pas un identifiant |
| Référence | `n° 12345` | Numéro de dossier, pas un code postal |

---

## GLiNER2 vs regex — qui détecte quoi

| Entité | Regex | GLiNER2 (NER) | Mode hybrid |
|--------|-------|---------------|-------------|
| Email standard | Oui | Oui | Oui |
| Email obfusqué (`jean [at] test.fr`) | Oui | Non | Oui |
| Téléphone français | Oui | Oui | Oui |
| IBAN (avec validation mod-97) | Oui | Oui (sans validation) | Regex prioritaire |
| Nom dans un champ structuré | Oui (dictionnaire) | Oui | Les deux |
| Nom dans le texte libre ("Alexandra m'a proposé...") | Non (sauf mode fort) | **Oui** | **Apport NER** |
| Nom ambigu ("Rose", "Martin") | Partiel | **Oui** (comprend le contexte) | **Apport NER** |
| Nom étranger rare | Non (hors dictionnaire) | **Oui** | **Apport NER** |
| Organisation ("Sosh") | Regex (avec suffixe SA/SAS) | **Oui** | **Apport NER** |
| Adresse complète | Regex (rue + numéro) | **Oui** (adresse complète) | **Apport NER** |

Le mode **hybrid** combine les forces des deux moteurs. Utilisez l'onglet **Diagnostic** pour comparer les résultats sur votre texte.

---

## Faux positifs connus

| Faux positif | Type détecté à tort | Mitigation |
|-------------|--------------------|----|
| "garage" | personne (NER, score < 0.5) | Rejeté par validation dictionnaire (score < 0.7 + absent du dictionnaire) |
| Code postal "94110" | carte bancaire (NER) | Regex le détecte correctement comme code postal (prioritaire) |
| "SIRET" (le mot) | ville (NER) | Le mode hybrid préfère le regex qui ne le matche pas |
| URL | adresse IP (NER) | Le regex la détecte correctement comme URL (prioritaire) |
| "conducteur" | personne (NER, score < 0.5) | Rejeté par validation dictionnaire |

**Règle** : les entités NER de type "personne" avec un score < 0.7 et absentes des dictionnaires (884k noms, 169k prénoms) sont automatiquement rejetées.

---

## Whitelist et blacklist

### Whitelist (ne jamais anonymiser)

Mots à protéger, typiquement les noms d'entreprises qui ressemblent à des noms propres :

```
ORANGE, SFR, FREE, BOUYGUES, SOSH, AMAZON, GOOGLE
```

La whitelist est **insensible à la casse** : `Orange`, `ORANGE` et `orange` sont tous protégés.

### Blacklist (toujours anonymiser)

Mots à forcer en pseudonymisation, même si les moteurs ne les détectent pas :

```
Dupont, NomSpecifique
```

La blacklist ajoute des détections supplémentaires de type "personne".

---

## Correspondances CSV

Format du fichier `confidentiel/correspondances.csv` :

```csv
type;jeton;valeur_originale
personne;[PERSONNE_1];Jean Dupont
email;[EMAIL_1];jean@test.fr
tel;[TEL_1];06 12 34 56 78
```

- Séparateur : **point-virgule** (`;`), pas virgule
- Encodage : **UTF-8**
- Permissions : **chmod 600** (lecture/écriture propriétaire uniquement)
- Le fichier est écrasé à chaque nouveau traitement
