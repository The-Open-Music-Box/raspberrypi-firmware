/**
 * Unified Data Contracts for TheOpenMusicBox
 * 
 * Updated to match the refactored backend standardized response formats.
 * All contracts now align with the unified data models and response structures.
 */

// Standardized response wrapper (all API responses use this)
export interface ApiResponse<T = any> {
  status: 'success' | 'error';
  message: string;
  data?: T;
  timestamp: number;
  server_seq?: number;
}

// Error response structure
export interface ApiError {
  status: 'error';
  message: string;
  error_type: 'validation_error' | 'not_found' | 'permission_denied' | 'rate_limit_exceeded' | 'service_unavailable' | 'internal_error' | 'conflict' | 'bad_request';
  details?: Record<string, any>;
  timestamp: number;
  request_id: string;
}

// Paginated response structure
export interface PaginatedData<T> {
  items: T[];
  page: number;
  limit: number;
  total: number;
  total_pages: number;
}

// Unified Track model (resolves all inconsistencies)
export interface Track {
  id: string;                    // Now required
  title: string;
  filename: string;
  duration_ms: number;           // Unified to milliseconds everywhere
  file_path: string;
  file_hash?: string;
  file_size?: number;
  
  // Metadata fields
  artist?: string;
  album?: string;
  track_number?: number;         // Renamed from 'number' for clarity
  
  // Statistics
  play_count: number;
  
  // Timestamps (can be null from backend)
  created_at: string | null;     // ISO8601 format or null
  updated_at?: string | null;    // ISO8601 format or null
  
  // State synchronization
  server_seq: number;
}

// Unified Playlist model (resolves name/title confusion)
export interface Playlist {
  id: string;
  title: string;                 // Resolved to 'title' everywhere (no more name/title confusion)
  description: string;           // Now required with default empty string
  
  // Type identifier
  type: 'playlist';

  // NFC integration
  nfc_tag_id?: string;

  // Tracks
  tracks: Track[];
  track_count: number;           // Always matches tracks.length

  // Playback state
  last_played: number;           // Unix timestamp in milliseconds
  
  // Timestamps (can be null from backend)
  created_at: string | null;     // ISO8601 format or null
  updated_at?: string | null;    // ISO8601 format or null
  
  // State synchronization
  server_seq: number;
  playlist_seq: number;
}

// Lightweight playlist model for list views
export interface PlaylistLite {
  id: string;
  title: string;
  description: string;
  nfc_tag_id?: string;
  track_count: number;
  created_at: string;
  updated_at?: string;
  server_seq: number;
}

// Playback state enum (matches backend)
export enum PlaybackState {
  PLAYING = 'playing',
  PAUSED = 'paused',
  STOPPED = 'stopped',
  LOADING = 'loading',
  ERROR = 'error'
}

// Unified PlayerState model (eliminates all building inconsistencies)
export interface PlayerState {
  // Playback state
  is_playing: boolean;
  state: PlaybackState;          // New detailed state field
  
  // Current playlist/track
  active_playlist_id?: string;
  active_playlist_title?: string;
  active_track_id?: string;
  active_track?: Track;          // Full track object, not partial
  
  // Playback position
  position_ms: number;
  duration_ms: number;           // Now required, not optional
  
  // Playlist navigation  
  track_index: number;           // Now required
  track_count: number;           // Now required
  can_prev: boolean;
  can_next: boolean;
  
  // Audio control
  volume: number;                // Now required (0-100)
  muted: boolean;                // New field
  
  // State synchronization
  server_seq: number;
  
  // Optional error information
  error_message?: string;
}

// Standardized Socket.IO event envelope (eliminates format chaos)
export interface StateEventEnvelope<T = any> {
  event_type: string;            // Canonical event type (state:*, join:*, etc.)
  server_seq: number;
  data: T;
  timestamp: number;
  event_id: string;
  
  // Optional fields for specific event types
  playlist_id?: string;
  playlist_seq?: number;
}

// Legacy StateEvent for backward compatibility
export type StateEvent<T = any> = StateEventEnvelope<T> | {
  data: T;
  server_seq: number;
  type?: 'snapshot' | 'update';
};

// Standardized operation acknowledgment (replaces mixed ack formats)
export interface OperationAck {
  client_op_id: string;
  success: boolean;
  server_seq: number;
  data?: any;
  message?: string;              // Renamed from 'error' for consistency
}

// Enhanced upload progress model
export interface UploadProgress {
  playlist_id: string;
  session_id: string;
  chunk_index?: number;
  progress: number;              // 0-100 percentage
  complete: boolean;
  filename?: string;
  error?: string;
}

// Upload status model
export interface UploadStatus {
  session_id: string;
  filename: string;
  file_size: number;
  bytes_uploaded: number;
  progress_percent: number;
  chunks_total: number;
  chunks_uploaded: number;
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'error';
  error_message?: string;
  created_at: string;
  updated_at: string;
}

// Track progress model
export interface TrackProgress {
  position_ms: number;
  duration_ms: number;
  is_playing: boolean;
  active_track_id?: string;
  server_seq: number;
  timestamp: number;
}

// Volume payload model
export interface VolumePayload {
  volume: number;                // 0-100
  muted: boolean;
  server_seq: number;
}

// NFC association model
export interface NFCAssociation {
  tag_id: string;
  playlist_id: string;
  playlist_title: string;
  created_at: string;
}

// YouTube progress model  
export interface YouTubeProgress {
  task_id: string;
  status: 'pending' | 'downloading' | 'processing' | 'completed' | 'error';
  progress_percent: number;
  current_step: string;
  estimated_time_remaining?: number;
  error_message?: string;
  result?: {
    track: Track;
    playlist_id: string;
  };
}

// YouTube search result model
export interface YouTubeResult {
  id: string;
  title: string;
  duration_ms: number;
  thumbnail_url: string;
  channel: string;
  view_count: number;
}

/**
 * Paginated Playlists Index Types
 * These types support the optimized paginated index feature.
 */

export interface PlaylistsIndexItem {
  id: string;
  title: string;
  summary: {
    track_count: number;
    total_duration_ms: number;
    updated_at: string; // ISO8601 timestamp
  };
  nfc_tag_id?: string | null;
  cover_thumb_url?: string | null;
  server_seq: number;
  playlist_seq: number;
}

export interface PlaylistsIndexResponse {
  items: PlaylistsIndexItem[];
  next_cursor?: string | null;
  total_estimate?: number;
  server_seq: number;
}

export interface PlaylistsIndexUpdateEvent {
  event_type: 'state:playlists_index_update';
  server_seq: number;
  ops: PlaylistsIndexOperation[];
  sort: string;
  timestamp: number;
  event_id: string;
}

export interface PlaylistsIndexOperation {
  type: 'upsert' | 'delete';
  item?: PlaylistsIndexItem; // Present for upsert operations
  id?: string; // Present for delete operations
}
