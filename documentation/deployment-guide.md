# TheOpenMusicBox Deployment Guide

This guide explains the complete deployment process for TheOpenMusicBox application, including both backend and frontend components.

## Overview

TheOpenMusicBox is a full-stack application with:
- A **Backend** built with FastAPI and SQLite
- A **Frontend** built with Vue.js and TypeScript

The deployment process uses automated scripts to build, package, and deploy components to a Raspberry Pi.

## Directory Structure

```
tomb-rpi/
├── back/                      # Backend code
│   ├── app/                   # FastAPI application
│   │   ├── src/               # Source code
│   │   └── ...
│   ├── export_public_package.sh  # Script to prepare backend for deployment
│   └── ...
├── front/                     # Frontend code
│   ├── src/                   # Vue.js source code
│   ├── dist/                  # Built frontend (after npm run build)
│   └── ...
├── public_release/            # Public release staging area
│   └── tomb-rpi/              # Combined backend and frontend for public distribution
│       ├── app/               # Backend code
│       │   ├── static/        # Frontend static files
│       │   └── ...
│       └── ...
├── release_dev/               # Development build staging area (excluded from git)
│   └── tomb-rpi/              # Combined backend and frontend for development deployment
├── build_public_release.sh    # Script to create public release package
├── sync_tmbdev.sh            # Script to build and sync to development server
├── sync_tmbdev.config        # Configuration file for deployment scripts
└── tomb-rpi-release-YYYYMMDD.tar.gz  # Generated release archive
```

## Deployment Methods

There are two main deployment workflows:

### 1. Development Deployment (sync_tmbdev.sh)

For development and testing, use the sync script to build and upload directly to your Raspberry Pi:

```bash
cd /path/to/tomb-rpi
./sync_tmbdev.sh
```

This script:
1. Creates a development build in the `release_dev/` directory (excluded from git)
2. Exports the backend package using `export_public_package.sh`
3. Builds the frontend with `npm run build`
4. Combines backend and frontend in `release_dev/tomb-rpi/`
5. Uses `rsync` over SSH to synchronize files to the Raspberry Pi
6. Sets proper permissions on the remote files

### 2. Public Release (build_public_release.sh)

For creating distributable packages for end users:

```bash
cd /path/to/tomb-rpi
./build_public_release.sh
```

This script:
1. Creates a clean build in the `public_release/` directory
2. Exports the backend package
3. Builds the frontend
4. Combines backend and frontend
5. Creates a timestamped tar.gz archive (e.g., `tomb-rpi-release-20240821.tar.gz`)
6. Sets up an empty data directory structure for users

## Configuration

### Deployment Configuration (sync_tmbdev.config)

The `sync_tmbdev.config` file contains all deployment settings:

```bash
# SSH connection settings
SSH_DEST="tomb"                                      # SSH alias or user@host
SSH_KEY="~/.ssh/musicbox_key"                        # Path to SSH private key
SSH_OPTS="-o StrictHostKeyChecking=accept-new -o IdentitiesOnly=yes"

# Remote server settings
REMOTE_DIR="/home/admin/tomb"                        # Remote directory on the Pi

# Build directories
RELEASE_DEV_DIR="release_dev"                        # Development release directory
PUBLIC_RELEASE_DIR="public_release/tomb-rpi"         # Public release directory
```

### Environment Variables

The frontend relies on several environment variables:

- `VUE_APP_API_URL`: The URL where the backend API is accessible
- `VUE_APP_PUBLIC_PATH`: The public path for static assets
- `VUE_APP_ASSETS_DIR`: The directory for assets within the public path

## Networking Configuration

### Backend Server

The backend server runs on the Raspberry Pi at:
- Host: `localhost` or `theopenmusicbox.local`
- Port: `5004`

### Frontend Access

When deployed, the frontend is served by the backend and can be accessed at:
- URL: `http://theopenmusicbox.local:5004/`

### API and Socket.IO Configuration

The frontend communicates with the backend through:

1. **REST API Calls**: Using Axios to make HTTP requests to endpoints defined in `apiRoutes.ts`
2. **Real-time Events**: Using Socket.IO for WebSocket communication

Critical configuration points:

- The Socket.IO client is configured to connect to the same origin as the web application using `window.location.origin`, which allows it to adapt to different access methods (e.g., localhost, hostname, IP address)
- The API base URL is set by the `VUE_APP_API_URL` environment variable
- During development, API requests are proxied through the Vue dev server as configured in `vue.config.js`

## Troubleshooting

### Connection Issues

If the frontend cannot connect to the backend:

1. Verify that the backend server is running on the Raspberry Pi
2. Check that the Raspberry Pi is accessible at `theopenmusicbox.local`
3. Ensure the backend is listening on port 5004
4. Confirm that the frontend is using the correct API URL
5. Check for CORS issues in the backend logs

### Empty Playlist Display Issues

If playlists are not displayed correctly:

1. Verify the backend API returns the correct format (`{"playlists":[]}` for empty playlists)
2. Check the frontend console for JavaScript errors
3. Ensure the Socket.IO connection is established successfully
4. Validate that the API service correctly handles empty arrays

### Socket.IO Polling Errors

If you see Socket.IO polling errors:

1. Verify network connectivity to the Raspberry Pi
2. Check that Socket.IO is using the same origin as the application
3. Confirm that WebSocket connections are not blocked by any network equipment
4. Try accessing the application using different URLs to identify any hostname resolution issues

## SSH Configuration

### Setting up SSH Access

Before using the sync script, ensure SSH access is properly configured:

1. **SSH Key**: Generate or use an existing SSH key pair
2. **SSH Config**: Add an entry to `~/.ssh/config`:
   ```
   Host tomb
       HostName theopenmusicbox.local
       User admin
       IdentityFile ~/.ssh/musicbox_key
       StrictHostKeyChecking accept-new
   ```
3. **Key Path**: Update the `SSH_KEY` path in `sync_tmbdev.config` if needed

### SSH Connection Override

You can override the SSH destination from the command line:

```bash
./sync_tmbdev.sh user@hostname
```

## File Exclusions

The sync process automatically excludes development files and directories:

- Python cache files (`__pycache__/`, `*.pyc`, `*.pyo`)
- Virtual environments (`venv/`, `.venv`, `ENV/`)
- IDE files (`.idea/`, `.vscode/`)
- Build artifacts (`dist/`, `build/`, `*.egg-info/`)
- System files (`.DS_Store`)
- Application data (`app/data/` - to preserve existing data on the Pi)
- Log files (`*.log`, `logs/`)

## End User Deployment

### For End Users (Public Release)

End users receive a `tomb-rpi-release-YYYYMMDD.tar.gz` file containing:

1. **Extract the archive**:
   ```bash
   tar -xzf tomb-rpi-release-YYYYMMDD.tar.gz
   ```

2. **Copy to Raspberry Pi**:
   ```bash
   scp -r tomb-rpi/ admin@theopenmusicbox.local:/home/admin/tomb/
   ```

3. **Set permissions**:
   ```bash
   ssh admin@theopenmusicbox.local "sudo chown -R admin:admin /home/admin/tomb"
   ```

The public release includes an empty data directory structure but excludes any existing database or user data.

## Maintenance

### Updating the Application

**For Development:**
```bash
./sync_tmbdev.sh
```

**For Public Release:**
```bash
./build_public_release.sh
```

### Backup

The SQLite database is located at `/home/admin/tomb/app/data/app.db` on the Raspberry Pi. Regular backups of this file are recommended.
