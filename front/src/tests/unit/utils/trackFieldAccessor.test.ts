/**
 * Unit tests for trackFieldAccessor.ts
 *
 * Tests the centralized track field accessor utilities including:
 * - Track field access with legacy fallback logic
 * - Track normalization and standardization
 * - Duration formatting and conversion
 * - Track array operations and validation
 * - Performance optimization utilities
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  getTrackNumber,
  getTrackDurationMs,
  getTrackDurationSeconds,
  normalizeTrack,
  formatTrackDuration,
  findTrackByNumber,
  sortTracksByNumber,
  hasValidTrackNumber,
  hasValidDuration,
  filterTracksByNumbers,
  filterTrackByNumber,
  findTrackByNumberSafe,
  validateTracksForDrag,
  createTrackIndexMap,
  batchUpdateTrackNumbers
} from '@/utils/trackFieldAccessor'

// Mock track interface for testing
interface MockTrack {
  id?: string
  title?: string
  artist?: string
  track_number?: number
  number?: number
  duration_ms?: number
  duration?: number
  [key: string]: any
}

// Mock the Track type import
vi.mock('@/components/files/types', () => ({
  Track: {}
}))

describe('trackFieldAccessor', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('getTrackNumber', () => {
    it('should prioritize track_number over number', () => {
      const track: MockTrack = {
        track_number: 5,
        number: 3
      }

      expect(getTrackNumber(track as any))
        .toBe(5)
    })

    it('should fallback to number when track_number is undefined', () => {
      const track: MockTrack = {
        number: 7
      }

      expect(getTrackNumber(track as any))
        .toBe(7)
    })

    it('should return 0 when both fields are undefined', () => {
      const track: MockTrack = {
        title: 'Test Track'
      }

      expect(getTrackNumber(track as any))
        .toBe(0)
    })

    it('should handle null values correctly', () => {
      const track: MockTrack = {
        track_number: null as any,
        number: 4
      }

      expect(getTrackNumber(track as any))
        .toBe(4)
    })

    it('should handle zero values correctly', () => {
      const track: MockTrack = {
        track_number: 0,
        number: 5
      }

      expect(getTrackNumber(track as any))
        .toBe(0)
    })

    it('should handle invalid track objects', () => {
      expect(getTrackNumber(null as any))
        .toBe(0)
      expect(getTrackNumber(undefined as any))
        .toBe(0)
      expect(getTrackNumber({} as any))
        .toBe(0)
    })
  })

  describe('getTrackDurationMs', () => {
    it('should prioritize duration_ms', () => {
      const track: MockTrack = {
        duration_ms: 180000,
        duration: 120
      }

      expect(getTrackDurationMs(track as any))
        .toBe(180000)
    })

    it('should convert duration seconds to milliseconds when duration_ms is undefined', () => {
      const track: MockTrack = {
        duration: 150
      }

      expect(getTrackDurationMs(track as any))
        .toBe(150000)
    })

    it('should return 0 when both fields are undefined', () => {
      const track: MockTrack = {
        title: 'Test Track'
      }

      expect(getTrackDurationMs(track as any))
        .toBe(0)
    })

    it('should handle zero duration correctly', () => {
      const track: MockTrack = {
        duration_ms: 0,
        duration: 120
      }

      expect(getTrackDurationMs(track as any))
        .toBe(0)
    })

    it('should handle decimal durations correctly', () => {
      const track: MockTrack = {
        duration: 123.456
      }

      expect(getTrackDurationMs(track as any))
        .toBe(123456)
    })

    it('should handle invalid track objects', () => {
      expect(getTrackDurationMs(null as any))
        .toBe(0)
      expect(getTrackDurationMs(undefined as any))
        .toBe(0)
      expect(getTrackDurationMs({} as any))
        .toBe(0)
    })
  })

  describe('getTrackDurationSeconds', () => {
    it('should convert duration_ms to seconds', () => {
      const track: MockTrack = {
        duration_ms: 180000,
        duration: 120
      }

      expect(getTrackDurationSeconds(track as any))
        .toBe(180)
    })

    it('should use duration directly when duration_ms is undefined', () => {
      const track: MockTrack = {
        duration: 150
      }

      expect(getTrackDurationSeconds(track as any))
        .toBe(150)
    })

    it('should return 0 when both fields are undefined', () => {
      const track: MockTrack = {
        title: 'Test Track'
      }

      expect(getTrackDurationSeconds(track as any))
        .toBe(0)
    })

    it('should handle fractional milliseconds correctly', () => {
      const track: MockTrack = {
        duration_ms: 123456
      }

      expect(getTrackDurationSeconds(track as any))
        .toBe(123.456)
    })
  })

  describe('normalizeTrack', () => {
    it('should normalize track with all fields', () => {
      const track: MockTrack = {
        id: '1',
        title: 'Test Track',
        track_number: 5,
        number: 3,
        duration_ms: 180000,
        duration: 120
      }

      const normalized = normalizeTrack(track as any)

      expect(normalized.track_number)
        .toBe(5)
      expect(normalized.duration_ms)
        .toBe(180000)
      expect(normalized.number)
        .toBeUndefined()
      expect(normalized.duration)
        .toBeUndefined()
      expect(normalized.id)
        .toBe('1')
      expect(normalized.title)
        .toBe('Test Track')
    })

    it('should normalize track with legacy fields only', () => {
      const track: MockTrack = {
        id: '2',
        title: 'Legacy Track',
        number: 7,
        duration: 200
      }

      const normalized = normalizeTrack(track as any)

      expect(normalized.track_number)
        .toBe(7)
      expect(normalized.duration_ms)
        .toBe(200000)
      expect(normalized.number)
        .toBeUndefined()
      expect(normalized.duration)
        .toBeUndefined()
    })

    it('should normalize track with missing fields', () => {
      const track: MockTrack = {
        id: '3',
        title: 'Minimal Track'
      }

      const normalized = normalizeTrack(track as any)

      expect(normalized.track_number)
        .toBe(0)
      expect(normalized.duration_ms)
        .toBe(0)
      expect(normalized.number)
        .toBeUndefined()
      expect(normalized.duration)
        .toBeUndefined()
    })

    it('should preserve other track properties', () => {
      const track: MockTrack = {
        id: '4',
        title: 'Full Track',
        artist: 'Test Artist',
        album: 'Test Album',
        genre: 'Test Genre',
        track_number: 1,
        duration_ms: 240000,
        custom_field: 'custom_value'
      }

      const normalized = normalizeTrack(track as any)

      expect(normalized.id)
        .toBe('4')
      expect(normalized.title)
        .toBe('Full Track')
      expect(normalized.artist)
        .toBe('Test Artist')
      expect(normalized.album)
        .toBe('Test Album')
      expect(normalized.genre)
        .toBe('Test Genre')
      expect(normalized.custom_field)
        .toBe('custom_value')
    })
  })

  describe('formatTrackDuration', () => {
    it('should format duration in MM:SS format for short tracks', () => {
      const track: MockTrack = { duration_ms: 180000 } // 3 minutes

      expect(formatTrackDuration(track as any))
        .toBe('3:00')
    })

    it('should format duration in H:MM:SS format for long tracks', () => {
      const track: MockTrack = { duration_ms: 3661000 } // 1 hour, 1 minute, 1 second

      expect(formatTrackDuration(track as any))
        .toBe('1:01:01')
    })

    it('should handle tracks with seconds', () => {
      const track: MockTrack = { duration_ms: 125000 } // 2:05

      expect(formatTrackDuration(track as any))
        .toBe('2:05')
    })

    it('should pad single digit minutes and seconds', () => {
      const track: MockTrack = { duration_ms: 65000 } // 1:05

      expect(formatTrackDuration(track as any))
        .toBe('1:05')
    })

    it('should handle legacy duration field', () => {
      const track: MockTrack = { duration: 195 } // 3:15

      expect(formatTrackDuration(track as any))
        .toBe('3:15')
    })

    it('should return 00:00 for invalid durations', () => {
      const invalidTracks = [
        { duration_ms: 0 },
        { duration_ms: -1000 },
        { duration_ms: NaN },
        { duration_ms: null }
      ]

      invalidTracks.forEach(track => {
        expect(formatTrackDuration(track as any))
          .toBe('00:00')
      })
    })

    it('should handle very long durations', () => {
      const track: MockTrack = { duration_ms: 7323000 } // 2:02:03

      expect(formatTrackDuration(track as any))
        .toBe('2:02:03')
    })

    it('should handle fractional seconds', () => {
      const track: MockTrack = { duration_ms: 123456 } // 2:03.456 -> 2:03

      expect(formatTrackDuration(track as any))
        .toBe('2:03')
    })
  })

  describe('findTrackByNumber', () => {
    const tracks: MockTrack[] = [
      { id: '1', track_number: 1, title: 'Track 1' },
      { id: '2', track_number: 2, title: 'Track 2' },
      { id: '3', number: 3, title: 'Track 3' }, // Legacy field
      { id: '4', track_number: 5, title: 'Track 5' }
    ]

    it('should find track by track number', () => {
      const found = findTrackByNumber(tracks as any, 2)

      expect(found)
        .toBeDefined()
      expect(found?.id)
        .toBe('2')
    })

    it('should find track using legacy number field', () => {
      const found = findTrackByNumber(tracks as any, 3)

      expect(found)
        .toBeDefined()
      expect(found?.id)
        .toBe('3')
    })

    it('should return undefined for non-existing track number', () => {
      const found = findTrackByNumber(tracks as any, 99)

      expect(found)
        .toBeUndefined()
    })

    it('should handle empty track array', () => {
      const found = findTrackByNumber([], 1)

      expect(found)
        .toBeUndefined()
    })

    it('should handle tracks with no track numbers', () => {
      const tracksWithoutNumbers = [
        { id: '1', title: 'Track without number' }
      ]

      const found = findTrackByNumber(tracksWithoutNumbers as any, 1)

      expect(found)
        .toBeUndefined()
    })
  })

  describe('sortTracksByNumber', () => {
    it('should sort tracks by track number in ascending order', () => {
      const unsortedTracks: MockTrack[] = [
        { id: '1', track_number: 3, title: 'Track 3' },
        { id: '2', track_number: 1, title: 'Track 1' },
        { id: '3', track_number: 2, title: 'Track 2' }
      ]

      const sorted = sortTracksByNumber(unsortedTracks as any)

      expect(sorted.map(t => t.track_number))
        .toEqual([1, 2, 3])
      expect(sorted.map(t => t.id))
        .toEqual(['2', '3', '1'])
    })

    it('should handle mixed track_number and number fields', () => {
      const tracks: MockTrack[] = [
        { id: '1', number: 3, title: 'Track 3' },
        { id: '2', track_number: 1, title: 'Track 1' },
        { id: '3', track_number: 2, title: 'Track 2' }
      ]

      const sorted = sortTracksByNumber(tracks as any)

      expect(sorted.map(t => getTrackNumber(t as any)))
        .toEqual([1, 2, 3])
    })

    it('should not modify original array', () => {
      const originalTracks: MockTrack[] = [
        { id: '1', track_number: 3 },
        { id: '2', track_number: 1 },
        { id: '3', track_number: 2 }
      ]

      const originalOrder = [...originalTracks]

      const sorted = sortTracksByNumber(originalTracks as any)

      expect(originalTracks)
        .toEqual(originalOrder)
      expect(sorted)
        .not.toBe(originalTracks)
    })

    it('should handle tracks with no track numbers (default to 0)', () => {
      const tracks: MockTrack[] = [
        { id: '1', track_number: 2 },
        { id: '2', title: 'No number' },
        { id: '3', track_number: 1 }
      ]

      const sorted = sortTracksByNumber(tracks as any)

      expect(sorted.map(t => getTrackNumber(t as any)))
        .toEqual([0, 1, 2])
    })

    it('should handle empty array', () => {
      const sorted = sortTracksByNumber([])

      expect(sorted)
        .toEqual([])
    })
  })

  describe('hasValidTrackNumber', () => {
    it('should return true for tracks with valid track numbers', () => {
      const validTracks: MockTrack[] = [
        { track_number: 1 },
        { track_number: 99 },
        { number: 5 },
        { track_number: 1, number: 2 } // track_number takes priority
      ]

      validTracks.forEach(track => {
        expect(hasValidTrackNumber(track as any))
          .toBe(true)
      })
    })

    it('should return false for tracks with invalid track numbers', () => {
      const invalidTracks: MockTrack[] = [
        { track_number: 0 },
        { track_number: -1 },
        { number: 0 },
        { number: -5 },
        { title: 'No track number' },
        {}
      ]

      invalidTracks.forEach(track => {
        expect(hasValidTrackNumber(track as any))
          .toBe(false)
      })
    })
  })

  describe('hasValidDuration', () => {
    it('should return true for tracks with valid durations', () => {
      const validTracks: MockTrack[] = [
        { duration_ms: 1000 },
        { duration_ms: 180000 },
        { duration: 120 },
        { duration_ms: 1, duration: 0 } // duration_ms takes priority
      ]

      validTracks.forEach(track => {
        expect(hasValidDuration(track as any))
          .toBe(true)
      })
    })

    it('should return false for tracks with invalid durations', () => {
      const invalidTracks: MockTrack[] = [
        { duration_ms: 0 },
        { duration_ms: -1000 },
        { duration: 0 },
        { duration: -60 },
        { title: 'No duration' },
        {}
      ]

      invalidTracks.forEach(track => {
        expect(hasValidDuration(track as any))
          .toBe(false)
      })
    })
  })

  describe('filterTracksByNumbers', () => {
    const tracks: MockTrack[] = [
      { id: '1', track_number: 1, title: 'Track 1' },
      { id: '2', track_number: 2, title: 'Track 2' },
      { id: '3', track_number: 3, title: 'Track 3' },
      { id: '4', track_number: 4, title: 'Track 4' }
    ]

    it('should filter out tracks with specified numbers', () => {
      const filtered = filterTracksByNumbers(tracks as any, [2, 4])

      expect(filtered)
        .toHaveLength(2)
      expect(filtered.map(t => t.id))
        .toEqual(['1', '3'])
    })

    it('should handle empty exclusion list', () => {
      const filtered = filterTracksByNumbers(tracks as any, [])

      expect(filtered)
        .toEqual(tracks)
    })

    it('should handle non-existing track numbers', () => {
      const filtered = filterTracksByNumbers(tracks as any, [99, 100])

      expect(filtered)
        .toEqual(tracks)
    })

    it('should handle empty track array', () => {
      const filtered = filterTracksByNumbers([], [1, 2])

      expect(filtered)
        .toEqual([])
    })
  })

  describe('filterTrackByNumber', () => {
    const tracks: MockTrack[] = [
      { id: '1', track_number: 1, title: 'Track 1' },
      { id: '2', track_number: 2, title: 'Track 2' },
      { id: '3', track_number: 3, title: 'Track 3' }
    ]

    it('should filter out single track by number', () => {
      const filtered = filterTrackByNumber(tracks as any, 2)

      expect(filtered)
        .toHaveLength(2)
      expect(filtered.map(t => t.id))
        .toEqual(['1', '3'])
    })

    it('should handle non-existing track number', () => {
      const filtered = filterTrackByNumber(tracks as any, 99)

      expect(filtered)
        .toEqual(tracks)
    })

    it('should handle empty track array', () => {
      const filtered = filterTrackByNumber([], 1)

      expect(filtered)
        .toEqual([])
    })
  })

  describe('findTrackByNumberSafe', () => {
    const tracks: MockTrack[] = [
      { id: '1', track_number: 1, title: 'Track 1' },
      { id: '2', track_number: 2, title: 'Track 2' }
    ]

    it('should find track successfully', () => {
      const result = findTrackByNumberSafe(tracks as any, 1)

      expect(result.track)
        .toBeDefined()
      expect(result.track?.id)
        .toBe('1')
      expect(result.error)
        .toBeNull()
    })

    it('should handle track not found', () => {
      const result = findTrackByNumberSafe(tracks as any, 99)

      expect(result.track)
        .toBeNull()
      expect(result.error)
        .toBeNull()
    })

    it('should handle errors gracefully', () => {
      // Mock an error by passing invalid data that would cause getTrackNumber to throw
      const invalidTracks = null as any

      const result = findTrackByNumberSafe(invalidTracks, 1)

      expect(result.track)
        .toBeNull()
      expect(result.error)
        .toContain('Error finding track 1')
    })
  })

  describe('validateTracksForDrag', () => {
    it('should validate correct track array', () => {
      const tracks: MockTrack[] = [
        { id: '1', track_number: 1, title: 'Track 1' },
        { id: '2', track_number: 2, title: 'Track 2' },
        { id: '3', track_number: 3, title: 'Track 3' }
      ]

      const result = validateTracksForDrag(tracks as any)

      expect(result.valid)
        .toBe(true)
      expect(result.errors)
        .toEqual([])
    })

    it('should detect non-array input', () => {
      const result = validateTracksForDrag(null as any)

      expect(result.valid)
        .toBe(false)
      expect(result.errors)
        .toContain('Tracks must be an array')
    })

    it('should detect duplicate track numbers', () => {
      const tracks: MockTrack[] = [
        { id: '1', track_number: 1, title: 'Track 1' },
        { id: '2', track_number: 2, title: 'Track 2' },
        { id: '3', track_number: 1, title: 'Track 1 duplicate' }
      ]

      const result = validateTracksForDrag(tracks as any)

      expect(result.valid)
        .toBe(false)
      expect(result.errors)
        .toContain('Duplicate track numbers found: 1')
    })

    it('should detect invalid track numbers', () => {
      const tracks: MockTrack[] = [
        { id: '1', track_number: 1, title: 'Track 1' },
        { id: '2', track_number: 0, title: 'Invalid track' },
        { id: '3', title: 'No track number' }
      ]

      const result = validateTracksForDrag(tracks as any)

      expect(result.valid)
        .toBe(false)
      expect(result.errors)
        .toContain('2 tracks have invalid track numbers')
    })

    it('should detect multiple issues', () => {
      const tracks: MockTrack[] = [
        { id: '1', track_number: 1, title: 'Track 1' },
        { id: '2', track_number: 1, title: 'Duplicate' },
        { id: '3', track_number: 0, title: 'Invalid' }
      ]

      const result = validateTracksForDrag(tracks as any)

      expect(result.valid)
        .toBe(false)
      expect(result.errors)
        .toHaveLength(2)
      expect(result.errors)
        .toContain('Duplicate track numbers found: 1')
      expect(result.errors)
        .toContain('1 tracks have invalid track numbers')
    })
  })

  describe('createTrackIndexMap', () => {
    it('should create correct index map', () => {
      const tracks: MockTrack[] = [
        { id: '1', track_number: 1, title: 'Track 1' },
        { id: '2', track_number: 2, title: 'Track 2' },
        { id: '3', track_number: 5, title: 'Track 5' }
      ]

      const map = createTrackIndexMap(tracks as any)

      expect(map.size)
        .toBe(3)
      expect(map.get(1)?.id)
        .toBe('1')
      expect(map.get(2)?.id)
        .toBe('2')
      expect(map.get(5)?.id)
        .toBe('3')
      expect(map.has(3))
        .toBe(false)
    })

    it('should handle tracks with legacy number field', () => {
      const tracks: MockTrack[] = [
        { id: '1', number: 1, title: 'Track 1' },
        { id: '2', track_number: 2, title: 'Track 2' }
      ]

      const map = createTrackIndexMap(tracks as any)

      expect(map.size)
        .toBe(2)
      expect(map.get(1)?.id)
        .toBe('1')
      expect(map.get(2)?.id)
        .toBe('2')
    })

    it('should handle empty track array', () => {
      const map = createTrackIndexMap([])

      expect(map.size)
        .toBe(0)
    })

    it('should handle duplicate track numbers (last one wins)', () => {
      const tracks: MockTrack[] = [
        { id: '1', track_number: 1, title: 'Track 1' },
        { id: '2', track_number: 1, title: 'Track 1 duplicate' }
      ]

      const map = createTrackIndexMap(tracks as any)

      expect(map.size)
        .toBe(1)
      expect(map.get(1)?.id)
        .toBe('2') // Last one wins
    })
  })

  describe('batchUpdateTrackNumbers', () => {
    it('should update track numbers correctly', () => {
      const tracks: MockTrack[] = [
        { id: '1', track_number: 3, title: 'Track A' },
        { id: '2', track_number: 1, title: 'Track B' },
        { id: '3', track_number: 2, title: 'Track C' }
      ]

      const newOrder = [2, 3, 1] // Not used in current implementation

      const updated = batchUpdateTrackNumbers(tracks as any, newOrder)

      expect(updated)
        .toHaveLength(3)
      expect(updated[0].track_number)
        .toBe(1)
      expect(updated[1].track_number)
        .toBe(2)
      expect(updated[2].track_number)
        .toBe(3)
      expect(updated[0].number)
        .toBeUndefined()
      expect(updated[1].number)
        .toBeUndefined()
      expect(updated[2].number)
        .toBeUndefined()
    })

    it('should preserve other track properties', () => {
      const tracks: MockTrack[] = [
        { id: '1', track_number: 3, title: 'Track A', artist: 'Artist 1' },
        { id: '2', track_number: 1, title: 'Track B', artist: 'Artist 2' }
      ]

      const updated = batchUpdateTrackNumbers(tracks as any, [1, 2])

      expect(updated[0].id)
        .toBe('1')
      expect(updated[0].title)
        .toBe('Track A')
      expect(updated[0].artist)
        .toBe('Artist 1')
      expect(updated[1].id)
        .toBe('2')
      expect(updated[1].title)
        .toBe('Track B')
      expect(updated[1].artist)
        .toBe('Artist 2')
    })

    it('should throw error for mismatched array lengths', () => {
      const tracks: MockTrack[] = [
        { id: '1', track_number: 1 },
        { id: '2', track_number: 2 }
      ]

      expect(() => {
        batchUpdateTrackNumbers(tracks as any, [1, 2, 3])
      })
        .toThrow('Track count mismatch')
    })

    it('should handle empty arrays', () => {
      const updated = batchUpdateTrackNumbers([], [])

      expect(updated)
        .toEqual([])
    })

    it('should handle tracks with legacy number field', () => {
      const tracks: MockTrack[] = [
        { id: '1', number: 5, title: 'Legacy Track' }
      ]

      const updated = batchUpdateTrackNumbers(tracks as any, [1])

      expect(updated[0].track_number)
        .toBe(1)
      expect(updated[0].number)
        .toBeUndefined()
    })
  })

  describe('Performance Tests', () => {
    it('should handle large track arrays efficiently', () => {
      const largeTracks = Array.from({ length: 10000 }, (_, i) => ({
        id: `track-${i}`,
        track_number: i + 1,
        title: `Track ${i + 1}`,
        duration_ms: 180000
      }))

      const startTime = performance.now()

      // Test various operations
      const sorted = sortTracksByNumber(largeTracks as any)
      const map = createTrackIndexMap(largeTracks as any)
      const found = findTrackByNumber(largeTracks as any, 5000)
      const filtered = filterTracksByNumbers(largeTracks as any, [1, 2, 3, 4, 5])

      const endTime = performance.now()

      expect(endTime - startTime)
        .toBeLessThan(1000) // Should complete within 1 second
      expect(sorted)
        .toHaveLength(10000)
      expect(map.size)
        .toBe(10000)
      expect(found?.id)
        .toBe('track-4999')
      expect(filtered)
        .toHaveLength(9995)
    })

    it('should handle frequent normalization operations efficiently', () => {
      const tracks = Array.from({ length: 1000 }, (_, i) => ({
        id: `track-${i}`,
        number: i + 1, // Legacy field
        duration: 180, // Legacy field
        title: `Track ${i + 1}`
      }))

      const startTime = performance.now()
      const normalized = tracks.map(track => normalizeTrack(track as any))
      const endTime = performance.now()

      expect(endTime - startTime)
        .toBeLessThan(100) // Should be very fast
      expect(normalized)
        .toHaveLength(1000)
      expect(normalized[0].track_number)
        .toBe(1)
      expect(normalized[999].track_number)
        .toBe(1000)
    })

    it('should handle frequent duration formatting efficiently', () => {
      const tracks = Array.from({ length: 1000 }, (_, i) => ({
        duration_ms: (i + 1) * 1000
      }))

      const startTime = performance.now()
      const formatted = tracks.map(track => formatTrackDuration(track as any))
      const endTime = performance.now()

      expect(endTime - startTime)
        .toBeLessThan(100) // Should be very fast
      expect(formatted)
        .toHaveLength(1000)
      expect(formatted[0])
        .toBe('0:01')
      expect(formatted[999])
        .toBe('16:40')
    })
  })

  describe('Edge Cases and Error Handling', () => {
    it('should handle null and undefined tracks gracefully', () => {
      expect(() => getTrackNumber(null as any))
        .not.toThrow()
      expect(() => getTrackDurationMs(undefined as any))
        .not.toThrow()
      expect(() => formatTrackDuration(null as any))
        .not.toThrow()
      expect(() => hasValidTrackNumber(undefined as any))
        .not.toThrow()
    })

    it('should handle malformed track objects', () => {
      const malformedTracks = [
        'not an object',
        123,
        [],
        { someOtherField: 'value' },
        { track_number: 'not a number' },
        { duration_ms: 'not a number' }
      ]

      malformedTracks.forEach(track => {
        expect(() => getTrackNumber(track as any))
          .not.toThrow()
        expect(() => getTrackDurationMs(track as any))
          .not.toThrow()
        expect(() => hasValidTrackNumber(track as any))
          .not.toThrow()
      })
    })

    it('should handle extreme values correctly', () => {
      const extremeTracks = [
        { track_number: Number.MAX_SAFE_INTEGER },
        { track_number: Number.MIN_SAFE_INTEGER },
        { duration_ms: Number.MAX_SAFE_INTEGER },
        { duration_ms: 0 },
        { duration_ms: Infinity },
        { duration_ms: -Infinity }
      ]

      extremeTracks.forEach(track => {
        expect(() => getTrackNumber(track as any))
          .not.toThrow()
        expect(() => getTrackDurationMs(track as any))
          .not.toThrow()
        expect(() => formatTrackDuration(track as any))
          .not.toThrow()
      })
    })
  })
})