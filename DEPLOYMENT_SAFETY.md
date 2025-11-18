# Deployment Safety Guidelines

## ⚠️ CRITICAL: Data Protection

### NEVER Use rsync Manually

**❌ NEVER DO THIS:**
```bash
rsync -avz --delete release_dev/tomb-rpi/ server:/home/admin/tomb/
```

**Why?** This will DELETE all production data including:
- `app/data/database.db` - All playlists, tracks, and NFC associations
- `app/data/uploads/` - All music files
- `venv/` - Python virtual environment

### ✅ ALWAYS Use the Deployment Script

```bash
# Correct way to deploy
./deploy.sh --prod tombdev --skip-tests
./deploy.sh --prod tomb
```

The deployment script (`deploy.sh`) automatically:
1. Loads exclusions from `sync_tmbdev.config`
2. Protects `app/data/` and `venv/` directories
3. Only updates application code

## Protected Directories

These directories are **excluded from deployment** via `sync_tmbdev.config`:

```bash
--exclude=app/data/          # Database and uploads (NEVER delete)
--exclude=venv/              # Virtual environment (NEVER delete)
--exclude=*.pyc              # Python cache
--exclude=__pycache__/       # Python cache
--exclude=logs/              # Application logs
```

## Emergency Recovery

If production data is lost:
1. Stop the service: `ssh server sudo systemctl stop app.service`
2. Restore from backup
3. Restart the service: `ssh server sudo systemctl restart app.service`

## Manual Deployment (Only if script fails)

If you **absolutely must** deploy manually:

```bash
# 1. Load exclusions from config
source sync_tmbdev.config

# 2. Deploy with exclusions
rsync -azP --delete \
    "${RSYNC_EXCLUDES[@]}" \
    release_dev/tomb-rpi/ \
    server:/home/admin/tomb/

# 3. Restart service
ssh server sudo systemctl restart app.service
```

## Why the Script Hung

The deployment script may hang during rsync if:
- Network is slow
- Large files are being transferred
- SSH connection times out

**Solution**: Use `--verbose` flag to see progress:
```bash
./deploy.sh --prod tombdev --skip-tests --verbose
```

## Incident Report: 2025-10-31

**What happened**: Manual rsync with `--delete` deleted all production data on tmbdev

**Cause**: Used `rsync --delete` without loading exclusions from config file

**Data lost**:
- 5 playlists with UUID-based folder names
- All music files in uploads directory
- Virtual environment

**Prevention**:
- ✅ Created this documentation
- ✅ Verified deployment script loads exclusions correctly
- ✅ Confirmed exclusions protect `app/data/` and `venv/`

## Testing Deployments Safely

Test on development server first:
```bash
# 1. Deploy to dev
./deploy.sh --dev

# 2. Test functionality

# 3. Deploy to production
./deploy.sh --prod tomb
```

## Key Takeaway

🚨 **NEVER bypass the deployment script unless you absolutely understand the rsync exclusions**
