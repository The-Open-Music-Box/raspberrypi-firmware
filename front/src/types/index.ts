/**
 * Frontend Types - Central Export Point
 *
 * Uses ONLY generated types from OpenAPI Contract v4.0.0
 * Zero legacy code - 100% contract-driven development
 */

// Import generated types from contracts v4.0.0
import type { components } from '../../../contracts/releases/4.0.0-82d5310/typescript/api-types';

// Export core data types from OpenAPI schema
export type Track = components['schemas']['Track'];
export type PlaylistDetailed = components['schemas']['PlaylistDetailed'];
export type PlaylistSummary = components['schemas']['PlaylistSummary'];
export type PlayerState = components['schemas']['PlayerState'];

// Aliases for cleaner usage
export type Playlist = PlaylistDetailed;
export type PlaylistLite = PlaylistSummary;

// API response types
export type ApiResponse<T = any> = {
  status: 'success' | 'error';
  message: string;
  data?: T;
  timestamp: number;
  request_id?: string;
  server_seq?: number;
  client_op_id?: string;
  error_type?: string;
  details?: any;
};

export type ApiError = {
  status: 'error';
  message: string;
  error_type?: string;
  details?: any;
  timestamp: number;
};

export type PaginatedData<T> = {
  items: T[];
  page: number;
  limit: number;
  total: number;
  total_pages: number;
};

// Socket.IO event types
export type StateEventEnvelope<T = any> = {
  event_type: string;
  server_seq: number;
  data: T;
  timestamp: number;
  event_id: string;
  playlist_id?: string | null;
  track_id?: string | null;
};

export type OperationAck = {
  client_op_id: string;
  success: boolean;
  data?: any;
  server_seq: number;
};

// Progress tracking types
export type UploadProgress = {
  playlist_id: string;
  session_id: string;
  progress: number;
  chunk_index?: number;
  file_name?: string;
  complete?: boolean;
};

export type UploadStatus = 'pending' | 'uploading' | 'complete' | 'error';

export type TrackProgress = {
  position_ms: number;
  track_id?: string | null;
  is_playing: boolean;
  duration_ms?: number | null;
};

export type VolumePayload = {
  volume: number;
};

// YouTube integration types
export type YouTubeProgress = {
  task_id: string;
  status: string;
  progress_percent?: number;
  current_step?: string;
};

export type YouTubeResult = {
  task_id: string;
  track: Track;
  playlist_id: string;
};

// NFC types
export type NFCAssociation = {
  assoc_id?: string;
  state: 'activated' | 'waiting' | 'success' | 'duplicate' | 'timeout' | 'cancelled' | 'error';
  playlist_id?: string | null;
  tag_id?: string | null;
  message?: string | null;
  expires_at?: number | null;
  existing_playlist?: {
    id: string;
    title: string;
  } | null;
  server_seq: number;
};

// System info types
export type SystemInfo = {
  version: string;
  platform: string;
  uptime: number;
};

export type HealthStatus = {
  status: 'healthy' | 'degraded' | 'unhealthy';
  checks: Record<string, boolean>;
};

// Playback state enum
export enum PlaybackState {
  PLAYING = 'playing',
  PAUSED = 'paused',
  STOPPED = 'stopped'
}

// Playlists index types (for optimized list view)
export type PlaylistsIndexItem = {
  id: string;
  title: string;
  track_count: number;
  nfc_tag_id?: string | null;
  server_seq: number;
};

export type PlaylistsIndexResponse = {
  playlists: PlaylistsIndexItem[];
  server_seq: number;
};

export type PlaylistsIndexUpdateEvent = {
  operation: PlaylistsIndexOperation;
  playlist: PlaylistsIndexItem;
  server_seq: number;
};

export type PlaylistsIndexOperation = 'created' | 'updated' | 'deleted';

// Re-export app-specific types
export * from './socket';
export * from './upload';
// Note: './errors' exports UploadError which conflicts with './upload'
// Import errors types explicitly if needed, or use from './errors' directly
