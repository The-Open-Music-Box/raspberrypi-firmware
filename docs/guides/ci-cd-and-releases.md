# CI/CD and Release Workflow

This document explains the CI/CD setup, self-hosted runner configuration, and release workflow for TheOpenMusicBox.

## Overview

The project uses GitHub Actions for CI/CD with:
- **Self-hosted runner** on a Raspberry Pi for ARM64-specific tests
- **Automated releases** triggered by version tags

---

## Self-Hosted GitHub Runner

### Why Self-Hosted?

- Tests hardware-specific code on actual Raspberry Pi
- ARM64 architecture matching production environment
- Access to GPIO and audio hardware for integration tests

### Runner Setup

#### 1. Install Runner on Raspberry Pi

```bash
# SSH into your runner Pi
ssh pi@ip

# Create actions runner directory
mkdir actions-runner && cd actions-runner

# Download latest runner package (ARM64)
curl -o actions-runner-linux-arm64-2.311.0.tar.gz -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-arm64-2.311.0.tar.gz

# Extract
tar xzf ./actions-runner-linux-arm64-2.311.0.tar.gz
```

#### 2. Configure the Runner

Get a new registration token from GitHub:

```bash
# Via GitHub API
gh api -X POST repos/The-Open-Music-Box/raspberrypi-firmware/actions/runners/registration-token --jq .token
```

Configure the runner with the token:

```bash
# Remove old configuration if exists
./config.sh remove --token YOUR_OLD_TOKEN

# Configure with new token and correct labels
./config.sh --url https://github.com/The-Open-Music-Box/raspberrypi-firmware \
  --token YOUR_NEW_TOKEN \
  --labels self-hosted,Linux,ARM64,rpi \
  --name your-runner-name
```

#### 3. Install as Service

```bash
# Install systemd service
sudo ./svc.sh install

# Start the service
sudo ./svc.sh start

# Enable on boot
sudo systemctl enable actions.runner.The-Open-Music-Box-raspberrypi-firmware.your-runner-name.service
```

### Monitoring Runner Status

```bash
# Check service status
sudo systemctl status actions.runner.The-Open-Music-Box-raspberrypi-firmware.your-runner-name.service

# View runner logs
journalctl -u actions.runner.The-Open-Music-Box-raspberrypi-firmware.your-runner-name.service -f
```

### Troubleshooting Runner Issues

#### Runner shows "offline"

```bash
# Restart the service
sudo systemctl restart actions.runner.The-Open-Music-Box-raspberrypi-firmware.your-runner-name.service

# Check if runner is listening
ps aux | grep Runner.Listener
```

#### Registration expired

```bash
# Get new token and reconfigure
gh api -X POST repos/The-Open-Music-Box/raspberrypi-firmware/actions/runners/registration-token --jq .token

# Reconfigure runner
cd ~/actions-runner
./config.sh remove --token YOUR_TOKEN
./config.sh --url https://github.com/The-Open-Music-Box/raspberrypi-firmware \
  --token YOUR_NEW_TOKEN \
  --labels self-hosted,Linux,ARM64,rpi
```

---

## Release Workflow

### Overview

Releases are automated via GitHub Actions when a version tag is pushed. The workflow:

1. Builds the Vue.js frontend
2. Packages backend + frontend into `tomb/` directory
3. Creates versioned and stable archives
4. Publishes GitHub Release with assets

### Creating a New Release

#### 1. Prepare Changes

Ensure all changes are committed and pushed to `develop`:

```bash
git checkout develop
git status
git add .
git commit -m "feat(module): description"
git push origin develop
```

#### 2. Verify CI Passes

Wait for CI to complete on develop:

```bash
gh run list --branch develop --limit 5
```

#### 3. Merge to Main

```bash
git checkout main
git pull origin main
git merge develop
git push origin main
```

#### 4. Update Version

Edit the VERSION file:

```bash
# Current version format: MAJOR.MINOR.PATCH or MAJOR.MINOR.PATCH-dev
echo "0.5.4" > VERSION
```

#### 5. Create and Push Tag

```bash
# Create annotated tag
git tag -a v0.5.4 -m "Release v0.5.4"

# Push tag to trigger release workflow
git push origin v0.5.4
```

#### 6. Monitor Release Build

```bash
# Watch the release workflow
gh run watch

# Or list recent workflow runs
gh run list --workflow=release.yml --limit 5
```

### Release Assets

Each release includes:

| File | Description |
|------|-------------|
| `tomb.tar.gz` | Stable URL - always latest version |
| `tomb.zip` | Stable URL - always latest version |
| `tomb-vX.Y.Z.tar.gz` | Versioned archive |
| `tomb-vX.Y.Z.zip` | Versioned archive |

Users can download:
- **Latest**: `https://github.com/The-Open-Music-Box/raspberrypi-firmware/releases/latest/download/tomb.tar.gz`
- **Specific**: `https://github.com/The-Open-Music-Box/raspberrypi-firmware/releases/download/v0.5.4/tomb-v0.5.4.tar.gz`

---

## Version Numbering

### Format

```
MAJOR.MINOR.PATCH[-dev]
```

- **MAJOR**: Breaking changes or major features
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, minor improvements
- **-dev**: Development version (not released)

### Examples

| Version | Type | Description |
|---------|------|-------------|
| `0.5.0` | Major feature | New playlist sharing feature |
| `0.5.1` | Feature | Added volume persistence |
| `0.5.2` | Bug fix | Fixed WM8960 driver installation |
| `0.5.3` | Bug fix | Bundled driver files for offline install |
| `0.5.4-dev` | Development | Working on next release |

### Workflow

1. After release, bump VERSION to next `-dev`:
   ```bash
   echo "0.5.5-dev" > VERSION
   git add VERSION
   git commit -m "chore: bump version to 0.5.5-dev"
   git push origin develop
   ```

2. Before release, remove `-dev`:
   ```bash
   echo "0.5.5" > VERSION
   ```

---

## GitHub Actions Workflow Files

### Main CI Workflow

Located at `.github/workflows/ci.yml` - runs on pull requests and pushes to develop/main.

### Release Workflow

Located at `.github/workflows/release.yml` - triggered by version tags:

```yaml
on:
  push:
    tags:
      - 'v*'
```

Key features:
- Requires `permissions: contents: write` for release creation
- Uses `softprops/action-gh-release` action
- Creates both versioned and stable-named archives

---

## Troubleshooting Releases

### Release fails with 403 error

Ensure workflow has write permissions:

```yaml
permissions:
  contents: write
```

### Frontend build fails

```bash
# Test build locally
cd front
npm ci
npm run build
```

### Archive missing files

Check `release.yml` package step includes all necessary files:
- `back/drivers/` for WM8960 driver
- `back/tools/` for utility scripts
- `back/.env.example` or `back/.env`

### Tag already exists

```bash
# Delete local tag
git tag -d v0.5.4

# Delete remote tag
git push origin :refs/tags/v0.5.4

# Recreate and push
git tag -a v0.5.4 -m "Release v0.5.4"
git push origin v0.5.4
```

---

## Quick Reference

### Release Checklist

- [ ] All changes committed to develop
- [ ] CI passes on develop
- [ ] Merged develop to main
- [ ] Updated VERSION file (removed -dev)
- [ ] Created annotated tag (v0.5.X)
- [ ] Pushed tag to origin
- [ ] Monitored release workflow
- [ ] Bumped VERSION to next -dev on develop

### Useful Commands

```bash
# Check runner status
ssh your-runner-host "sudo systemctl status actions.runner.*.service"

# List recent releases
gh release list --limit 5

# View release details
gh release view v0.5.4

# Monitor workflows
gh run list --limit 10

# Get runner registration token
gh api -X POST repos/The-Open-Music-Box/raspberrypi-firmware/actions/runners/registration-token --jq .token
```
