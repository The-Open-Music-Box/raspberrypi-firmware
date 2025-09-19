/**
 * Types for the audio file management system
 */

/**
 * File status options that define the current state of a file
 */
export type FileStatus = 'pending' | 'processing' | 'ready' | 'error';

/**
 * Enum-like object for backward compatibility
 */
export const FILE_STATUS = {
  PENDING: 'pending' as FileStatus,
  IN_PROGRESS: 'processing' as FileStatus,
  READY: 'ready' as FileStatus,
  ERROR: 'error' as FileStatus,
  ASSOCIATED: 'ready' as FileStatus, // Adding missing constant
};

/**
 * CSS classes for different file statuses
 */
export const STATUS_CLASSES: Record<FileStatus, string> = {
  pending: 'bg-warning-light text-warning',
  processing: 'bg-info-light text-info',
  ready: 'bg-success-light text-success',
  error: 'bg-error-light text-error',
};

/**
 * Basic content interface that all content types extend
 */
export interface BaseContent {
  id: string;
  type: string;
}

/**
 * Represents a track in a playlist
 * UNIFIED INTERFACE - matches contracts.ts exactly
 */
export interface Track {
  id: string;                    // Required
  title: string;
  filename: string;
  duration_ms: number;           // Unified to milliseconds everywhere
  file_path: string;
  file_hash?: string;
  file_size?: number;
  
  // Metadata fields
  artist?: string;
  album?: string;
  track_number?: number;         // Primary field name (unified)
  
  // Statistics
  play_count: number;
  
  // Timestamps
  created_at: string;            // ISO8601 format
  updated_at?: string;           // ISO8601 format
  
  // State synchronization
  server_seq: number;

  // Legacy compatibility fields (for migration only)
  number?: number;               // DEPRECATED: use track_number instead
  duration?: number;             // DEPRECATED: use duration_ms instead
}

/**
 * Represents a playlist containing multiple tracks
 */
export interface PlayList extends BaseContent {
  type: 'playlist';
  title: string;
  description?: string;
  last_played: number; // Unix timestamp in milliseconds
  tracks: Track[];
  track_count?: number; // Add track_count field for unified store compatibility
  created_at?: string;
  nfc_tag_id?: string; // NFC tag association (optionnel)
}

/**
 * Legacy playlist format for backward compatibility
 */
export interface LegacyPlayList {
  id: string;
  title: string;
  description?: string;
  tracks: Track[];
  lastPlayed?: Date;
}

/**
 * Basic audio file properties
 */
export interface AudioFile {
  id: string;
  name: string;
  status: FileStatus;
  size: number;
  type: string;
}

/**
 * Legacy audio file format for backward compatibility
 */
export interface LegacyAudioFile extends AudioFile {
  path: string;
  uploaded: string;
  metadata?: Record<string, unknown>; // Using unknown instead of any
}

/**
 * Hook interface for event handling
 */
export interface Hook extends BaseContent {
  type: 'hook';
  idtagnfc: string;
  path: string;
  created_at: string;
}

/**
 * Convert a modern playlist to legacy format
 * @param playlist - Modern playlist format
 * @returns Legacy playlist format
 */
export function playlistToLegacy(playlist: PlayList): LegacyPlayList {
  return {
    id: playlist.id,
    title: playlist.title,
    description: playlist.description,
    tracks: playlist.tracks,
    lastPlayed: playlist.last_played ? new Date(playlist.last_played * 1000) : undefined
  };
}