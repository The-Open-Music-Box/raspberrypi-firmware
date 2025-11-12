/**
 * Types for the audio file management system
 *
 * IMPORTANT: Track and Playlist types are imported from @/types/index.ts
 * which uses ONLY generated types from OpenAPI Contract v4.0.0.
 * DO NOT define custom Track or Playlist interfaces here.
 */

/**
 * File status options that define the current state of a file
 */
export type FileStatus = 'pending' | 'processing' | 'ready' | 'error';

/**
 * Enum-like object for file status constants
 */
export const FILE_STATUS = {
  PENDING: 'pending' as FileStatus,
  IN_PROGRESS: 'processing' as FileStatus,
  READY: 'ready' as FileStatus,
  ERROR: 'error' as FileStatus,
  ASSOCIATED: 'ready' as FileStatus,
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
 * Hook interface for event handling
 */
export interface Hook {
  id: string;
  type: 'hook';
  idtagnfc: string;
  path: string;
  created_at: string;
}