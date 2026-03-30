# PRD-02 — Passage en production

**Projet** : anonymisation-synthesia
**Date** : 2026-03-29
**Statut** : à planifier
**Prérequis** : PRD-01 livré (prototype fonctionnel)

---

## Contexte

Le prototype est fonctionnel : 19 routes API, 8 pages UI, 71 tests, CLI complète. Il est prêt pour le partage avec les collègues et le dépôt public GitHub.

Ce PRD couvre les travaux nécessaires pour passer du prototype à un outil de production utilisable en conditions réelles dans un service public.

---

## Objectifs

| Objectif | Critère de succès |
|----------|------------------|
| Fiabilité | Supporte 5 utilisateurs simultanés sans dégradation |
| Sécurité | Authentification, rate limiting, chiffrement correspondances |
| Qualité | Taux de détection mesuré (precision/recall/F1) sur un jeu annoté |
| Déployabilité | Dockerfile fonctionnel, démarrage en une commande |
| Observabilité | Logs structurés, métriques, health check avancé |

---

## Phase 1 — Pilote (retours utilisateurs)

**Objectif** : faire tourner l'outil avec des collègues sur des vrais fichiers et collecter les retours.

**Durée estimée** : 2-4 semaines d'usage réel.

- [ ] Partager le dépôt avec 3-5 collègues
- [ ] Documenter les retours : faux positifs, formats manquants, temps de traitement
- [ ] Identifier les cas d'usage non couverts (types de fichiers, structures JSON spécifiques)
- [ ] Mesurer le temps réel de traitement sur les fichiers de chaque collègue
- [ ] Collecter les whitelist/blacklist métier (noms d'organismes à ne jamais anonymiser)

**Livrable** : document de retours avec liste des améliorations prioritaires.

---

## Phase 2 — Sécurité

- [ ] **Authentification API** : token Bearer simple (variable d'environnement `API_TOKEN`). Toutes les routes POST protégées
- [ ] **Rate limiting** : `slowapi`, 100 requêtes/minute par IP
- [ ] **Chiffrement correspondances CSV** : option `--encrypt` avec clé symétrique (Fernet). Le CSV est chiffré au repos, déchiffré à la demande pour restauration
- [ ] **HTTPS** : documentation pour reverse proxy nginx/caddy en front
- [ ] **En-têtes de sécurité** : CSP, X-Frame-Options, X-Content-Type-Options (middleware FastAPI)
- [ ] **Limitation taille upload** : vérification côté serveur (pas seulement côté client)
- [ ] **Audit des dépendances** : `pip audit` dans la CI

---

## Phase 3 — Concurrence et performance

- [ ] **`run_in_executor` pour GLiNER2** : les appels NER bloquent le thread async FastAPI. Exécuter dans un `ThreadPoolExecutor(max_workers=1)` pour ne pas bloquer les autres routes
- [ ] **Queue de traitement** : pour les gros fichiers, file d'attente avec position affichée (évite les timeouts)
- [ ] **Améliorer la regex IBAN** : le pattern actuel ne matche pas tous les formats (compensé par GLiNER2, mais la regex devrait être autonome)
- [ ] **Batching NER Python** : regrouper N textes avant d'appeler GLiNER2 (le batch natif n'existe pas, mais on peut réduire l'overhead en envoyant les textes par lot)
- [ ] **Test de charge** : mesurer le comportement avec 5 requêtes simultanées, identifier les goulots d'étranglement
- [ ] **Benchmark formel** : traiter les 31 891 enregistrements SignalConso de bout en bout, mesurer le temps en regex/NER/hybrid

---

## Phase 4 — Qualité de détection

- [ ] **Annoter 100 enregistrements golden** : sélection aléatoire stratifiée dans les fichiers réels, annotation manuelle des entités attendues
- [ ] **Mesurer precision/recall/F1** : par mode (regex, NER, hybrid) et par type d'entité
- [ ] **Ajuster les seuils** : seuil NER (0.4 actuellement), seuil de rejet dictionnaire (0.7), en fonction des résultats mesurés
- [ ] **Réduire les faux positifs connus** : "94110" → carte bancaire (NER), "conducteur" → personne (NER). Ajouter des règles de filtrage post-NER
- [ ] **Ajouter les CLI manquantes** : `--extract`, `--compare`, `--validate`, `--analyze` (les routes API existent, la CLI ne les expose pas)
- [ ] **Tester sur d'autres formats de fichiers** : CSV réels, XLSX avec cellules fusionnées, PDF scannés, DOCX avec tableaux

---

## Phase 5 — Conteneurisation et déploiement

- [ ] **Dockerfile** : image multi-stage (build + runtime), modèle GLiNER2 pré-téléchargé dans l'image
- [ ] **docker-compose.yml** : service unique, volume pour `confidentiel/`, port configurable
- [ ] **Script de démarrage** : `start.sh` qui détecte l'environnement (Docker ou local) et configure automatiquement
- [ ] **CI/CD** : GitHub Actions avec lint, tests, audit dépendances
- [ ] **Documentation de déploiement** : guide pour déployer sur un serveur interne (pas d'accès internet)

---

## Phase 6 — Observabilité

- [ ] **Logs structurés** : format JSON pour intégration ELK/Loki, avec `request_id` pour tracer une requête
- [ ] **Métriques** : `/metrics` endpoint (Prometheus) — nombre de requêtes, temps de traitement, entités détectées par type
- [ ] **Health check avancé** : `/health/ready` (modèle chargé ?) et `/health/live` (serveur up ?)
- [ ] **Dashboard** : page admin dans l'interface avec statistiques d'usage (nombre de fichiers traités, temps moyen, types les plus détectés)

---

## Phase 7 — Améliorations fonctionnelles (post-production)

- [ ] **Upload drag-and-drop** : dans la page Import fichier (le champ upload existe mais pas le drag-and-drop visuel)
- [ ] **Historique des traitements** : persistance des derniers fichiers traités (chemin, date, stats)
- [ ] **Export PDF anonymisé** : réécriture du PDF avec les données masquées (nécessite reportlab ou weasyprint)
- [ ] **Multi-langue** : interface en anglais (les labels NER fonctionnent en anglais aussi)
- [ ] **Mapping par défaut** : mapping pré-configuré pour les formats courants (SignalConso, exports CNIL, etc.)

---

## Estimation d'effort

| Phase | Effort | Priorité |
|-------|--------|----------|
| 1. Pilote | 0 (usage réel) | Immédiat |
| 2. Sécurité | 1-2 sessions | Haute |
| 3. Performance | 1-2 sessions | Haute |
| 4. Qualité détection | 2-3 sessions + travail humain | Haute |
| 5. Conteneurisation | 1 session | Moyenne |
| 6. Observabilité | 1 session | Moyenne |
| 7. Améliorations | À planifier selon les retours pilote | Basse |

**Chemin critique** : phases 1 → 2 → 3 → 4 (dans cet ordre). Les phases 5-7 sont parallélisables.

---

## Critères de mise en production

| Critère | Seuil |
|---------|-------|
| Authentification | Token API obligatoire sur toutes les routes POST |
| Rate limiting | Activé (100 req/min) |
| Tests | 71+ tests, 0 échec |
| Precision PII | >= 90 % sur le jeu annoté |
| Recall PII | >= 95 % sur le jeu annoté |
| Temps de traitement | < 2 min pour 1 000 enregistrements (hybrid) |
| Dockerfile | Fonctionnel, image < 4 Go |
| Documentation déploiement | Complète |
| Retours pilote | Au moins 3 collègues ont testé pendant 2+ semaines |

---

Date de création : 2026-03-29
