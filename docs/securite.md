# Sécurité et conformité RGPD

Ce document décrit les mesures de sécurité de l'application pour les DPO, RSSI et responsables conformité.

---

## Principe fondamental

**Aucune donnée personnelle ne quitte votre machine.** Le traitement est 100 % local après le téléchargement initial du modèle GLiNER2.

---

## Cycle de vie des données personnelles

```
Fichier source (sur votre disque)
    ↓
Chargement en mémoire (RAM)
    ↓
Détection des PII (regex + GLiNER2, en mémoire)
    ↓
Substitution par jetons ([PERSONNE_1], [EMAIL_1])
    ↓
Écriture du fichier anonymisé + correspondances CSV
    ↓
Nettoyage mémoire (gc.collect)
```

### Où les données personnelles existent

| Emplacement | Contenu | Protection |
|-------------|---------|-----------|
| Fichier source | Données originales | Inchangé, à protéger par l'utilisateur |
| RAM (pendant le traitement) | Texte original + spans détectés | Nettoyé par `gc.collect()` après chaque enregistrement |
| `confidentiel/correspondances.csv` | Mapping jeton → valeur originale | chmod 600, gitignoré, jamais versionné |
| Fichier `_PSEUDO.json` | Données anonymisées | Plus de PII (si anonymisation correcte) |
| Logs du serveur | Métadonnées uniquement | Aucune donnée personnelle dans les logs |

---

## Mesures de protection

### Réseau

- Le serveur écoute sur `127.0.0.1` uniquement (localhost)
- Pas d'accès réseau en fonctionnement normal
- Pas d'authentification nécessaire (usage local mono-utilisateur)
- Le modèle GLiNER2 est téléchargé une seule fois, puis fonctionne hors ligne

### Fichiers

- `confidentiel/` : chmod 700, gitignoré
- Les correspondances CSV sont en chmod 600 (lisibles uniquement par le propriétaire)
- Les fichiers temporaires d'upload sont supprimés automatiquement à l'arrêt du serveur
- Les fichiers de sortie `_PSEUDO` ne contiennent plus de données personnelles (si le traitement est correct)

### Mémoire

- `gc.collect()` est appelé après chaque traitement de fichier
- Chaque requête API crée ses propres objets (pas d'état partagé entre requêtes)
- Le singleton NERService ne stocke aucune donnée utilisateur (uniquement le modèle)

### Logs

- Niveau INFO : nombre d'entités, types détectés, temps de traitement. **Jamais** de valeurs PII
- Niveau DEBUG (désactivé par défaut) : peut contenir des spans détaillés. Un avertissement s'affiche au démarrage si DEBUG est activé
- Aucun log ne contient d'email, nom, téléphone, IBAN, ou autre donnée personnelle

---

## Mode air-gap (hors ligne complet)

Pour les environnements sensibles sans accès internet :

1. Télécharger le modèle une fois sur une machine connectée
2. Copier le cache : `~/.cache/huggingface/hub/models--fastino--gliner2-base-v1/`
3. Sur la machine air-gap : `HF_HUB_OFFLINE=1 .venv/bin/uvicorn app.main:app --port 8091`

---

## Correspondances CSV

Le fichier `confidentiel/correspondances.csv` contient le lien entre les jetons et les valeurs originales :

```csv
type;jeton;valeur_originale
personne;[PERSONNE_1];Jean Dupont
email;[EMAIL_1];jean@test.fr
```

**Ce fichier est la clé de la réversibilité.** Il permet de restaurer les données originales. Il doit être :

- Stocké dans un emplacement sécurisé
- Supprimé quand il n'est plus nécessaire
- Jamais versionné dans git (gitignoré par défaut)
- Jamais transmis avec le fichier anonymisé (sauf si la restauration est prévue)

### Politique de rétention

L'application ne supprime pas automatiquement les correspondances. C'est à l'utilisateur de définir la durée de conservation selon sa politique RGPD.

---

## Swagger en production

Le Swagger (`/docs`) est activé par défaut pour le développement. Il expose les schémas de l'API mais ne contient aucune donnée personnelle. Pour le désactiver, modifier `app/main.py` :

```python
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
```

---

## Limitations connues

| Limitation | Impact | Mitigation |
|-----------|--------|-----------|
| PDF en lecture seule | Le fichier anonymisé sort en TXT, pas en PDF | Utiliser le TXT de sortie ou un outil tiers pour recréer le PDF |
| Pas de chiffrement au repos | Les correspondances CSV sont en clair | chmod 600 + politique de suppression |
| Mono-utilisateur | Pas d'isolation entre utilisateurs si plusieurs personnes accèdent au même serveur | Bind sur localhost, usage individuel |
| Faux négatifs possibles | Certaines PII peuvent ne pas être détectées (noms très rares, formats inhabituels) | Utiliser le mode fort + vérifier avec `/ner/validate` |
