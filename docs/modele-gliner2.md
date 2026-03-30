# Comment le modèle GLiNER2 fonctionne dans l'application

---

## Où il est stocké

```
~/.cache/huggingface/hub/models--fastino--gliner2-base-v1/
    └── snapshots/
        └── 283f4af5e5.../
            ├── config.json          # Configuration du modèle
            ├── model.safetensors    # Les poids du réseau de neurones (~800 Mo)
            ├── tokenizer_config.json
            └── ...
```

C'est dans le cache HuggingFace de votre répertoire utilisateur. Téléchargé une seule fois au premier lancement, réutilisé ensuite sans internet.

Un raccourci `modele-gliner2` existe à la racine du projet (symlink, non versionné) pour explorer le contenu.

---

## Comment il se déclenche

```
Vous lancez le serveur
    │
    ▼
uvicorn démarre FastAPI
    │
    ▼
lifespan() s'exécute au démarrage :
    ├── Charge les dictionnaires (884k noms) ........... ~0.1s
    └── Vérifie que gliner2 est installé ............... pas de chargement du modèle ici !
    │
    ▼
Le serveur est prêt. Le modèle N'EST PAS encore en mémoire.
    │
    ▼
Un utilisateur envoie du texte (API, CLI ou interface web)
    │
    ▼
detect_hybrid() est appelé
    ├── regex.detect_regex(texte) ...................... instantané (patterns compilés)
    └── ner.extract(texte) ............................ c'est ICI que ça se passe
        │
        ▼
    NERService.extract()
        │
        ├── Premier appel ? → _load_model()
        │       │
        │       ├── GLiNER2.from_pretrained("fastino/gliner2-base-v1")
        │       │       │
        │       │       ├── Cherche dans ~/.cache/huggingface/ (trouvé !)
        │       │       ├── Charge les poids en RAM (~800 Mo)
        │       │       └── Place le modèle sur le device (MPS ou CPU)
        │       │
        │       └── Temps : 5-30 secondes (UNE SEULE FOIS)
        │
        ├── Appels suivants ? → le modèle est déjà en RAM
        │       └── Temps : ~0.2 secondes
        │
        └── model.extract_entities(texte, labels)
                │
                ├── Le tokenizer découpe le texte en tokens
                ├── Le réseau de neurones analyse les tokens
                ├── Il retourne les entités détectées avec leur score de confiance
                └── Résultat : {"personne": [{"text": "Jean Dupont", "confidence": 0.99}]}
```

---

## Le pattern singleton

Le modèle est chargé une seule fois et réutilisé pour toutes les requêtes. C'est le pattern "singleton avec lazy loading" :

```python
class NERService:
    _instance = None      # Une seule instance pour toute l'application
    _model = None         # Le modèle chargé (ou None si pas encore appelé)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()    # Créé une seule fois
        return cls._instance         # Réutilisé ensuite

    def extract(self, text, labels):
        if self._model is None:
            self._load_model()       # Chargement LAZY (seulement quand on en a besoin)
        return self._model.extract_entities(text, labels)
```

Le modèle vit en RAM pendant toute la durée de vie du serveur. Pas de rechargement entre les requêtes.

---

## Chronologie

| Moment | Ce qui se passe | Durée |
|--------|----------------|-------|
| `install.sh` | Le modèle est téléchargé dans `~/.cache/huggingface/` | 1-5 min (une fois) |
| `uvicorn` démarre | Les dictionnaires sont chargés. Le modèle **n'est pas** chargé | 0.1s |
| Premier texte envoyé | Le modèle est chargé en RAM depuis le cache | 5-30s |
| Textes suivants | Le modèle est déjà en RAM, exécution directe | ~0.2s |
| Le serveur s'arrête | Le modèle est libéré de la RAM | instantané |

---

## Quand le modèle est-il utilisé ?

| Mode | Regex | GLiNER2 (NER) | Modèle chargé ? |
|------|-------|---------------|-----------------|
| `--mode regex` | Oui | Non | Non — le modèle ne se charge jamais |
| `--mode ner` | Non | Oui | Oui — chargé au premier appel |
| `--mode hybrid` | Oui | Oui | Oui — chargé au premier appel |

Le mode **regex** ne déclenche jamais le chargement du modèle. Il utilise uniquement les patterns compilés et les dictionnaires. C'est pourquoi il est beaucoup plus rapide (~0.01s par texte vs ~0.2s en hybrid).

---

## Détection automatique du device

Le modèle choisit automatiquement le meilleur device disponible :

```
MPS (Apple Silicon M1/M2/M4) → GPU Apple, le plus rapide
    ↓ si indisponible
CPU → fonctionne partout, plus lent
```

Pas besoin de configuration. La détection est automatique via `torch.backends.mps.is_available()`.

---

## Mode hors ligne (air-gap)

Pour les environnements sans accès internet :

```bash
# 1. Sur une machine connectée : télécharger le modèle
.venv/bin/python3 -c "from gliner2 import GLiNER2; GLiNER2.from_pretrained('fastino/gliner2-base-v1')"

# 2. Copier le cache sur la machine air-gap
cp -r ~/.cache/huggingface/hub/models--fastino--gliner2-base-v1 /chemin/destination/

# 3. Sur la machine air-gap : lancer sans réseau
HF_HUB_OFFLINE=1 .venv/bin/uvicorn app.main:app --port 8091
```

---

## Fallback sans modèle

Si GLiNER2 n'est pas installé (pas de `pip install gliner2`) ou si le modèle n'est pas téléchargé :

- Le serveur démarre normalement
- Le mode **hybrid** bascule automatiquement en mode **regex seul**
- Un message s'affiche : `GLiNER2 non disponible — mode regex uniquement`
- Aucune erreur, l'outil reste fonctionnel (sans la détection contextuelle)
