/**
 * Track Field Accessor Utilities
 *
 * Centralized utilities for accessing track fields safely.
 * Uses ONLY OpenAPI Contract v4.1.0 types.
 */

import type { Track } from '@/types'
import { logger } from './logger'

/**
 * Get track number from contract v4.1.0
 *
 * IMPORTANT: No longer uses silent fallback to 0.
 * Logs error and throws if 'track_number' field is missing to prevent
 * contract violations from causing silent data corruption (issue #71).
 *
 * Supports backward compatibility with legacy 'number' field during migration.
 */
export function getTrackNumber(track: Track): number {
  if (!track) {
    logger.error('getTrackNumber called with null/undefined track', {}, 'trackFieldAccessor')
    throw new Error('Track is null or undefined')
  }

  // Check for 'track_number' field (v4.1.0 contract), fallback to 'number' for backward compat
  const trackNumber = track.track_number ?? (track as any).number

  if (trackNumber === undefined || trackNumber === null) {
    const trackKeys = Object.keys(track)
    logger.error(
      'CONTRACT VIOLATION: Track missing required "track_number" field',
      {
        trackId: (track as any).id,
        trackTitle: track.title,
        trackFilename: track.filename,
        availableFields: trackKeys,
        trackData: track
      },
      'trackFieldAccessor'
    )

    throw new Error(
      `Track missing required 'track_number' field. ` +
      `Available fields: ${trackKeys.join(', ')}. ` +
      `This indicates a backend serialization bug (see issue #71).`
    )
  }

  // Validate track_number is actually a number type
  if (typeof trackNumber !== 'number') {
    logger.error(
      'CONTRACT VIOLATION: Track "track_number" field has wrong type',
      {
        trackNumber: trackNumber,
        actualType: typeof trackNumber,
        trackId: (track as any).id
      },
      'trackFieldAccessor'
    )

    throw new Error(
      `Track 'track_number' field has wrong type. ` +
      `Expected: number, Got: ${typeof trackNumber}. ` +
      `Value: ${trackNumber}`
    )
  }

  // Validate track_number is positive
  if (trackNumber <= 0) {
    logger.warn(
      'Track has invalid track_number (<=0)',
      { trackNumber: trackNumber, trackId: (track as any).id },
      'trackFieldAccessor'
    )
  }

  return trackNumber
}

/**
 * Get track duration in milliseconds from contract v4.1.0
 * Prefers duration_ms, falls back to duration * 1000 (deprecated field)
 */
export function getTrackDurationMs(track: Track): number {
  if (!track) return 0
  // Prefer duration_ms (milliseconds)
  if (track.duration_ms != null) return track.duration_ms
  // Fallback to duration (seconds, deprecated)
  if (track.duration != null) return track.duration * 1000
  return 0
}

/**
 * Get track duration in seconds from contract v4.1.0
 */
export function getTrackDurationSeconds(track: Track): number {
  if (!track) return 0
  // Prefer duration_ms (convert to seconds)
  if (track.duration_ms != null) return track.duration_ms / 1000
  // Fallback to duration (seconds, deprecated)
  if (track.duration != null) return track.duration
  return 0
}

/**
 * Ensure track has all required fields from contract v4.1.0
 */
export function normalizeTrack(track: Track): Track {
  if (!track) return track
  // Contract v4.1.0 - Track uses 'track_number' field
  return track
}

/**
 * Format track duration for display (MM:SS or H:MM:SS)
 */
export function formatTrackDuration(track: Track): string {
  const seconds = getTrackDurationSeconds(track)
  
  if (isNaN(seconds) || seconds <= 0) {
    return '00:00'
  }
  
  const totalSeconds = Math.floor(seconds)
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const remainingSeconds = totalSeconds % 60
  
  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`
  }
  
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`
}

/**
 * Find track in array by track number (with fallback logic)
 */
export function findTrackByNumber(tracks: Track[], trackNumber: number): Track | undefined {
  return tracks.find(track => getTrackNumber(track) === trackNumber)
}

/**
 * Sort tracks by track number (with fallback logic)
 */
export function sortTracksByNumber(tracks: Track[]): Track[] {
  return tracks.slice().sort((a, b) => getTrackNumber(a) - getTrackNumber(b))
}

/**
 * Validation: Check if track has valid track number
 * Returns false if track is invalid or missing number field (catches errors)
 */
export function hasValidTrackNumber(track: Track): boolean {
  try {
    const trackNumber = getTrackNumber(track)
    return trackNumber > 0
  } catch (error) {
    // Track is invalid (null, missing number field, etc.)
    return false
  }
}

/**
 * Validation: Check if track has valid duration
 */
export function hasValidDuration(track: Track): boolean {
  const duration = getTrackDurationMs(track)
  return duration > 0
}

/**
 * Filter tracks by track numbers - CENTRALIZED LOGIC
 * Removes tracks matching the provided track numbers
 */
export function filterTracksByNumbers(tracks: Track[], trackNumbersToRemove: number[]): Track[] {
  return tracks.filter(track => !trackNumbersToRemove.includes(getTrackNumber(track)))
}

/**
 * Filter tracks excluding specific track number - CENTRALIZED LOGIC
 * Removes single track matching the provided track number
 */
export function filterTrackByNumber(tracks: Track[], trackNumberToRemove: number): Track[] {
  return tracks.filter(track => getTrackNumber(track) !== trackNumberToRemove)
}

/**
 * Find track by track number with error handling - CENTRALIZED LOGIC
 */
export function findTrackByNumberSafe(tracks: Track[], trackNumber: number): { track: Track | null; error: string | null } {
  try {
    const track = tracks.find(track => getTrackNumber(track) === trackNumber) || null
    return { track, error: null }
  } catch (error) {
    return { track: null, error: `Error finding track ${trackNumber}: ${error}` }
  }
}

/**
 * Validate track array for drag operations
 */
export function validateTracksForDrag(tracks: Track[]): { valid: boolean; errors: string[] } {
  const errors: string[] = []

  if (!Array.isArray(tracks)) {
    errors.push('Tracks must be an array')
    return { valid: false, errors }
  }

  // Check for invalid track numbers (must be done first to prevent getTrackNumber from throwing)
  const invalidTracks = tracks.filter(track => !hasValidTrackNumber(track))
  if (invalidTracks.length > 0) {
    errors.push(`${invalidTracks.length} tracks have invalid track numbers`)
  }

  // Only check duplicates for valid tracks
  const validTracks = tracks.filter(track => hasValidTrackNumber(track))
  const trackNumbers = validTracks.map(getTrackNumber) // Safe now - only valid tracks
  const duplicates = trackNumbers.filter((num, index) => trackNumbers.indexOf(num) !== index)
  if (duplicates.length > 0) {
    errors.push(`Duplicate track numbers found: ${[...new Set(duplicates)].join(', ')}`)
  }

  return { valid: errors.length === 0, errors }
}

/**
 * Create track index map for O(1) lookups - PERFORMANCE OPTIMIZATION
 */
export function createTrackIndexMap(tracks: Track[]): Map<number, Track> {
  const trackMap = new Map<number, Track>()
  tracks.forEach(track => {
    const trackNumber = getTrackNumber(track)
    trackMap.set(trackNumber, track)
  })
  return trackMap
}

/**
 * Batch update track numbers efficiently (v4.1.0 uses 'track_number' field)
 */
export function batchUpdateTrackNumbers(tracks: Track[], newOrder: number[]): Track[] {
  if (tracks.length !== newOrder.length) {
    throw new Error(`Track count mismatch: ${tracks.length} tracks vs ${newOrder.length} positions`)
  }

  return tracks.map((track, index) => ({
    ...track,
    track_number: index + 1
  }))
}