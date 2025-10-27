# TODO: Maximiser la Couverture des Tests

**Date:** 2025-10-20
**Objectif:** Atteindre 80%+ de couverture backend et 90%+ frontend
**Statut:** 🔴 EN COURS

---

## 🎯 PRIORITÉ 1 - URGENTE (Cette Semaine)

### Backend - Analyse et Métriques

- [ ] **Générer rapport de couverture complet et à jour**
  ```bash
  USE_MOCK_HARDWARE=true python -m pytest tests/ --cov=app/src --cov-report=html --cov-report=term --cov-report=json
  ```
  - [ ] Analyser le rapport HTML généré
  - [ ] Identifier les fichiers avec 0% de couverture
  - [ ] Créer une matrice de couverture par module
  - [ ] Documenter les résultats dans `COVERAGE_BASELINE.md`

- [ ] **Identifier les fichiers critiques non testés**
  - [ ] Lister tous les fichiers `app/src/` sans tests
  - [ ] Prioriser par criticité (core business logic en premier)
  - [ ] Créer une issue GitHub par fichier critique

### Backend - Services API (Couverture Faible 22-53%)

- [ ] **player_operations_service.py (41% → 80%)**
  - [ ] Tester `play_track()` - tous les cas (succès, erreur, edge cases)
  - [ ] Tester `pause()` - états multiples
  - [ ] Tester `resume()` - validation état
  - [ ] Tester `stop()` - nettoyage ressources
  - [ ] Tester `next_track()` - navigation playlist
  - [ ] Tester `previous_track()` - navigation playlist
  - [ ] Tester `seek()` - validation position
  - [ ] Tester `set_volume()` - validation range
  - [ ] Tester gestion d'erreurs pour chaque opération
  - [ ] Tester interactions avec audio_controller

- [ ] **playlist_operations_service.py (22% → 80%)**
  - [ ] Tester `create_playlist()` - validation données
  - [ ] Tester `update_playlist()` - modifications
  - [ ] Tester `delete_playlist()` - cascade et cleanup
  - [ ] Tester `add_tracks()` - ajout multiple
  - [ ] Tester `remove_tracks()` - suppression multiple
  - [ ] Tester `reorder_tracks()` - réorganisation
  - [ ] Tester `move_track()` - déplacement
  - [ ] Tester validation des opérations
  - [ ] Tester broadcasting des changements
  - [ ] Tester gestion des erreurs

- [ ] **playlist_broadcasting_service.py (33% → 80%)**
  - [ ] Tester `broadcast_playlist_created()`
  - [ ] Tester `broadcast_playlist_updated()`
  - [ ] Tester `broadcast_playlist_deleted()`
  - [ ] Tester `broadcast_track_added()`
  - [ ] Tester `broadcast_track_removed()`
  - [ ] Tester format des événements
  - [ ] Tester gestion des abonnés
  - [ ] Tester fallback si broadcast échoue

- [ ] **player_broadcasting_service.py (53% → 80%)**
  - [ ] Tester `broadcast_player_state()`
  - [ ] Tester `broadcast_position_update()`
  - [ ] Tester `broadcast_volume_change()`
  - [ ] Tester throttling des événements
  - [ ] Tester gestion des erreurs de broadcast

### Frontend - Baseline

- [ ] **Générer rapport de couverture complet**
  ```bash
  npm run test:coverage
  ```
  - [ ] Analyser le rapport de couverture
  - [ ] Identifier tous les fichiers non testés
  - [ ] Documenter baseline dans `COVERAGE_BASELINE_FRONTEND.md`

---

## 🎯 PRIORITÉ 2 - IMPORTANTE (Semaine 2)

### Backend - Controllers (Application Layer)

- [ ] **audio_controller.py**
  - [ ] Tester initialisation avec différents backends
  - [ ] Tester lecture de fichier
  - [ ] Tester pause/resume
  - [ ] Tester stop
  - [ ] Tester changement de volume
  - [ ] Tester gestion de la queue
  - [ ] Tester événements audio (fin de lecture, erreur)
  - [ ] Tester cleanup ressources

- [ ] **playback_coordinator_controller.py**
  - [ ] Tester coordination entre services
  - [ ] Tester gestion de l'état global
  - [ ] Tester synchronisation playlist/player
  - [ ] Tester gestion des transitions d'état
  - [ ] Tester récupération après erreur

- [ ] **playlist_state_manager_controller.py**
  - [ ] Tester gestion de l'état playlist active
  - [ ] Tester persistance de l'état
  - [ ] Tester restauration après redémarrage
  - [ ] Tester synchronisation multi-clients
  - [ ] Tester validation de l'état

- [ ] **upload_controller.py**
  - [ ] Tester initialisation session upload
  - [ ] Tester upload de chunks
  - [ ] Tester finalisation upload
  - [ ] Tester validation fichiers
  - [ ] Tester gestion des erreurs réseau
  - [ ] Tester cleanup après échec
  - [ ] Tester reprise après interruption

### Backend - Routes API

- [ ] **player_api_routes.py**
  - [ ] Tester GET /player/status
  - [ ] Tester POST /player/play
  - [ ] Tester POST /player/pause
  - [ ] Tester POST /player/stop
  - [ ] Tester POST /player/next
  - [ ] Tester POST /player/previous
  - [ ] Tester POST /player/seek
  - [ ] Tester validation des requêtes
  - [ ] Tester codes d'erreur HTTP

- [ ] **playlist_api_routes.py**
  - [ ] Tester GET /playlists
  - [ ] Tester GET /playlists/{id}
  - [ ] Tester POST /playlists
  - [ ] Tester PUT /playlists/{id}
  - [ ] Tester DELETE /playlists/{id}
  - [ ] Tester POST /playlists/{id}/tracks
  - [ ] Tester DELETE /playlists/{id}/tracks/{track_id}
  - [ ] Tester pagination
  - [ ] Tester filtres et tri

- [ ] **system_api_routes.py**
  - [ ] Compléter tests GET /health (déjà 23 tests, 2 skipped)
  - [ ] Tester GET /system/info
  - [ ] Tester GET /system/logs
  - [ ] Tester POST /system/restart
  - [ ] Tester validation permissions

### Frontend - Stores

- [ ] **serverStateStore.ts**
  - [ ] Tester initialisation du store
  - [ ] Tester réception d'événements Socket.IO
  - [ ] Tester mise à jour de l'état serveur
  - [ ] Tester synchronisation server_seq
  - [ ] Tester gestion des erreurs
  - [ ] Tester reconnexion

- [ ] **uploadStore.ts**
  - [ ] Tester initialisation session upload
  - [ ] Tester progression upload
  - [ ] Tester finalisation upload
  - [ ] Tester gestion des erreurs
  - [ ] Tester annulation upload
  - [ ] Tester reprise après échec

### Frontend - Services

- [ ] **apiClient.ts**
  - [ ] Tester configuration client
  - [ ] Tester intercepteurs
  - [ ] Tester gestion des erreurs
  - [ ] Tester timeout
  - [ ] Tester retry logic

- [ ] **socketService.ts**
  - [ ] Tester connexion
  - [ ] Tester déconnexion
  - [ ] Tester reconnexion automatique
  - [ ] Tester émission d'événements
  - [ ] Tester réception d'événements
  - [ ] Tester gestion des erreurs
  - [ ] Tester heartbeat

### Frontend - Components

- [ ] **AudioPlayer.vue**
  - [ ] Tester affichage état lecture
  - [ ] Tester contrôles (play/pause/stop)
  - [ ] Tester navigation tracks
  - [ ] Tester barre de progression
  - [ ] Tester contrôle volume
  - [ ] Tester réactivité aux événements

- [ ] **FileListContainer.vue**
  - [ ] Tester affichage liste
  - [ ] Tester sélection fichiers
  - [ ] Tester tri
  - [ ] Tester filtres
  - [ ] Tester actions (supprimer, réorganiser)

---

## 🎯 PRIORITÉ 3 - NORMALE (Semaines 3-4)

### Backend - Domain Services

- [ ] **playback_state_manager.py**
  - [ ] Compléter tests existants (déjà 20 tests)
  - [ ] Tester transitions d'état complexes
  - [ ] Tester validation d'état
  - [ ] Tester événements de changement d'état

- [ ] **track_reordering_service.py**
  - [ ] Compléter tests existants (déjà 37 tests)
  - [ ] Tester edge cases de réorganisation
  - [ ] Tester validation des positions

### Backend - Infrastructure

- [ ] **sqlite_playlist_repository.py**
  - [ ] Compléter tests existants (déjà 10 tests)
  - [ ] Tester requêtes complexes
  - [ ] Tester transactions
  - [ ] Tester gestion des erreurs DB
  - [ ] Tester migrations

- [ ] **Créer tests pour repositories manquants**
  - [ ] track_repository
  - [ ] upload_session_repository
  - [ ] nfc_association_repository

### Backend - Tests d'Intégration Manquants

- [ ] **Upload Workflow E2E**
  - [ ] Test upload complet multi-chunks
  - [ ] Test reprise après interruption
  - [ ] Test annulation en cours
  - [ ] Test validation post-upload
  - [ ] Test cleanup après erreur

- [ ] **Player Workflow E2E**
  - [ ] Test lecture playlist complète
  - [ ] Test navigation entre tracks
  - [ ] Test modes lecture (normal, repeat, shuffle)
  - [ ] Test gestion file d'attente
  - [ ] Test persistance position

- [ ] **State Synchronization E2E**
  - [ ] Test sync multi-clients
  - [ ] Test résolution conflits
  - [ ] Test récupération après déconnexion
  - [ ] Test convergence état

### Frontend - Integration Tests

- [ ] **player-store-integration.test.ts**
  - [ ] Tester intégration complète player store + API
  - [ ] Tester synchronisation état
  - [ ] Tester gestion des erreurs

- [ ] **playlist-store-integration.test.ts**
  - [ ] Tester CRUD playlists
  - [ ] Tester synchronisation Socket.IO
  - [ ] Tester gestion conflits

### Frontend - Workflow Tests

- [ ] **audio-playback.test.ts**
  - [ ] Tester workflow lecture complet
  - [ ] Tester navigation
  - [ ] Tester contrôles

- [ ] **nfc-association.test.ts**
  - [ ] Tester workflow association NFC complet
  - [ ] Tester scan tag
  - [ ] Tester association playlist
  - [ ] Tester lecture automatique

- [ ] **playlist-management.test.ts**
  - [ ] Tester création playlist
  - [ ] Tester ajout/suppression tracks
  - [ ] Tester réorganisation
  - [ ] Tester suppression

---

## 🎯 PRIORITÉ 4 - BASSE (Mois 2)

### Backend - Tests de Performance

- [ ] **Player Performance Tests**
  - [ ] Test charge lecture simultanée
  - [ ] Test temps de réponse seek
  - [ ] Test consommation mémoire
  - [ ] Test gestion ressources audio

- [ ] **API Performance Tests**
  - [ ] Test charge endpoints (100 req/s)
  - [ ] Test temps de réponse moyen
  - [ ] Test timeout sous charge
  - [ ] Test rate limiting

- [ ] **Database Performance Tests**
  - [ ] Test requêtes complexes (temps d'exécution)
  - [ ] Test transactions lourdes
  - [ ] Test index efficacité
  - [ ] Test cleanup performance

### Backend - Tests de Sécurité

- [ ] **API Security Tests**
  - [ ] Test injection SQL
  - [ ] Test XSS
  - [ ] Test CSRF
  - [ ] Test validation entrées
  - [ ] Test authentification
  - [ ] Test autorisation

- [ ] **Upload Security Tests**
  - [ ] Test validation types fichiers
  - [ ] Test taille maximum
  - [ ] Test contenu malicieux
  - [ ] Test path traversal

### Frontend - E2E Tests

- [ ] **Player E2E**
  - [ ] Playwright: Test lecture complète
  - [ ] Playwright: Test contrôles UI
  - [ ] Playwright: Test navigation

- [ ] **Playlist E2E**
  - [ ] Playwright: Test gestion playlist
  - [ ] Playwright: Test upload fichiers
  - [ ] Playwright: Test réorganisation

- [ ] **NFC E2E**
  - [ ] Playwright: Test workflow NFC complet
  - [ ] Playwright: Test association tag
  - [ ] Playwright: Test lecture automatique

### Frontend - Tests d'Accessibilité

- [ ] **Accessibility Tests**
  - [ ] Test navigation clavier
  - [ ] Test screen readers
  - [ ] Test contraste couleurs
  - [ ] Test labels ARIA
  - [ ] Test focus management
  - [ ] Test responsive design

---

## 📊 MÉTRIQUES ET SUIVI

### Objectifs de Couverture

**Backend:**
- [ ] API Layer: 80%+ (actuellement 22-53%)
- [ ] Application Layer: 75%+
- [ ] Domain Layer: 85%+
- [ ] Infrastructure: 70%+
- [ ] **Global: 80%+**

**Frontend:**
- [ ] Stores: 90%+
- [ ] Services: 85%+
- [ ] Components: 80%+
- [ ] Utils: 90%+
- [ ] **Global: 85%+**

### Suivi Hebdomadaire

- [ ] **Semaine 1:** Générer rapports + Tester services API
- [ ] **Semaine 2:** Tester controllers + stores frontend
- [ ] **Semaine 3:** Tests d'intégration backend
- [ ] **Semaine 4:** Tests workflow frontend
- [ ] **Mois 2:** Tests performance + E2E

### Checkpoints

- [ ] **Checkpoint 1 (Fin Semaine 1):** Baseline établie + Services API 60%+
- [ ] **Checkpoint 2 (Fin Semaine 2):** Controllers 70%+ + Stores 80%+
- [ ] **Checkpoint 3 (Fin Semaine 3):** Integration tests complets
- [ ] **Checkpoint 4 (Fin Semaine 4):** Frontend workflows testés
- [ ] **Checkpoint 5 (Fin Mois 2):** Objectifs atteints (80%+ backend, 85%+ frontend)

---

## 🔧 INFRASTRUCTURE ET OUTILS

### CI/CD Integration

- [ ] **Configurer GitHub Actions**
  - [ ] Job tests backend avec couverture
  - [ ] Job tests frontend avec couverture
  - [ ] Bloquer merge si couverture < seuil
  - [ ] Générer rapport de couverture dans PR
  - [ ] Badge de couverture dans README

- [ ] **Code Quality Gates**
  - [ ] Configurer SonarQube/CodeClimate
  - [ ] Définir seuils qualité
  - [ ] Alertes régression couverture
  - [ ] Dashboard métriques

### Documentation

- [ ] **Documenter stratégie de test**
  - [ ] Créer `TESTING_STRATEGY.md`
  - [ ] Documenter types de tests (unit, integration, e2e)
  - [ ] Documenter conventions de nommage
  - [ ] Exemples de tests types

- [ ] **Guides de contribution**
  - [ ] Créer `CONTRIBUTING_TESTS.md`
  - [ ] Checklist tests pour nouvelles features
  - [ ] Workflow review tests
  - [ ] Best practices

---

## 📝 TEMPLATES DE TESTS

### Backend Test Template

- [ ] **Créer template test unitaire**
  ```python
  # tests/unit/template_unit_test.py
  ```

- [ ] **Créer template test intégration**
  ```python
  # tests/integration/template_integration_test.py
  ```

- [ ] **Créer template test contrat**
  ```python
  # tests/contracts/template_contract_test.py
  ```

### Frontend Test Template

- [ ] **Créer template test composant**
  ```typescript
  // tests/unit/components/template.test.ts
  ```

- [ ] **Créer template test store**
  ```typescript
  // tests/unit/stores/template.test.ts
  ```

- [ ] **Créer template test workflow**
  ```typescript
  // tests/integration/workflows/template.test.ts
  ```

---

## ✅ CHECKLIST VALIDATION

### Avant de Merger une PR

- [ ] Tous les tests passent
- [ ] Couverture globale n'a pas baissé
- [ ] Nouveaux fichiers ont des tests (>80%)
- [ ] Tests d'intégration pour nouvelles features
- [ ] Documentation tests à jour
- [ ] Pas de tests skippés sans raison

### Avant Release

- [ ] Couverture >= 80% backend
- [ ] Couverture >= 85% frontend
- [ ] Tous tests architecture passent
- [ ] Tous tests contrats passent
- [ ] Tests E2E critiques passent
- [ ] Tests de performance acceptables
- [ ] Rapport de couverture généré

---

## 🚀 COMMANDES RAPIDES

```bash
# Backend - Tests complets avec couverture
USE_MOCK_HARDWARE=true python -m pytest tests/ --cov=app/src --cov-report=html --cov-report=term -v

# Backend - Tests unitaires seulement
USE_MOCK_HARDWARE=true python -m pytest tests/unit -v

# Backend - Tests d'un module spécifique
USE_MOCK_HARDWARE=true python -m pytest tests/unit/api/services/test_player_operations_service.py -v

# Frontend - Tests complets avec couverture
npm run test:coverage

# Frontend - Tests unitaires
npm run test:unit

# Frontend - Tests spécifiques
npm run test -- src/tests/unit/stores/unifiedPlaylistStore.test.ts

# Frontend - Mode watch
npm run test:watch
```

---

**Date de création:** 2025-10-20
**Prochaine révision:** 2025-10-27
**Responsable:** Équipe Dev
**Status:** 🔴 TODO

