# Tâches — anonymisation-synthesia

## En cours

(rien — projet livré)

## Améliorations futures

- [ ] CLI : ajouter `--extract` (extraction sans anonymisation)
- [ ] CLI : ajouter `--compare` (comparaison regex vs NER vs hybrid)
- [ ] CLI : ajouter `--validate` (vérification post-anonymisation)
- [ ] CLI : ajouter `--analyze` (structure du fichier)
- [ ] Annoter 100 enregistrements golden (annotation manuelle)
- [ ] Mesurer precision/recall/F1 sur le jeu annoté
- [ ] Test de performance sur 31 891 enregistrements
- [ ] Pousser sur GitHub (dépôt public)

## Terminé

- [x] Phase 0 : GLiNER2 validé sur MPS (2026-03-29)
- [x] Phase 1 : modules moteur extraits (regex spans, NER, détecteur hybrid)
- [x] Phase 4 : API FastAPI — 19 routes, toutes testées
- [x] Phase 5 : CLI fonctionnelle (pseudo, anon, dry-run, score-only, batch)
- [x] Phase 6 : interface web DSFR — 8 pages
- [x] 71 tests pytest — regex, pipeline, API, golden, formats, détecteur
- [x] Catalogue complet P2-P4 (routes fichier, mapping, diagnostic)
- [x] Documentation publique : installation, guide utilisateur, CLI, API, mapping, sécurité, types d'entités, performances, exemples
- [x] Sécurité : nettoyage mémoire, logs sécurisés, air-gap validé
- [x] Préparation dépôt public : LICENSE GPL v3, données fictives, .gitignore
- [x] Footer DSFR conforme, fil d'Ariane, accents, page Documentation pédagogique
