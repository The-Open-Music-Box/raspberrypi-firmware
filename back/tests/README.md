# Test Suite Organization

Cette documentation décrit l'organisation des tests pour The Open Music Box.

## Structure des Tests

```
tests/
├── functional/          # Tests fonctionnels end-to-end
├── integration/          # Tests d'intégration
├── unit/                # Tests unitaires
├── contract/            # Tests de contrat
├── conftest.py          # Configuration pytest partagée
└── README.md           # Cette documentation
```

## Types de Tests

### Tests Unitaires (`unit/`)
Tests qui vérifient le comportement d'une seule unité de code (fonction, classe, méthode) en isolation.

**Exemples :**
- `test_path_utils.py` - Tests des utilitaires de normalisation de chemins
- Tests des services individuels sans dépendances externes

**Critères :**
- Rapides à exécuter (< 1ms par test)
- Aucune dépendance externe (base de données, fichiers, réseau)
- Utilisation de mocks/stubs pour les dépendances
- Couverture élevée des edge cases

### Tests d'Intégration (`integration/`)
Tests qui vérifient l'interaction entre plusieurs composants du système.

**Exemples :**
- Tests de l'API avec base de données réelle
- Tests des services avec leurs dépendances
- Tests de la persistance des données

**Critères :**
- Utilisent des dépendances réelles mais contrôlées
- Base de données de test isolée
- Vérification des flux de données entre couches

### Tests Fonctionnels (`functional/`)
Tests qui vérifient les fonctionnalités complètes du point de vue utilisateur.

**Exemples :**
- `test_track_deletion_with_file_cleanup.py` - Test complet de suppression de tracks avec nettoyage fichiers
- `test_playlist_folder_deletion.py` - Test complet de suppression de playlists avec nettoyage dossiers
- `test_serialization_service.py` - Test complet du service de sérialisation

**Critères :**
- Simulent des scénarios réels d'utilisation
- Tests end-to-end avec toutes les couches
- Vérification des effets de bord (fichiers, état)
- Plus lents mais plus représentatifs

### Tests de Contrat (`contract/`)
Tests qui vérifient les contrats d'API et les interfaces.

## Conventions de Nommage

### Fichiers
- `test_*.py` - Préfixe obligatoire pour pytest
- Noms descriptifs reflétant le composant testé
- Suffixes selon le type :
  - `_unit.py` pour les tests unitaires spécifiques
  - `_integration.py` pour les tests d'intégration spécifiques
  - Pas de suffixe pour les tests fonctionnels

### Classes de Test
- `class Test<ComponentName>` pour les tests d'un composant
- `class Test<FeatureName>` pour les tests d'une fonctionnalité

### Méthodes de Test
- `test_<what_is_tested>_<expected_outcome>()`
- Exemples :
  - `test_delete_tracks_removes_files()`
  - `test_serialize_playlist_handles_none_duration()`
  - `test_normalize_folder_name_special_characters()`

## Fixtures et Configuration

### Fixtures Communes (`conftest.py`)
- `test_config` - Configuration de test isolée
- `temp_database` - Base de données temporaire
- `playlist_repository_adapter` - Repository configuré pour les tests
- `unified_controller` - Contrôleur avec mocks appropriés

### Fixtures Spécifiques
Définies dans chaque fichier de test selon les besoins.

## Exécution des Tests

### Scripts Disponibles

#### Script Unifié Principal (Recommandé)
- **`run_tests_unified.sh`** - Script moderne avec toutes les fonctionnalités

#### Script de Compatibilité
- **`run_business_logic_tests.sh`** - Wrapper de compatibilité (déprécié)

### Commandes les Plus Utilisées

```bash
# ⚡ Validation rapide de la logique métier (le plus utilisé)
./run_tests_unified.sh --business-logic

# 🔬 Suite complète de tests
./run_tests_unified.sh

# 🤖 Pipeline CI/CD (silencieux, ignore les warnings)
./run_tests_unified.sh --quiet --warnings ignore

# 📖 Voir toutes les options
./run_tests_unified.sh --help
```

### Modes de Test Comparés

| Mode | Commande | Tests Exécutés | Cas d'Usage |
|------|----------|----------------|-------------|
| **Logique Métier** | `--business-logic` | 13 tests | 🎯 Validation rapide |
| **Suite Complète** | *(défaut)* | 40+ tests | 🔬 Vérification complète |
| **CI/CD** | `--quiet --warnings ignore` | Tous tests | 🤖 Pipelines automatisés |
| **Debug** | `--verbose --warnings strict` | Tous tests | 🐛 Dépannage |

### Usage pour Développeurs

#### Développement Quotidien
```bash
# Vérification rapide pendant le développement
./run_tests_unified.sh --business-logic

# Avant commit
./run_tests_unified.sh --business-logic --quiet
```

#### Avant Déploiement
```bash
# Validation complète
./run_tests_unified.sh

# Préparation production
./run_tests_unified.sh --warnings strict
```

#### Intégration CI/CD
```bash
# Dans votre pipeline CI
./run_tests_unified.sh --quiet --warnings ignore --timeout 120
```

### Compatibilité Legacy
```bash
# Fonctionne encore mais affiche un avertissement de dépréciation
./run_business_logic_tests.sh
```

### Migration vers le Système Unifié

#### Phase Actuelle ✅
- `run_tests_unified.sh` - Script principal avec toutes les fonctionnalités
- `run_business_logic_tests.sh` - Wrapper pour la compatibilité

#### Phase Future (dans 2-3 mois)
- `run_tests_unified.sh` - Seul script nécessaire
- Suppression : `run_business_logic_tests.sh`

#### Avantages du Système Unifié

**Avant** (2 scripts)
```bash
./run_business_logic_tests.sh     # Logique métier uniquement
# ./run_tests_robust.sh           # Script supprimé - remplacé par run_tests.sh
```

**Après** (1 script)
```bash
./run_tests_unified.sh --business-logic          # Même que l'ancienne logique métier
./run_tests_unified.sh --quiet --warnings ignore # Même que l'ancien robust
./run_tests_unified.sh --verbose                 # Nouveau : sortie détaillée
./run_tests_unified.sh --help                    # Nouveau : système d'aide
```

**Bénéfices :**
- ✅ **Source unique de vérité** pour l'exécution des tests
- ✅ **Options flexibles** pour différents cas d'usage
- ✅ **Meilleure gestion d'erreurs** et expérience utilisateur
- ✅ **Maintenance facilitée** - un seul script à maintenir
- ✅ **Interface cohérente** pour tous les modes de test

### Exécution Directe avec pytest

#### Tous les Tests
```bash
python -m pytest tests/
```

#### Par Catégorie
```bash
python -m pytest tests/unit/          # Tests unitaires
python -m pytest tests/integration/   # Tests d'intégration
python -m pytest tests/functional/    # Tests fonctionnels
```

#### Tests Spécifiques
```bash
python -m pytest tests/functional/test_track_deletion_with_file_cleanup.py
python -m pytest tests/unit/test_path_utils.py::TestPathUtils::test_normalize_folder_name_basic_cases
```

#### Avec Options
```bash
python -m pytest tests/ -v              # Verbose
python -m pytest tests/ -x              # Stop au premier échec
python -m pytest tests/ --tb=short      # Tracebacks courts
python -m pytest tests/ -k "deletion"   # Tests contenant "deletion"
```

## Couverture de Code

### Génération du Rapport
```bash
python -m pytest tests/ --cov=app/src --cov-report=html
```

### Objectifs de Couverture
- **Services critiques** : > 95%
- **Contrôleurs** : > 90%
- **Utilitaires** : > 95%
- **Routes** : > 80%

## Bonnes Pratiques

### Organisation du Code de Test
1. **Arrange** - Préparation des données et mocks
2. **Act** - Exécution de l'action à tester
3. **Assert** - Vérification des résultats

### Isolation des Tests
- Chaque test doit être indépendant
- Utilisation de fixtures pour la configuration
- Nettoyage automatique après chaque test

### Données de Test
- Utiliser des données représentatives mais anonymisées
- Éviter les données sensibles même en test
- Prévoir les cas limite et edge cases

### Performance
- Tests unitaires : < 1ms chacun
- Tests d'intégration : < 100ms chacun
- Tests fonctionnels : < 1s chacun
- Suite complète : < 30s

## Maintenance

### Ajout de Nouveaux Tests
1. Identifier le type de test approprié
2. Créer dans le bon répertoire
3. Suivre les conventions de nommage
4. Ajouter à la documentation si nécessaire

### Refactoring
- Maintenir les tests à jour lors des changements de code
- Réviser les tests obsolètes
- Optimiser les tests lents

Cette organisation assure une couverture complète de la logique métier tout en maintenant des tests maintenables et performants.