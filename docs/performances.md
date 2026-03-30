# Performances

## Temps de traitement par mode

Mesures réalisées sur Mac Studio M1 Ultra 64 Go, texte de ~1 000 caractères.

| Mode | Temps par texte | Estimation 1 000 enreg. | Estimation 31 000 enreg. |
|------|----------------|------------------------|--------------------------|
| Regex seul | ~0.01s | ~10s | ~5 min |
| NER seul | ~0.2s | ~3 min | ~1.5h |
| Hybrid | ~0.5s | ~8 min | ~4.5h |

### Premier appel

Le premier appel NER est plus lent (chargement du modèle GLiNER2 en mémoire) :

| Étape | Temps |
|-------|-------|
| Chargement dictionnaires | ~0.1s |
| Chargement GLiNER2 (premier appel) | 5-30s |
| Appels suivants | ~0.2s par texte |

### Recommandation par volume

| Volume | Mode recommandé |
|--------|----------------|
| < 100 enregistrements | hybrid (qualité maximale) |
| 100-1 000 enregistrements | hybrid (quelques minutes) |
| 1 000-10 000 enregistrements | hybrid ou regex selon le besoin de qualité |
| > 10 000 enregistrements | regex (rapide) puis `/ner/validate` sur un échantillon |

---

## Consommation mémoire

| Composant | RAM |
|-----------|-----|
| Modèle GLiNER2 (205M paramètres) | ~800 Mo |
| Dictionnaires (884k noms + 169k prénoms) | ~50 Mo |
| Serveur FastAPI | ~30 Mo |
| **Total au repos** | **~900 Mo** |
| Pendant le traitement (fichier 112 Mo) | ~1.5 Go |

Avec 4 Go de RAM minimum, l'application fonctionne. 8 Go recommandés pour le confort.

---

## Espace disque

| Composant | Taille |
|-----------|--------|
| Code source + interface DSFR | ~5 Mo |
| Dictionnaires (`data/`) | ~14 Mo |
| Modèle GLiNER2 (cache HuggingFace) | ~800 Mo |
| Environnement virtuel (`.venv/`) | ~2 Go (torch + dépendances) |
| **Total** | **~3 Go** |
