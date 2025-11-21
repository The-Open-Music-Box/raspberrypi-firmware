/**
 * API Routes Constants
 *
 * This file centralizes all API routes and socket events used in the application.
 * All routes are aligned with the backend API documentation found in /documentation/routes-api.md
 */

/**
 * API Configuration Constants
 */
export const API_CONFIG = {
  PLAYLISTS_FETCH_LIMIT: 100  // Number of playlists to fetch at once
} as const

/**
 * Base API routes
 */
export const API_ROUTES = {
  // Playlists
  PLAYLISTS: '/api/playlists/',
  PLAYLIST: (id: string) => `/api/playlists/${id}`,
  // Chunked upload routes (REST compliant)
  PLAYLIST_UPLOAD_SESSION: (id: string) => `/api/playlists/${id}/uploads/session`,
  PLAYLIST_UPLOAD_CHUNK: (playlistId: string, sessionId: string, chunkIndex: number) => 
    `/api/playlists/${playlistId}/uploads/${sessionId}/chunks/${chunkIndex}`,
  PLAYLIST_UPLOAD_FINALIZE: (playlistId: string, sessionId: string) => 
    `/api/playlists/${playlistId}/uploads/${sessionId}/finalize`,
  PLAYLIST_UPLOAD_STATUS: (playlistId: string, sessionId: string) => 
    `/api/playlists/${playlistId}/uploads/${sessionId}`,
  PLAYLIST_REORDER: (id: string) => `/api/playlists/${id}/reorder`,
  DELETE_TRACKS: (id: string) => `/api/playlists/${id}/tracks`,
  PLAYLIST_TRACK: (playlistId: string, trackNumber: number) =>
    `/api/playlists/${playlistId}/play/${trackNumber}`,
  PLAYLIST_SYNC: '/api/playlists/sync',
  PLAYLIST_MOVE_TRACK: (id: string) => `/api/playlists/${id}/move-track`,

  // Player routes (server-authoritative)
  PLAYER_STATUS: '/api/player/status',
  PLAYER_PLAY: '/api/player/play',
  PLAYER_PAUSE: '/api/player/pause',
  PLAYER_STOP: '/api/player/stop',
  PLAYER_NEXT: '/api/player/next',
  PLAYER_PREVIOUS: '/api/player/previous',
  PLAYER_TOGGLE: '/api/player/toggle',
  PLAYER_SEEK: '/api/player/seek',
  
  // Playlist playback
  PLAYLIST_START: (id: string) => `/api/playlists/${id}/start`,
  PLAYLIST_PLAY_TRACK: (playlistId: string, trackNumber: number) =>
    `/api/playlists/${playlistId}/play/${trackNumber}`,

  // NFC (unified API)
  NFC_ASSOCIATE: '/api/nfc/associate',
  NFC_REMOVE_ASSOCIATION: (tagId: string) => `/api/nfc/associate/${tagId}`,
  NFC_STATUS: '/api/nfc/status',
  NFC_SCAN: '/api/nfc/scan',

  // YouTube
  YOUTUBE_SEARCH: '/api/youtube/search',
  YOUTUBE_DOWNLOAD: '/api/youtube/download',
  YOUTUBE_STATUS: (taskId: string) => `/api/youtube/status/${taskId}`,

  // System
  SYSTEM_INFO: '/api/system/info',
  SYSTEM_LOGS: '/api/system/logs',
  SYSTEM_RESTART: '/api/system/restart',
  VOLUME: '/api/player/volume',
  HEALTH: '/api/health',
  PLAYBACK_STATUS: '/api/playback/status',

  // Upload management utilities
  UPLOAD_SESSIONS_LIST: '/api/uploads/sessions',
  UPLOAD_SESSION_DELETE: (sessionId: string) => `/api/uploads/sessions/${sessionId}`,
  UPLOAD_CLEANUP: '/api/uploads/cleanup',
}

/**
 * Socket events - Server-Authoritative Architecture v2.0
 * Canonical events only per API Contract
 */
export const SOCKET_EVENTS = {
  // Connection events
  CONNECT: 'connect',
  DISCONNECT: 'disconnect',
  CONNECT_ERROR: 'connect_error',
  RECONNECT: 'reconnect',
  CONNECTION_STATUS: 'connection_status',

  // Clean real-time state events
  STATE_PLAYLISTS: 'state:playlists',
  STATE_PLAYLIST: 'state:playlist',
  STATE_TRACK: 'state:track',
  STATE_PLAYER: 'state:player',
  STATE_TRACK_PROGRESS: 'state:track_progress',
  STATE_TRACK_POSITION: 'state:track_position',

  // Upload events
  UPLOAD_PROGRESS: 'upload:progress',
  UPLOAD_COMPLETE: 'upload:complete',
  UPLOAD_ERROR: 'upload:error',

  // Operation acknowledgments
  ACK_OP: 'ack:op',
  ERR_OP: 'err:op',

  // Room management
  JOIN_PLAYLISTS: 'join:playlists',
  LEAVE_PLAYLISTS: 'leave:playlists',
  JOIN_PLAYLIST: 'join:playlist',
  LEAVE_PLAYLIST: 'leave:playlist',
  JOIN_NFC: 'join:nfc',
  SYNC_REQUEST: 'sync:request',
  ACK_JOIN: 'ack:join',
  ACK_LEAVE: 'ack:leave',
  SYNC_COMPLETE: 'sync:complete',
  SYNC_ERROR: 'sync:error',

  // NFC events
  NFC_STATUS: 'nfc_status',
  NFC_ASSOCIATION_STATE: 'nfc_association_state',

  // YouTube events
  YOUTUBE_PROGRESS: 'youtube:progress',
  YOUTUBE_COMPLETE: 'youtube:complete',
  YOUTUBE_ERROR: 'youtube:error',
  
  // Health monitoring (implemented)
  PONG: 'client_pong'
} as const
