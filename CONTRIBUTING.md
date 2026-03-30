# Contribuer

Merci de votre intérêt pour le projet. Voici comment contribuer.

---

## Signaler un problème

Ouvrez une issue sur GitHub en décrivant :
- Le comportement attendu
- Le comportement observé
- Les étapes pour reproduire
- Votre environnement (OS, Python, version)

---

## Proposer une modification

1. Forkez le dépôt
2. Créez une branche : `git checkout -b feature/ma-fonctionnalite`
3. Codez votre modification
4. Lancez les tests : `.venv/bin/python3 -m pytest tests/ -v`
5. Vérifiez qu'aucun test ne casse (71/71 verts)
6. Commitez en français, forme nominale : `git commit -m "Ajout de la fonctionnalité X"`
7. Poussez et ouvrez une pull request

---

## Conventions

- **Langue** : français (commits, docs, messages d'erreur, interface)
- **Code Python** : type hints, variables en anglais, docstrings en français
- **Commits** : forme nominale ("Ajout de...", "Correction de..."), pas de point final
- **Branches** : `feature/`, `fix/`, `docs/`
- **Tests** : tout changement de comportement doit être couvert par un test

---

## Structure des tests

```
tests/
├── test_regex.py       # Validateurs et détection par regex
├── test_pipeline.py    # Pipeline complet (texte + enregistrement)
├── test_api.py         # Routes FastAPI
├── test_golden.py      # Non-régression
├── test_formats.py     # Formats de fichiers
└── test_detecteur.py   # Détecteur hybride
```

Avant de soumettre : `.venv/bin/python3 -m pytest tests/ -v` doit afficher 0 échec.

---

## Sécurité

- Ne jamais commiter de données personnelles réelles
- Les fichiers de test utilisent des données fictives (Pierre Durand, Sophie Lambert, example.com)
- Le répertoire `confidentiel/` est gitignoré — ne pas le forcer
