# The Open Music Box - Frontend

> Frontend for TheOpenMusicBox, a Vue.js application that provides a user interface for managing music playlists, NFC tags, and system settings.

## Table of Contents
- [Overview](#overview)
- [Project Structure](#project-structure)
- [Development Setup](#development-setup)
- [Build Process](#build-process)
- [Key Components](#key-components)
- [API Integration](#api-integration)
- [Configuration](#configuration)
- [Testing](#testing)
- [Deployment](#deployment)

## Overview

The frontend for The Open Music Box is built with Vue.js and provides a responsive web interface for:
- Managing music playlists and tracks
- Uploading audio files
- Controlling playback
- Configuring NFC tag associations
- Monitoring system status

## Project Structure

```
front/
├── public/                 # Static assets that are copied without processing
│   ├── img/                # Images and icons
│   ├── favicon.ico         # Website favicon
│   └── index.html          # HTML template
├── scripts/                # Build and optimization scripts
│   ├── optimize-images.js  # Image optimization script
│   └── optimize-logo.js    # Logo optimization script
├── src/                    # Source code
│   ├── assets/             # Assets that will be processed by webpack
│   ├── components/         # Vue components
│   │   ├── audio/          # Audio playback components
│   │   ├── layout/         # Layout components (header, footer, etc.)
│   │   ├── playlist/       # Playlist management components
│   │   ├── settings/       # Settings and configuration components
│   │   └── upload/         # File upload components
│   ├── config/             # Configuration files
│   │   ├── apiRoutes.ts    # API endpoint definitions
│   │   └── appConfig.ts    # Application configuration
│   ├── services/           # Service layer for API communication
│   │   ├── apiService.ts   # API service interface
│   │   └── realApiService.ts # Concrete API service implementation
│   ├── stores/             # Pinia stores for state management
│   ├── types/              # TypeScript type definitions
│   ├── utils/              # Utility functions
│   ├── views/              # Page components
│   ├── App.vue             # Root component
│   ├── main.ts             # Application entry point
│   └── router.ts           # Vue Router configuration
├── .env                    # Environment variables
├── .env.build              # Production build environment variables
├── .env.development        # Development environment variables
├── package.json            # NPM dependencies and scripts
├── tsconfig.json           # TypeScript configuration
└── vue.config.js           # Vue CLI configuration
```

## Development Setup

1. **Prerequisites**:
   - Node.js 14+ and npm 6+
   - Backend server running (see `/back/README.md`)

2. **Installation**:
   ```bash
   # Navigate to the frontend directory
   cd front
   
   # Install dependencies
   npm install
   ```

3. **Start development server**:
   ```bash
   npm run serve
   ```
   This will:
   - Start a development server with hot-reload
   - Compile and place the output in `../back/app/static/`
   - Open the application in your browser at `http://localhost:8080`

## Build Process

The frontend build process is integrated with the backend:

1. **Development build**:
   ```bash
   npm run serve
   ```
   Outputs to `../back/app/static/` for immediate testing with the backend.

2. **Production build**:
   ```bash
   npm run build
   ```
   Creates optimized production files in `dist/` that are later copied to the appropriate location by deployment scripts.

## Key Components

### Playlist Management
- `PlaylistList.vue`: Displays and manages playlists
- `PlaylistDetail.vue`: Shows tracks in a playlist
- `TrackItem.vue`: Individual track display and controls

### Audio Playback
- `AudioPlayer.vue`: Main audio player component
- `PlaybackControls.vue`: Play, pause, next, previous controls
- `VolumeControl.vue`: Volume slider and mute toggle

### File Upload
- `SimpleUploader.vue`: Drag-and-drop file uploader with chunked upload
- `UploadModal.vue`: Modal dialog for file upload
- `UploadProgress.vue`: Shows upload progress and status

### Settings
- `SystemSettings.vue`: System configuration options
- `NfcManager.vue`: NFC tag association management

## API Integration

The frontend communicates with the backend through a service layer:

- `apiService.ts`: Interface defining all API methods
- `realApiService.ts`: Implementation using Axios for HTTP requests
- `apiRoutes.ts`: Central definition of all API endpoints

Example usage:
```typescript
import { useApiService } from '@/services/apiService';

const api = useApiService();
const playlists = await api.getPlaylists();
```

## Configuration

Environment-specific configuration is managed through `.env` files:

- `.env`: Base configuration shared across all environments
- `.env.development`: Development-specific settings
- `.env.build`: Production build settings

Key configuration options:
```
VUE_APP_API_BASE_URL=http://localhost:5004/api
VUE_APP_SOCKET_URL=http://localhost:5004
VUE_APP_TITLE=The Open Music Box
```

## Testing

Tests are written using Vitest:

```bash
# Run tests
npm run test

# Run tests with coverage
npm run test:coverage
```

## Deployment

The frontend is automatically deployed as part of the backend deployment process:

1. The frontend is built using `npm run build`
2. Build output is copied to the backend's static directory
3. The backend serves the frontend files

For more details on deployment, see the main project README.md.
