import { describe, it, expect, vi } from 'vitest'
import * as ops from '@/utils/operationUtils'

describe('operationUtils', () => {
  it('generateClientOpId creates op_timestamp_random format', () => {
    vi.spyOn(Date, 'now').mockReturnValue(1720000000000)
    vi.spyOn(Math, 'random').mockReturnValue(0.5)

    const id = ops.generateClientOpId('create_playlist')
    expect(id).toMatch(/^create_playlist_1720000000000_[a-z0-9]+$/)
  })

  it('generateClientOpId uses fallback when random suffix empty', () => {
    vi.spyOn(Date, 'now').mockReturnValue(1720000000000)
    vi.spyOn(Math, 'random').mockReturnValue(0)
    const id = ops.generateClientOpId('op')
    expect(id.endsWith('_000000000')).toBe(true)
  })

  it('validateClientOpId validates correct and rejects invalid IDs', () => {
    const valid = 'delete_track_1720000000000_abcd12345'
    expect(ops.validateClientOpId(valid)).toBe(true)
    expect(ops.validateClientOpId('')).toBe(false)
    expect(ops.validateClientOpId('no_underscores')).toBe(false)
    expect(ops.validateClientOpId('missing_random_1720000_')).toBe(false)
    expect(ops.validateClientOpId('missing_timestamp__abcdef')).toBe(false)
  })

  it('extractOperationName returns the operation segment', () => {
    const id = 'upload_file_1720000000000_abcd12345'
    expect(ops.extractOperationName(id)).toBe('upload_file')
  })

  it('extractOperationName returns null for invalid id', () => {
    expect(ops.extractOperationName('bad')).toBeNull()
  })

  // batchUpdateTrackNumbers is covered via store workflows; skip here for now
})
