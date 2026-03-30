# Spécifications fonctionnelles

**Projet** : anonymisation-synthesia
**Version** : 0.1.0
**Date** : 2026-03-29
**Statut** : livré

---

## 1. Objet du document

Ce document décrit les fonctionnalités de l'application du point de vue de l'utilisateur : ce qu'elle fait, pour qui, et comment.

---

## 2. Contexte et besoin

### Problème

Les agents publics, DPO et équipes data manipulent des fichiers contenant des données personnelles (RGPD). Avant tout partage, archivage ou analyse, ces données doivent être anonymisées. Les outils existants sont soit :
- **Déterministes** (regex) : rapides mais aveugles au contexte ("Rose" = prénom ou fleur ?)
- **Contextuels** (NER/LLM) : intelligents mais dépendants du réseau et lents

### Solution

Une application locale combinant les deux approches pour une couverture maximale, sans aucune dépendance réseau en fonctionnement.

### Utilisateurs cibles

| Profil | Besoin principal |
|--------|-----------------|
| Agent public | Anonymiser un fichier avant transmission |
| DPO | Évaluer le risque RGPD d'un jeu de données |
| Data analyst | Traiter des exports de base de données en masse |
| Développeur | Intégrer l'anonymisation dans un pipeline via l'API |

---

## 3. Périmètre fonctionnel

### 3.1 Anonymisation de texte

**Description** : l'utilisateur colle du texte libre et obtient une version anonymisée.

**Entrées** :
- Texte brut (1 à 500 000 caractères)
- Mode de détection : regex, NER ou hybrid
- Mode de sortie : mask (`[PERSONNE_1]`), anon (`***`), redact (`████`), hash
- Options : mode fort, détection technique, whitelist, blacklist

**Sorties** :
- Texte anonymisé
- Liste des correspondances (jeton → valeur originale)
- Score RGPD (total + niveau + détail par catégorie)
- Statistiques (nombre de remplacements par type)

**Règles métier** :
- Un même email apparaissant plusieurs fois reçoit le même jeton (`[EMAIL_1]`)
- La whitelist est insensible à la casse
- Le contexte négatif empêche l'anonymisation des nombres non personnels (n° de page, montants en euros)
- En mode mask, la restauration est possible via les correspondances. En mode anon/redact/hash, elle est irréversible

### 3.2 Anonymisation de fichier

**Description** : l'utilisateur fournit un fichier complet et obtient un fichier anonymisé dans le même format.

**Formats supportés** :

| Format | Entrée | Sortie | Mapping requis |
|--------|--------|--------|---------------|
| JSON | Oui | Oui | Oui (fichiers structurés) |
| CSV / TSV | Oui | Oui | Oui |
| XLSX / XLS | Oui | Oui | Oui |
| ODS | Oui | Oui | Oui |
| DOCX | Oui | Oui | Non |
| ODT | Oui | Oui | Non |
| PDF | Oui | TXT | Non |
| TXT / MD | Oui | Oui | Non |

**Entrées** :
- Fichier (upload multipart ou chemin local)
- Mapping JSON (optionnel — obligatoire pour les fichiers structurés)
- Options de traitement (mode, détection, limite, fort, tech)

**Sorties** :
- Fichier anonymisé (même format que l'entrée, sauf PDF → TXT)
- Correspondances CSV (`confidentiel/correspondances.csv`)
- Statistiques de traitement

**Règles métier** :
- Les documents non structurés (DOCX, PDF, TXT) sont traités sans mapping : tout le texte est scanné
- Les fichiers structurés (JSON, CSV, XLSX) nécessitent un mapping pour cibler les champs sensibles
- Un mapping peut être généré automatiquement par l'outil
- Le mapping supporte la notation pointée (`Report.Firstname`), les arrays (`Details[].Value`) et le dépaquetage de JSON stringifié (`unwrap`)

### 3.3 Génération de mapping

**Description** : l'outil inspecte un fichier et propose un mapping squelette.

**Entrées** : chemin du fichier

**Sorties** : mapping JSON avec les champs détectés (heuristique sur les noms de colonnes)

**Règles métier** :
- Les colonnes dont le nom contient "nom", "name", "email", "tel", "phone" sont classées automatiquement
- Les champs texte longs (> 50 caractères) sont proposés comme texte libre

### 3.4 Scoring RGPD

**Description** : évaluer le niveau de risque d'un texte ou d'un fichier sans anonymiser.

**Scoring** :

| Catégorie | Points par détection | Exemples |
|-----------|---------------------|----------|
| Finance | 5 | IBAN, carte bancaire, NIR, CVV |
| Direct | 3 | Nom, email, téléphone, date de naissance |
| Tech | 2 | Adresse IP, MAC, JWT, clé API |
| Indirect | 1 | Code postal, adresse, ville, organisation, SIRET |

| Niveau | Score | Interprétation |
|--------|-------|----------------|
| NUL | 0 | Aucune donnée personnelle |
| FAIBLE | 1-9 | Données indirectes |
| MODÉRÉ | 10-49 | Données personnelles directes |
| ÉLEVÉ | 50-99 | Données sensibles |
| CRITIQUE | 100+ | Données hautement sensibles |

### 3.5 Extraction d'entités

**Description** : détecter les entités PII dans un texte sans les anonymiser.

**Sorties** : liste d'entités avec texte, type, position, score de confiance, source (regex ou NER)

### 3.6 Diagnostic

**Description** : comparer les 3 modes de détection sur le même texte et vérifier la qualité d'une anonymisation.

**Fonctionnalités** :
- Comparaison regex vs NER vs hybrid (nombre d'entités, apport de chaque moteur)
- Vérification post-anonymisation : repasser GLiNER2 sur un texte anonymisé pour détecter les fuites

### 3.7 Restauration

**Description** : inverser la pseudonymisation en remplaçant les jetons par les valeurs originales.

**Entrées** : texte pseudonymisé + correspondances (en mémoire ou CSV)

**Sorties** : texte original restauré

**Règles métier** : les jetons sont remplacés du plus long au plus court (`[PERSONNE_10]` avant `[PERSONNE_1]`) pour éviter les collisions

### 3.8 Analyse de fichier

**Description** : explorer la structure d'un fichier avant de le traiter (format, nombre d'enregistrements, types de champs).

---

## 4. Modes de détection

### 4.1 Regex (déterministe)

40+ patterns compilés couvrant :
- Finance : IBAN (mod-97), carte bancaire (Luhn), NIR (checksum), SIRET (Luhn), CVV, n° fiscal
- Communication : 5 variantes email + 3 variantes téléphone
- Adresses : voie avec numéro, voie sans numéro, codes postaux
- Organisations : nom + suffixe légal (SA, SAS, SARL, etc.)
- Personnes : salutations, titres (M./Mme), Prénom NOM MAJUSCULE
- URLs

### 4.2 NER (contextuel)

Modèle GLiNER2 (205M paramètres) en zero-shot :
- 10 labels PII en français : personne, email, téléphone, adresse, IBAN, n° sécu, carte bancaire, adresse IP, date de naissance, organisation
- Comprend le contexte : "Alexandra m'a proposé un tarif" → Alexandra = personne

### 4.3 Hybrid (combiné)

Les deux moteurs tournent sur le texte original indépendamment. Les résultats sont fusionnés avec des règles de priorité :
1. Regex finance > tout (validateurs mathématiques)
2. NER > regex heuristique (noms ambigus)
3. En cas de chevauchement : garder le span le plus long

Validation post-NER : les entités "personne" avec score < 0.7 et absentes des dictionnaires (884k noms, 169k prénoms) sont rejetées.

---

## 5. Interfaces

### 5.1 Interface web (8 pages)

| Page | Fonction |
|------|----------|
| Pseudonymisation | Coller du texte et pseudonymiser |
| Import fichier | Upload ou chemin local + mapping |
| Analyse | Structure fichier + extraction entités |
| Scoring RGPD | Score risque texte ou fichier |
| Correspondances | Table jetons/valeurs + export CSV |
| Restauration | Inverser la pseudonymisation |
| Diagnostic | Comparer moteurs + vérifier anonymisation |
| Documentation | Guide pédagogique, glossaire, FAQ |

### 5.2 API REST (19 routes)

Swagger auto sur `/docs`. Bind localhost uniquement. Pas d'authentification.

### 5.3 CLI

Commandes : `--pseudo`, `--anon`, `--dry-run`, `--score-only`, `--mapping-generate`, `--input-dir`, `--fort`, `--tech`, `--mode`

---

## 6. Sécurité

- Traitement 100 % local (après téléchargement initial du modèle)
- Correspondances CSV en chmod 600 dans `confidentiel/` (gitignoré)
- Aucune donnée personnelle dans les logs
- Nettoyage mémoire après chaque traitement
- Mode air-gap supporté (`HF_HUB_OFFLINE=1`)

---

## 7. Contraintes

- Python 3.10+
- ~3 Go d'espace disque (modèle + dépendances)
- 4 Go RAM minimum, 8 Go recommandé
- Premier appel NER : 5-30s (chargement modèle), ensuite ~0.2s par texte
