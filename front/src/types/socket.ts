/**
 * Socket Event Type Definitions
 * Provides type safety for all socket.io events used in the application
 */

export interface SocketProgressData {
  session_id: string;
  progress: number;
  chunk_index?: number;
  file_name?: string;
}

export interface SocketCompleteData {
  session_id: string;
  file_id?: string;
  filename: string;
  playlist_id?: string;
}

export interface SocketErrorData {
  session_id: string;
  error: string;
  code?: string;
  context?: string;
}

export interface SocketUploadStatusData {
  session_id: string;
  status: 'pending' | 'uploading' | 'processing' | 'complete' | 'error';
  progress?: number;
  error?: string;
}

/**
 * NFC Association State Data
 */
export interface NfcAssociationStateData {
  state: 'activated' | 'waiting' | 'success' | 'duplicate' | 'timeout' | 'cancelled' | 'error';
  playlist_id?: string;
  tag_id?: string;
  message?: string;
  expires_at?: number;
  existing_playlist?: { id: string; title: string };
}

/**
 * NFC Tag Duplicate Data
 */
export interface NfcTagDuplicateData {
  tag_id: string;
  existing_playlist: { id: string; title: string };
  current_playlist_id: string;
}

/**
 * Server-Authoritative State Events
 */
export interface PlaylistStateData {
  id: string;
  title: string;
  tracks?: Array<{
    track_number: number;  // 1-based position per OpenAPI v6.0.1
    title: string;
    filename: string;
    /** @deprecated Use duration_ms instead */
    duration?: number;
    /** Duration in milliseconds (preferred over duration) */
    duration_ms?: number;
  }>;
  nfc_tag_id?: string;
  server_seq?: number;
}

export interface PlayerStateData {
  is_playing: boolean;
  active_playlist_id?: string;
  /** @deprecated Will be renamed to active_track_filename in v7.0.0 */
  active_track_id?: string;
  /** Track number (1-based) in current playlist */
  active_track_number?: number;
  position_ms: number;
  /** Duration in milliseconds */
  duration_ms?: number;
  can_prev: boolean;
  can_next: boolean;
  server_seq: number;
}

export interface TrackProgressData {
  position_ms: number;
  duration_ms: number;
  /** Track filename (renamed from track_id in v6.0.0) */
  track_filename?: string;
  track_number?: number;
  playlist_id?: string;
}

/**
 * Socket event handler types
 */
export type SocketProgressHandler = (data: SocketProgressData) => void;
export type SocketCompleteHandler = (data: SocketCompleteData) => void;
export type SocketErrorHandler = (data: SocketErrorData) => void;
export type SocketStatusHandler = (data: SocketUploadStatusData) => void;

/**
 * Generic socket event handler
 */
export type SocketEventHandler<T = unknown> = (data: T) => void;

/**
 * Type-safe socket event handler that accepts unknown data and casts it
 */
export function createTypedSocketHandler<T>(handler: (data: T) => void): SocketEventHandler {
  return (data: unknown) => {
    handler(data as T);
  };
}
