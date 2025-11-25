# TheMusicBox - Backend

> Backend for TheOpenMusicBox, an application that links music playlists to NFC tags for an interactive, tangible listening experience.

---

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Features](#features)
- [Requirements](#requirements)
- [Hardware Setup](#hardware-setup)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [State Management](#state-management)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)
- [Contact / Support](#contact--support)

---

## Architecture Overview

The Open Music Box backend implements a **server-authoritative state management architecture** designed for reliable hardware integration and real-time client synchronization.

### Core Design Principles

- **Single Source of Truth**: The backend maintains authoritative state for all playlists, tracks, and player status
- **Event-Driven Architecture**: Real-time updates via WebSocket events with sequence-based ordering
- **Hardware Abstraction**: Clean separation between business logic and hardware modules (NFC, audio, controls)
- **API Contract v2.0**: Unified HTTP+WebSocket interface with client operation tracking

### Key Architectural Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend Core   │    │   Hardware      │
│   (Vue.js)      │◄──►│   (FastAPI)      │◄──►│   (RPi + NFC)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
        │                       │                       │
        │                       │                       │
   WebSocket Events         State Manager          NFC Service
   HTTP API Calls          Playlist Service       Audio Player
   Client State Sync       Route Handlers         Physical Controls
```

### State Management Flow

1. **Client Operations**: Frontend sends HTTP requests with `client_op_id`
2. **Server Processing**: Backend processes operation and updates authoritative state
3. **Event Broadcasting**: Server broadcasts state changes via WebSocket with `server_seq`
4. **Client Synchronization**: All connected clients receive and apply state updates

---

## Features
- NFC tag reading and playlist association
- Audio playback with volume and navigation controls
- REST API for playlist and audio file management
- WebSocket interface for real-time updates
- YouTube content download support
- Raspberry Pi hardware compatibility


---

## Requirements
- **Python** 3.9+
- **FFmpeg** (for audio processing)
- **Hardware (for Raspberry Pi):**
  - NFC Reader (PN532)
  - Sound card (WM8960)
  - Physical controls (buttons, rotary encoder)
  - Raspberry Pi

---

## Hardware Setup
- **NFC Reader:** Connect PN532 to Raspberry Pi (I2C/SPI/UART as required)
- **Sound Card:** WM8960 wiring per manufacturer instructions
- **Physical Controls:** Wire buttons and rotary encoder to GPIO pins (see `app/src/module/controles/`)
- For troubleshooting and detailed wiring diagrams, see the [Hardware Setup Guide](docs/HARDWARE_SETUP.md) *(to be created)*

---

## Installation

### Development Environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

pip install -r requirements/dev.txt
```

#### Requirements Files
All requirements are now in the `requirements/` directory:
| File              | Purpose                                 |
|-------------------|-----------------------------------------|
| base.txt          | Core, cross-platform dependencies        |
| dev.txt           | Dev tools, lint, docs, CI (includes base)|
| prod.txt          | Raspberry Pi production (includes base)  |
| test.txt          | Testing/CI (includes base)               |

See `requirements/README.md` for details.

### Production Environment (Raspberry Pi)
```bash
sudo bash app/install_pi_system_deps.sh
python -m venv venv
source venv/bin/activate
pip install -r requirements/prod.txt
```

#### Automated Deployment
You can use the provided deployment script to install everything on your Raspberry Pi:
```bash
./install_on_pi.sh <pi_host> <target_dir> [--requirements prod|dev|test]
```
- Example: `./install_on_pi.sh pi@raspberrypi.local /home/pi/tmbbox --requirements prod`

This will copy the app folder, the selected requirements, `.env`, and `app.service`, then set up the virtual environment and install dependencies on the Pi.

---

## Configuration
Configuration parameters are defined in `app/src/config/app_config.py` and can be overridden using environment variables or a `.env` file.

### Environment Variables
| Variable           | Description                        | Default       |
|--------------------|------------------------------------|---------------|
| DEBUG              | Enable debug mode                  | False         |
| SOCKETIO_HOST      | SocketIO server host               | 0.0.0.0       |
| SOCKETIO_PORT      | SocketIO server port               | 5004          |
| UPLOAD_FOLDER      | Path for uploaded files            | uploads       |
| AUTO_PAUSE_ENABLED | Enable auto-pause on disconnect    | True          |
| ...                | *(see app_config.py for more)*     |               |

**Example `.env` file:**
```
DEBUG=True
SOCKETIO_HOST=0.0.0.0
SOCKETIO_PORT=5004
UPLOAD_FOLDER=uploads
AUTO_PAUSE_ENABLED=True
```

---

## Usage

### Development
```bash
python start_dev.py
```

### Production
```bash
python start_app.py
```

### Tests
```bash
pytest
```

---

## API Documentation

The backend uses FastAPI, which provides auto-generated, interactive API documentation. Once the backend server is running, you can access the following documentation UIs:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

These interfaces allow you to explore and test all available API endpoints directly from your browser.

### Example Endpoints
- `GET /api/volume` — Get the current system volume
- `POST /api/volume` — Set the system volume (0-100)
- `GET /api/health` — Health check and subsystem status
- `GET /api/playlists` — List playlists
- `POST /api/playlists` — Create a new playlist
- `POST /api/youtube/download` — Download a YouTube playlist or track

> **Note:** The root URL and port may differ if you change the default configuration. See your environment variables or `start_app.py` for details.

- Interactive API docs available at [`/docs`](http://localhost:5004/docs) when running (FastAPI default)
- Example endpoints:
  - `GET /api/playlists`
  - `POST /api/playlists`
  - `GET /api/tracks/{track_id}`
  - ...
- See [API Reference](docs/API_REFERENCE.md) *(to be created)*

---

## Project Structure

```
back/
├── app/                          # Application source code
│   ├── src/                      # Main modules
│   │   ├── config/               # App configuration
│   │   ├── core/                 # Core application components
│   │   │   ├── application.py    # Main application orchestrator
│   │   │   ├── service_container.py # Dependency injection
│   │   │   └── playlist_controller.py # Playlist coordination
│   │   ├── services/             # Business services
│   │   │   ├── state_manager.py  # Server-authoritative state management
│   │   │   ├── nfc_service.py    # NFC tag reading and management
│   │   │   ├── playlist_service.py # Playlist business logic
│   │   │   └── track_management_service.py # Track operations
│   │   ├── routes/               # API routes
│   │   │   ├── playlist_routes_state.py # Playlist HTTP endpoints
│   │   │   ├── websocket_handlers_state.py # WebSocket event handlers
│   │   │   └── player_routes.py  # Audio player endpoints
│   │   ├── module/               # Hardware integration modules
│   │   │   ├── audio_player/     # Audio playback system
│   │   │   ├── nfc/              # NFC hardware interface
│   │   │   └── controles/        # Physical controls (buttons, encoder)
│   │   ├── controllers/          # Request controllers
│   │   ├── interfaces/           # Abstract interfaces
│   │   ├── model/                # Data models
│   │   └── utils/                # Utility functions
│   ├── data/                     # User data (playlists, audio files)
│   └── static/                   # Frontend build output
├── tests/                        # Unit and integration tests
├── requirements/                 # Python dependencies
└── scripts/                      # Utility scripts
```

### Key Components Explained

- **`core/application.py`**: Main application class that orchestrates all services
- **`services/state_manager.py`**: Implements server-authoritative state pattern
- **`services/nfc_service.py`**: Handles NFC tag reading and playlist associations
- **`module/audio_player/`**: Hardware-abstracted audio playback system
- **`routes/websocket_handlers_state.py`**: Real-time event broadcasting
- **`routes/playlist_routes_state.py`**: HTTP API for playlist operations

---

## State Management

The backend implements a sophisticated state management system designed for reliability and real-time synchronization.

### Server-Authoritative Pattern

**Core Principle**: The server is the single source of truth for all application state.

```python
# Example: Client requests playlist creation
POST /api/playlists
{
  "client_op_id": "uuid-123",
  "name": "My Playlist"
}

# Server processes and broadcasts state change
WebSocket Event: {
  "event_type": "state:playlists",
  "server_seq": 42,
  "data": { /* updated playlists */ }
}
```

### State Event Types

- **`state:playlists`**: Complete playlists snapshot
- **`state:playlist`**: Individual playlist updates
- **`state:player`**: Audio player state changes
- **`state:track_progress`**: Playback progress updates
- **`state:volume_changed`**: System volume changes
- **`state:nfc_state`**: NFC reader status

### Event Sequencing

All state events include a `server_seq` number to ensure proper ordering and prevent race conditions:

```python
@dataclass
class StateEvent:
    event_type: StateEventType
    server_seq: int
    playlist_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
```

### Client Operation Tracking

HTTP requests include `client_op_id` for operation acknowledgment:

- Client sends operation with unique ID
- Server processes and responds with success/error
- Server broadcasts resulting state changes
- Clients can correlate their operations with state updates

---

## Development Workflow
- **Linting:**
  - `flake8` for style checks
  - `pydocstyle` for docstring checks
- **Formatting:**
  - Use `black` or `isort` as configured
- **Pre-commit Hooks:**
  - Install with `pre-commit install`
  - Configured in `.pre-commit-config.yaml`
- **Code conventions:**
  - See `plan_amelioration.md` for coding standards and guidelines

---

## Testing
- Run all tests:
  ```bash
  pytest
  ```
- Test coverage is reported automatically if `pytest-cov` is installed
- Add new tests in the relevant `tests/` subdirectory

---

## Deployment

### Exporting a Public Package
To create a public-ready package (for open source or distribution):
```bash
./export_public_package.sh /path/to/export_dir
```
This will export only the `app` folder, production requirements, README, and service file to the target directory.

### Deploying to Raspberry Pi
See the Production Environment section above for automated deployment instructions.

- *(Add instructions for running as a service, Docker, or other deployment tools if applicable)*

---

## Contributing
- Please follow the code conventions and improvement plan in `plan_amelioration.md`
- Open issues or submit pull requests for new features or bug fixes

---

## License

This project is open source and released under the following terms:

- You are free to use, copy, modify, and distribute this software for any non-commercial purpose.
- Contributions are welcome from anyone via pull requests or issues.
- **Commercial use and monetization (selling, offering paid services, or bundling with paid products) is reserved exclusively to the original author (Jonathan Piette).**
- If you wish to monetize or use this project commercially, please contact the maintainer for licensing options.

---

## Contact / Support
- For questions, open an issue on GitHub or contact the maintainer.
- *(Add Discord, email, or other channels if available)*
