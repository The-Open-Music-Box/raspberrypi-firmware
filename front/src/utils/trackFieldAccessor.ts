/**
 * Track Field Accessor Utilities
 * 
 * Centralized utilities for accessing track fields safely during migration.
 * Provides fallback logic for legacy field names.
 */

import type { Track } from '@/components/files/types'

/**
 * Get track number with fallback logic
 * Priority: track_number > number > 0
 */
export function getTrackNumber(track: Track): number {
  if (!track) return 0
  return track.track_number ?? track.number ?? 0
}

/**
 * Get track duration in milliseconds with fallback logic
 * Priority: duration_ms > duration * 1000 > 0
 */
export function getTrackDurationMs(track: Track): number {
  if (!track) return 0

  if (track.duration_ms !== undefined) {
    return track.duration_ms
  }

  // Legacy fallback - duration in seconds, convert to ms
  if (track.duration !== undefined) {
    return track.duration * 1000
  }

  return 0
}

/**
 * Get track duration in seconds with fallback logic
 * Priority: duration_ms / 1000 > duration > 0
 */
export function getTrackDurationSeconds(track: Track): number {
  if (!track) return 0

  if (track.duration_ms !== undefined) {
    return track.duration_ms / 1000
  }

  // Legacy fallback
  if (track.duration !== undefined) {
    return track.duration
  }

  return 0
}

/**
 * Create a normalized track object with unified field names
 * Converts legacy fields to new standardized format
 */
export function normalizeTrack(track: Track): Track {
  if (!track) return track

  return {
    ...track,
    track_number: getTrackNumber(track),
    duration_ms: getTrackDurationMs(track),
    // Remove legacy fields in normalized version
    number: undefined,
    duration: undefined
  }
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
 */
export function hasValidTrackNumber(track: Track): boolean {
  const trackNumber = getTrackNumber(track)
  return trackNumber > 0
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
  
  // Check for duplicate track numbers
  const trackNumbers = tracks.map(getTrackNumber)
  const duplicates = trackNumbers.filter((num, index) => trackNumbers.indexOf(num) !== index)
  if (duplicates.length > 0) {
    errors.push(`Duplicate track numbers found: ${[...new Set(duplicates)].join(', ')}`)
  }
  
  // Check for invalid track numbers
  const invalidTracks = tracks.filter(track => !hasValidTrackNumber(track))
  if (invalidTracks.length > 0) {
    errors.push(`${invalidTracks.length} tracks have invalid track numbers`)
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
 * Batch update track numbers efficiently
 */
export function batchUpdateTrackNumbers(tracks: Track[], newOrder: number[]): Track[] {
  if (tracks.length !== newOrder.length) {
    throw new Error(`Track count mismatch: ${tracks.length} tracks vs ${newOrder.length} positions`)
  }
  
  return tracks.map((track, index) => {
    const newPosition = index + 1
    return {
      ...track,
      track_number: newPosition,
      // Handle legacy field
      number: undefined
    }
  })
}