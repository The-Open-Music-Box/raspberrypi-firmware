---
title: "Release Workflow Guide"
status: active
category: operations
last_reviewed: 2026-02-09
review_cycle: 6months
---

# Release Workflow Guide

Quick guide for creating and publishing new versions of TheOpenMusicBox.

## Overview

The versioning system uses the **Semantic Versioning** format in beta version:
- Format: `0.MINOR.PATCH`
- Example: `0.4.1` -> `0.5.0` -> `0.5.1`
- Once stable (v1.0.0), `MAJOR.MINOR.PATCH` will be used

## Release Workflow

### 1. Prepare Your Branch

```bash
# Make sure you are on the main or feature branch to release
git checkout main
git pull origin main

# Verify everything is clean
git status
```

### 2. Update the Version

Use the `bump_version.sh` script:

```bash
# For a bug fix: 0.4.1 -> 0.4.2
./bump_version.sh patch

# For a new feature: 0.4.1 -> 0.5.0
./bump_version.sh minor

# For a breaking change: 0.4.1 -> 1.0.0
./bump_version.sh major

# For a specific version
./bump_version.sh 0.6.0
```

**The script automatically:**
- Verifies that git is clean
- Updates `VERSION`
- Updates `front/package.json`
- Adds an entry in `CHANGELOG.md`
- Creates a git commit
- Creates an annotated git tag

### 3. Edit the CHANGELOG

After running `bump_version.sh`, edit `CHANGELOG.md` to add the details:

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

Then amend the commit:

```bash
git add CHANGELOG.md
git commit --amend --no-edit
```

### 4. Push the Release

```bash
# Push the commit
git push origin feat/version-management

# Push the tag
git push origin v0.5.0
```

### 5. Merge into Main

```bash
# Create a PR or merge directly
git checkout main
git merge feat/version-management
git push origin main

# Push the tag on main
git push origin v0.5.0
```

### 6. Deploy

```bash
# Deploy to production
./deploy.sh --prod tomb

# Or deploy to dev for testing
./deploy.sh --dev
```

## Version Types

### Patch (0.4.1 -> 0.4.2)
**When:** Bug fixes only

```bash
./bump_version.sh patch
```

**Examples:**
- NFC bug fix
- UI display fix
- Fixing failing tests

### Minor (0.4.1 -> 0.5.0)
**When:** New features (backward compatible)

```bash
./bump_version.sh minor
```

**Examples:**
- Adding RGB LED support
- New page in the interface
- New API endpoint
- Feature flag enabled

### Major (0.x.y -> 1.0.0)
**When:** Breaking changes or exit from beta

```bash
./bump_version.sh major
```

**Examples:**
- Public beta release -> v1.0.0
- Incompatible API change
- Major architecture overhaul

## Complete Workflow Example

```bash
# 1. Create a feature branch
git checkout -b feat/rgb-led-indicator

# 2. Develop and commit
git add .
git commit -m "feat(led): add RGB LED indicator system"

# 3. Merge into main
git checkout main
git merge feat/rgb-led-indicator

# 4. Bump version (for new feature = minor)
./bump_version.sh minor
# Version 0.4.1 -> 0.5.0

# 5. Edit CHANGELOG.md with details
vim CHANGELOG.md
git add CHANGELOG.md
git commit --amend --no-edit

# 6. Push
git push origin main
git push origin v0.5.0

# 7. Deploy
./deploy.sh --prod tomb
```

## Useful Commands

```bash
# View current version
cat VERSION

# View all tags
git tag -l

# View tag details
git show v0.5.0

# View version history
git log --oneline --decorate --tags

# Undo a bump (before push)
git reset --hard HEAD~1
git tag -d v0.5.0

# Check version in the backend
cd back && python3 -c "from app import __version__; print(__version__)"

# Check version in the frontend
grep version front/package.json
```

## Pre-Release Checklist

Before creating a release, verify:

- [ ] All tests pass (`./deploy.sh --test-only`)
- [ ] Documentation is up to date
- [ ] Contracts are synchronized (`git submodule update --remote`)
- [ ] CHANGELOG.md is complete and detailed
- [ ] Git status is clean (no uncommitted changes)
- [ ] Version follows the correct format (0.X.Y)

## Troubleshooting

### Script refuses to bump (git dirty)
```bash
# Check what is not committed
git status

# Commit or stash
git add .
git commit -m "fix: something"
# or
git stash
```

### Tag already exists
```bash
# Delete local tag
git tag -d v0.5.0

# Delete remote tag (DANGER!)
git push origin :refs/tags/v0.5.0
```

### Fix CHANGELOG after bump
```bash
# Edit CHANGELOG.md
vim CHANGELOG.md

# Amend the commit
git add CHANGELOG.md
git commit --amend --no-edit

# Recreate the tag
git tag -d v0.5.0
git tag -a v0.5.0 -m "Release v0.5.0"
```

## After the Release

1. Verify that the tag is on GitHub
2. Create a GitHub Release (optional)
3. Announce the release (if applicable)
4. Monitor logs after deployment
5. Update external documentation if necessary

---

**Current release system version:** v0.4.1
**Date this guide was created:** 2025-10-26
