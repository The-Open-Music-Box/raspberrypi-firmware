# Documentation Technique - Backend RPI Firmware

Ce dossier contient la documentation technique essentielle pour la maintenance et l'évolution du système.

## 📚 Table des matières

### Architecture

- **[DDD_ARCHITECTURE_DOCUMENTATION.md](./DDD_ARCHITECTURE_DOCUMENTATION.md)**
  Architecture Domain-Driven Design du système backend. Décrit les couches (Domain, Application, Infrastructure) et les principes de conception.

- **[DATABASE_ARCHITECTURE_DOCUMENTATION.md](./DATABASE_ARCHITECTURE_DOCUMENTATION.md)**
  Architecture de la base de données SQLite. Schémas, relations et stratégies de migration.

### Intégration & APIs

- **[README_CONTRACTS.md](./README_CONTRACTS.md)**
  Documentation sur l'intégration des contrats OpenAPI et Socket.IO. Explique comment utiliser le submodule `contracts` et valider la conformité.

- **[LED_INTEGRATION_GUIDE.md](./LED_INTEGRATION_GUIDE.md)**
  Guide complet d'intégration du système LED RGB. États, priorités, événements et exemples d'utilisation.

### Bonnes pratiques

- **[ERROR_HANDLING_BEST_PRACTICES.md](./ERROR_HANDLING_BEST_PRACTICES.md)**
  Standards et patterns pour la gestion d'erreurs dans tout le codebase. Logging, propagation, recovery patterns.

---

## 📝 Notes

- Cette documentation est maintenue à jour avec le code
- Pour les guides de déploiement, voir `/DEPLOY_GUIDE.md` à la racine
- Pour les exemples de code, consulter les tests d'intégration dans `/tests/integration/`

## 🔄 Mise à jour

Lors de modifications architecturales majeures, mettre à jour la documentation correspondante :
- Nouveaux domaines → DDD_ARCHITECTURE_DOCUMENTATION.md
- Nouveaux schémas DB → DATABASE_ARCHITECTURE_DOCUMENTATION.md
- Nouveaux endpoints/events → README_CONTRACTS.md
- Nouveaux états LED → LED_INTEGRATION_GUIDE.md
