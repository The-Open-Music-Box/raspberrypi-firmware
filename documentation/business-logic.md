# The Open Music Box - Business Logic Documentation

## Overview

The Open Music Box is an NFC-enabled music player system that allows users to manage playlists and play music by scanning NFC tags or using a web interface. This document outlines the core business logic that governs the application's behavior.

## System Architecture

The application follows a server-authoritative pattern where:
- The backend maintains the single source of truth for all state
- The frontend reflects the server state and sends user actions via HTTP requests
- Real-time updates are pushed to the frontend via WebSocket connections
- All UI state changes must be validated and confirmed by the server

---

## Playlist Management

### Core Functionality
- **Pagination**: Web UI displays playlists in batches of 50 to optimize performance
- **Real-time Synchronization**: Playlist state automatically updates across all clients without requiring page refresh
- **CRUD Operations**: Full create, read, update, and delete capabilities for both playlists and individual tracks
- **Playlist Sync**: At the start of the server, empty playlists are deleted from the db and missing playlist or tracks are added to the db to keep the uploads folder sync to the current db state.

### Playlist Operations
1. **Create Playlist**: Users can create new playlists through the web interface
2. **Delete Playlist**: Entire playlists can be removed from the system
3. **Track Management**: Within playlists, users can:
   - Add new audio files
   - Remove existing tracks
   - Reorder tracks by moving them up/down in the playlist

### UI Behavior
- **Collapsed by Default**: Playlist details (track listings) are hidden initially to provide a clean interface
- **Expandable Details**: Users can expand playlists to view and manage individual tracks
- **Live Updates**: Any modifications (add/remove/reorder) are immediately reflected in the UI across all connected clients

---

## User Interface Modes

The web interface operates in two distinct modes to separate content consumption from content management.

### Normal Mode
- **Purpose**: Primary viewing and playback mode
- **Features**:
  - Display all playlists and their songs
  - Play button on each playlist header to start playback
  - NFC association button available on each playlist
- **Interactions**: Focused on music discovery and playback initiation

### Edit Mode
- **Purpose**: Content management and file upload mode
- **Features**:
  - All Normal Mode functionality remains available
  - Upload zones appear on each playlist for direct file uploads
  - Drag-and-drop file upload capability
- **File Management**: Users can upload audio files directly to specific playlists

### Common Features (Both Modes)
- **NFC Association**: Available in both modes via dedicated association buttons
- **Playlist Navigation**: Full playlist browsing capabilities
- **Real-time Updates**: Live synchronization across all connected devices

---

## NFC Association System

The NFC association system enables physical NFC tags to trigger playlist playback, creating a tactile music experience.

### Association Process

#### Initiating Association Mode
1. User clicks the association button on any playlist
2. Backend enters **Association Mode** - a special state that:
   - Prevents any NFC-triggered playlist playback
   - Activates NFC tag scanning with a 60-second timeout
   - Broadcasts association status to all connected clients via WebSocket

#### Tag Reading Workflow
When an NFC tag is scanned during association mode:

**New/Unknown Tag**:
1. Tag UID is read and checked against existing associations
2. If tag is unregistered, it's automatically associated with the selected playlist
3. Association dialog is dismissed
4. System waits for tag removal before exiting association mode
5. Once tag is removed, system returns to normal play mode

**Known/Registered Tag**:
1. Tag UID is recognized as already associated
2. UI displays override dialog showing:
   - Current playlist name associated with the tag
   - Override button to reassign the tag
3. User can either:
   - Click override to reassign tag to new playlist
   - Scan a different tag to continue association process

#### Association Rules
- **Unique Association**: Each NFC tag can only be associated with one playlist
- **Exclusive Mapping**: One tag = one playlist (no sharing between playlists)
- **Override Capability**: Existing associations can be overwritten with explicit user confirmation

#### Mode Transitions
- **Entry**: Normal/Edit Mode → Association Mode (60s timeout)
- **Exit**: Association Mode → Play Mode (after successful association and tag removal)
- **Timeout**: Association Mode → Play Mode (if no tag scanned within 60 seconds)

### Playback Prevention
During association mode, the system specifically blocks:
- NFC-triggered playlist playback
- Automatic music start from tag scanning
- This ensures tags are properly associated before being used for playback

---

## Audio Player System

The audio player provides comprehensive playback control and real-time status information across all connected devices.

### Player Display Information
The player interface always shows current playback status:
- **Playlist Title**: Name of the currently playing playlist
- **Track Title**: Name of the current song
- **Track Duration**: Total length of the current track
- **Playback Progress**: Current position with interactive seek bar
- **Playback Status**: Play/pause state indicator

### Playback Controls

#### Play/Pause Control
- **UI Button**: Interactive play/pause toggle button
- **State Management**: Backend determines actual play/pause state
- **Multi-source Pause**: Player can be paused from:
  - Web interface button
  - Physical hardware buttons
  - API calls from external sources
- **State Persistence**: Pause state maintained across all interfaces

#### Track Navigation
- **Previous Track**: Navigate to previous song in playlist (when available)
- **Next Track**: Navigate to next song in playlist (when available)
- **Button State**: Navigation buttons activate/deactivate based on playlist position
- **Seamless Transition**: Automatic progression to next track upon completion

#### Seek Control
- **Interactive Seek Bar**: Users can click/drag to jump to specific time positions
- **Real-time Updates**: Seek bar continuously reflects current playback position
- **HTTP Communication**: Seek requests sent via HTTP to backend
- **Immediate Response**: Playback position updates immediately upon seek

### Communication Architecture

#### Backend → Frontend (WebSocket)
Real-time push updates for:
- Current playback status (playing/paused)
- Track information changes
- Progress updates
- Playlist transitions
- Player state changes

#### Frontend → Backend (HTTP)
User action requests:
- Play/pause commands
- Track navigation (next/previous)
- Seek position changes
- Volume adjustments (if implemented)

### Playback Triggers
The player can be activated through multiple methods:
1. **Web Interface**: Play button on playlist headers
2. **NFC Tags**: Scanning associated NFC tags (when not in association mode)
3. **Physical Controls**: Hardware buttons (if configured)
4. **API Calls**: Direct backend API requests

### State Synchronization
- **Server-Authoritative**: Backend maintains definitive player state
- **Live Updates**: All connected clients receive real-time status updates
- **Consistent Experience**: Player status remains synchronized across all devices and interfaces

---

## Technical Implementation Notes

### WebSocket Events
The system uses WebSocket connections for real-time communication:
- Playlist state changes
- Player status updates
- NFC association status
- File upload progress
- System notifications

### Error Handling
- Network disconnections are handled gracefully
- Failed operations are retried automatically where appropriate
- User feedback is provided for all failed operations

### Performance Considerations
- Playlist pagination (50 items) prevents UI performance issues with large collections
- Lazy loading of track details reduces initial load time
- WebSocket updates are batched to prevent flooding
- File uploads use chunked transfer for large audio files

---

## File Upload System

The application provides a robust file upload system designed to handle large audio files efficiently while providing real-time feedback to users.

### Core Features
- **Chunked Upload**: Large files are split into smaller chunks for reliable transfer
- **Real-time Progress Tracking**: Users see upload progress with percentage and transfer rates
- **Session-based Upload Management**: Each upload maintains a persistent session for error recovery
- **Multiple Concurrent Uploads**: Users can upload several files simultaneously to different playlists

### Upload Process Flow
1. **Session Initialization**: System creates upload session with unique ID and determines optimal chunk size
2. **Chunked Transfer**: File is split and uploaded in sequential chunks with progress updates
3. **Error Recovery**: Failed chunks are automatically retried without restarting entire upload
4. **Finalization**: Once all chunks are received, system processes the audio file and adds it to the playlist
5. **Real-time Integration**: New tracks immediately appear in the playlist across all connected clients

### Technical Implementation
- **Progress Events**: Real-time upload progress via WebSocket (`upload:progress`, `upload:complete`)
- **Validation**: File type and size validation before upload begins
- **Optimization**: Adaptive chunk sizing based on connection quality
- **Cleanup**: Automatic cleanup of incomplete upload sessions after timeout

### User Interface Integration
- **Edit Mode**: Upload zones appear on each playlist when in edit mode
- **Drag & Drop**: Intuitive file dropping directly onto desired playlist
- **Progress Indicators**: Visual progress bars with transfer statistics
- **Error Feedback**: Clear error messages with retry options for failed uploads

---

## User Experience Flows

### Playing Music via NFC
1. User associates NFC tag with desired playlist (one-time setup)
2. User scans NFC tag near device
3. Associated playlist begins playing immediately
4. Player UI updates to show current track information
5. User can control playback via web interface

### Adding Music to Collection
1. User switches to Edit Mode
2. User drags audio files to desired playlist upload zone
3. Files are uploaded and processed
4. New tracks appear in playlist automatically
5. Changes are synchronized across all connected devices

### Managing Playlists
1. User creates new playlist via web interface
2. User uploads audio files to populate playlist
3. User reorders tracks as desired
4. User associates NFC tag with playlist (optional)
5. Playlist is immediately available for playback

This business logic ensures a seamless, multi-modal music experience that combines physical interaction (NFC tags) with modern web interface capabilities, all while maintaining real-time synchronization across all connected devices.