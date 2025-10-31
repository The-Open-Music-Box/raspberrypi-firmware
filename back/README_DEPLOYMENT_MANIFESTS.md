# Deployment Manifest System

## Overview

TheOpenMusicBox uses a **declarative manifest system** for controlling which files are included in deployments. This approach provides:

- **Single source of truth**: File selection rules are defined in one place
- **Version control**: Manifests are tracked with the code
- **Clarity**: Easy to understand what gets deployed
- **Flexibility**: Different file sets for dev vs. production

## Manifest Files

### `.deploy-exclude`

**Purpose**: Lists files and patterns to EXCLUDE from ALL deployments (dev and prod)

**Format**: One rsync-style pattern per line

**Examples**:
```bash
# Exclude Python cache
__pycache__/
*.pyc

# Exclude tests
tests/
test_*.py

# Exclude development tools
.pytest_cache/
.coverage
```

**Used by**:
- `deploy.sh` (package_release function)
- `export_public_package.sh` (public release builds)

### `.deploy-include`

**Purpose**: Explicitly lists what SHOULD be deployed (documentation/reference)

**Format**: Relative paths from `back/` directory

**Examples**:
```bash
app/
requirements.txt
start_app.py
README.md
tools/
```

**Note**: This file is primarily for documentation. The actual deployment uses `.deploy-exclude` with rsync to copy everything except excluded patterns.

### `.deploy-dev-include`

**Purpose**: Additional files to include ONLY in development deployments

**Format**: Relative paths from `back/` directory

**Examples**:
```bash
tests/
documentation/
run_tests.sh
pytest.ini
```

**Used by**:
- `deploy.sh` when called with `--dev` flag

## How It Works

### Production Deployment (`./deploy.sh --prod`)

1. Reads `.deploy-exclude` to build exclusion list
2. Uses `rsync` with `--exclude` patterns to copy backend files
3. Excludes all development files (tests, docs, coverage, etc.)
4. Results in minimal production-ready package

### Development Deployment (`./deploy.sh --dev`)

1. Reads `.deploy-exclude` to build exclusion list
2. Reads `.deploy-dev-include` to build inclusion list
3. Includes development tools for local testing
4. Results in full development environment

### Public Release (`./build_public_release.sh`)

1. Calls `export_public_package.sh`
2. Uses `.deploy-exclude` for clean public distribution
3. Creates archive suitable for public download

## Usage Examples

### Adding a New File Type to Exclude

Edit `.deploy-exclude`:
```bash
# Add at the end
*.backup
temp_*.py
```

### Adding Development-Only Files

Edit `.deploy-dev-include`:
```bash
# Tools for local debugging
debug_tools/
profiler.py
```

### Validation

After modifying manifests, test the deployment:

```bash
# Test production build (should exclude dev files)
./deploy.sh --build-only --verbose

# Check what was packaged
ls -la release_dev/tomb-rpi/

# Ensure no test files are present
find release_dev/tomb-rpi -name "test_*" -o -name "*_test.py"

# Test development build (should include dev files)
./deploy.sh --dev --skip-tests --no-monitor
```

## Migration from Old System

### Before (Hardcoded in deploy.sh)
```bash
rsync -a --delete \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='logs' \
    # ... more hardcoded patterns
```

### After (Manifest-based)
```bash
# Build exclusions from manifest
local exclude_args=()
while IFS= read -r pattern; do
    [[ -z "$pattern" || "$pattern" =~ ^[[:space:]]*# ]] && continue
    exclude_args+=("--exclude=$pattern")
done < "$deploy_exclude"

rsync -a --delete "${exclude_args[@]}" ...
```

## Benefits

1. **Maintainability**: Single file to update instead of multiple scripts
2. **Consistency**: Same exclusions across all deployment paths
3. **Documentation**: Comments explain why files are excluded
4. **Testability**: Can validate manifests against actual file tree
5. **Flexibility**: Easy to add environment-specific rules

## Troubleshooting

### Files Still Being Included

Check if pattern in `.deploy-exclude` is correct:
```bash
# Test rsync pattern matching
rsync --dry-run --exclude-from=back/.deploy-exclude \
    back/ /tmp/test-deploy/
```

### Development Files Missing in Dev Build

Check `.deploy-dev-include` has the pattern:
```bash
cat back/.deploy-dev-include | grep "your-file"
```

### Critical Files Missing from Production

1. Check if accidentally excluded in `.deploy-exclude`
2. Verify file exists in `back/` directory
3. Run deployment with `--verbose` flag

## Related Files

- `deploy.sh`: Main deployment script using manifests
- `export_public_package.sh`: Public release export using manifests
- `build_public_release.sh`: Calls export script
- `sync_tmbdev.config`: Legacy RSYNC_EXCLUDES (deprecated for manifest usage)

## See Also

- [Main README](README.md)
- [Deploy Guide](../DEPLOY_GUIDE.md)
- [Contract Integration](README_CONTRACTS.md)
