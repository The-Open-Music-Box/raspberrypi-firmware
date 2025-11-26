# 🚀 Release Workflow Guide

Guide rapide pour créer et publier des nouvelles versions de TheOpenMusicBox.

## 📋 Vue d'ensemble

Le système de versioning utilise le format **Semantic Versioning** en version beta :
- Format : `0.MINOR.PATCH`
- Exemple : `0.4.1` → `0.5.0` → `0.5.1`
- Une fois stable (v1.0.0), on utilisera `MAJOR.MINOR.PATCH`

## 🎯 Workflow de Release

### 1. Préparer votre branche

```bash
# Assurez-vous d'être sur la branche main ou feature à release
git checkout main
git pull origin main

# Vérifiez que tout est propre
git status
```

### 2. Mettre à jour la version

Utilisez le script `bump_version.sh` :

```bash
# Pour un bug fix : 0.4.1 → 0.4.2
./bump_version.sh patch

# Pour une nouvelle fonctionnalité : 0.4.1 → 0.5.0
./bump_version.sh minor

# Pour un breaking change : 0.4.1 → 1.0.0
./bump_version.sh major

# Pour une version spécifique
./bump_version.sh 0.6.0
```

**Le script fait automatiquement :**
- ✅ Vérifie que git est propre
- ✅ Met à jour `VERSION`
- ✅ Met à jour `front/package.json`
- ✅ Ajoute une entrée dans `CHANGELOG.md`
- ✅ Crée un commit git
- ✅ Crée un tag git annoté

### 3. Éditer le CHANGELOG

Après avoir exécuté `bump_version.sh`, éditez `CHANGELOG.md` pour ajouter les détails :

```markdown
## [0.5.0] - 2025-10-26

### Added
- RGB LED status indicator with boot error detection
- NFC tag association verification in normal mode

### Changed
- Refactored LED architecture (status vs events pattern)

### Fixed
- Circular import issues in dependency injection
```

Puis amendez le commit :

```bash
git add CHANGELOG.md
git commit --amend --no-edit
```

### 4. Pousser la release

```bash
# Pousser le commit
git push origin feat/version-management

# Pousser le tag
git push origin v0.5.0
```

### 5. Merger dans main

```bash
# Créer une PR ou merger directement
git checkout main
git merge feat/version-management
git push origin main

# Pousser le tag sur main
git push origin v0.5.0
```

### 6. Déployer

```bash
# Déployer en production
./deploy.sh --prod tomb

# Ou déployer en dev pour tester
./deploy.sh --dev
```

## 📦 Types de Versions

### Patch (0.4.1 → 0.4.2)
**Quand :** Corrections de bugs uniquement

```bash
./bump_version.sh patch
```

**Exemples :**
- Correction d'un bug NFC
- Fix d'affichage dans l'UI
- Correction de tests qui échouent

### Minor (0.4.1 → 0.5.0)
**Quand :** Nouvelles fonctionnalités (backward compatible)

```bash
./bump_version.sh minor
```

**Exemples :**
- Ajout du support RGB LED
- Nouvelle page dans l'interface
- Nouvelle API endpoint
- Feature flag activée

### Major (0.x.y → 1.0.0)
**Quand :** Breaking changes ou sortie de beta

```bash
./bump_version.sh major
```

**Exemples :**
- Sortie de beta publique → v1.0.0
- Changement d'API incompatible
- Refonte majeure de l'architecture

## 🔄 Workflow Complet Exemple

```bash
# 1. Créer une branche feature
git checkout -b feat/rgb-led-indicator

# 2. Développer et commiter
git add .
git commit -m "feat(led): add RGB LED indicator system"

# 3. Merger dans main
git checkout main
git merge feat/rgb-led-indicator

# 4. Bump version (pour nouvelle feature = minor)
./bump_version.sh minor
# Version 0.4.1 → 0.5.0

# 5. Éditer CHANGELOG.md avec détails
vim CHANGELOG.md
git add CHANGELOG.md
git commit --amend --no-edit

# 6. Pousser
git push origin main
git push origin v0.5.0

# 7. Déployer
./deploy.sh --prod tomb
```

## 📊 Commandes Utiles

```bash
# Voir la version actuelle
cat VERSION

# Voir tous les tags
git tag -l

# Voir les détails d'un tag
git show v0.5.0

# Voir l'historique des versions
git log --oneline --decorate --tags

# Annuler un bump (avant push)
git reset --hard HEAD~1
git tag -d v0.5.0

# Vérifier la version dans le backend
cd back && python3 -c "from app import __version__; print(__version__)"

# Vérifier la version dans le frontend
grep version front/package.json
```

## 🎯 Checklist Pre-Release

Avant de créer une release, vérifiez :

- [ ] Tous les tests passent (`./deploy.sh --test-only`)
- [ ] La documentation est à jour
- [ ] Les contrats sont synchronisés (`git submodule update --remote`)
- [ ] Le CHANGELOG.md est complet et détaillé
- [ ] Git status est propre (no uncommitted changes)
- [ ] La version suit le format correct (0.X.Y)

## 🚨 Troubleshooting

### Le script refuse de bumper (git dirty)
```bash
# Vérifier ce qui n'est pas commité
git status

# Commiter ou stash
git add .
git commit -m "fix: something"
# ou
git stash
```

### Tag déjà existant
```bash
# Supprimer le tag local
git tag -d v0.5.0

# Supprimer le tag remote (DANGER!)
git push origin :refs/tags/v0.5.0
```

### Corriger un CHANGELOG après bump
```bash
# Éditer CHANGELOG.md
vim CHANGELOG.md

# Amender le commit
git add CHANGELOG.md
git commit --amend --no-edit

# Recréer le tag
git tag -d v0.5.0
git tag -a v0.5.0 -m "Release v0.5.0"
```

## 🎉 Après la Release

1. ✅ Vérifier que le tag est sur GitHub
2. ✅ Créer une GitHub Release (optionnel)
3. ✅ Annoncer la release (si applicable)
4. ✅ Monitorer les logs après déploiement
5. ✅ Mettre à jour la documentation externe si nécessaire

---

**Version actuelle du système de release :** v0.5.4-dev (see VERSION file for current version)
**Date de création de ce guide :** 2025-10-26
