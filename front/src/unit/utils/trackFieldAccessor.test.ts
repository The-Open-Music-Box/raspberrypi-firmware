import { describe, it, expect } from 'vitest'
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

describe('trackFieldAccessor', () => {
  const t = (over: any = {}) => ({ track_number: 1, duration_ms: 1000, title: 't', ...over }) as any

  it('accessors and fallbacks work', () => {
    expect(getTrackNumber(t({ track_number: 7 }))).toBe(7)
    expect(getTrackNumber(t({ track_number: undefined, number: 3 }))).toBe(3)
    expect(getTrackNumber({} as any)).toBe(0)
    expect(getTrackNumber(null as any)).toBe(0)

    expect(getTrackDurationMs(t({ duration_ms: 5000 }))).toBe(5000)
    expect(getTrackDurationMs(t({ duration_ms: undefined, duration: 5 }))).toBe(5000)
    expect(getTrackDurationMs(null as any)).toBe(0)

    expect(getTrackDurationSeconds(t({ duration_ms: 2000 }))).toBe(2)
    expect(getTrackDurationSeconds(t({ duration_ms: undefined, duration: 2 }))).toBe(2)
    expect(getTrackDurationSeconds({} as any)).toBe(0)
    expect(getTrackDurationSeconds(null as any)).toBe(0)
  })

  it('normalizeTrack converts legacy fields', () => {
    const norm = normalizeTrack({ number: 9, duration: 3 } as any)
    expect(norm.track_number).toBe(9)
    expect(norm.duration_ms).toBe(3000)
    expect(norm.number).toBeUndefined()
    expect(norm.duration).toBeUndefined()
    expect(normalizeTrack(null as any)).toBe(null)
  })

  it('formatTrackDuration prints mm:ss or h:mm:ss', () => {
    expect(formatTrackDuration(t({ duration_ms: 0 }))).toBe('00:00')
    expect(formatTrackDuration(t({ duration_ms: 65000 }))).toBe('1:05')
    expect(formatTrackDuration(t({ duration_ms: 3600_000 + 61_000 }))).toBe('1:01:01')
  })

  it('find/sort/filter helpers behave as expected', () => {
    const a = t({ track_number: 2, title: 'a' })
    const b = t({ track_number: 1, title: 'b' })
    const c = t({ track_number: 3, title: 'c' })
    const arr = [a, b, c]

    expect(findTrackByNumber(arr, 1)).toBe(b)
    expect(sortTracksByNumber(arr).map(x => x.title)).toEqual(['b', 'a', 'c'])
    expect(filterTracksByNumbers(arr, [1, 3]).map(x => x.title)).toEqual(['a'])
    expect(filterTrackByNumber(arr, 2).map(x => x.title)).toEqual(['b', 'c'])
    expect(findTrackByNumber(arr, 99)).toBeUndefined()
  })

  it('validation helpers work', () => {
    expect(hasValidTrackNumber(t({ track_number: 0 }))).toBe(false)
    expect(hasValidTrackNumber(t({ track_number: 5 }))).toBe(true)
    expect(hasValidDuration(t({ duration_ms: 0 }))).toBe(false)
    expect(hasValidDuration(t({ duration_ms: 1 }))).toBe(true)
  })

  it('safe find and drag validation', () => {
    const arr = [t({ track_number: 1 }), t({ track_number: 2 }), t({ track_number: 2 })]
    const safe = findTrackByNumberSafe(arr, 2)
    expect(safe.track).toBeDefined()
    expect(safe.error).toBeNull()

    const invalid = validateTracksForDrag('nope' as any)
    expect(invalid.valid).toBe(false)
    const dup = validateTracksForDrag(arr)
    expect(dup.valid).toBe(false)
    expect(dup.errors.join(' ')).toMatch(/Duplicate/)

    // Invalid track numbers error path
    const invalidNumbers = validateTracksForDrag([t({ track_number: 0 })])
    expect(invalidNumbers.valid).toBe(false)
    expect(invalidNumbers.errors.join(' ')).toMatch(/invalid track numbers/)
  })

  it('findTrackByNumberSafe catches thrown errors', () => {
    const throwingTrack = {}
    Object.defineProperty(throwingTrack, 'track_number', { get() { throw new Error('boom') } })
    const res = findTrackByNumberSafe([throwingTrack as any], 1)
    expect(res.track).toBeNull()
    expect(res.error).toMatch(/Error finding track/)
  })

  it('createTrackIndexMap builds O(1) lookup map', () => {
    const arr = [t({ track_number: 1 }), t({ track_number: 9 })]
    const map = createTrackIndexMap(arr)
    expect(map.get(9)?.track_number).toBe(9)
  })

  it('getTrackDurationMs and batchUpdateTrackNumbers paths', () => {
    expect(getTrackDurationMs({} as any)).toBe(0)

    const arr = [t({ track_number: 5 }), t({ track_number: 9 })]
    const updated = batchUpdateTrackNumbers(arr as any, [1, 2])
    expect(updated[0].track_number).toBe(1)
    expect(updated[1].track_number).toBe(2)

    expect(() => batchUpdateTrackNumbers([t({})] as any, [1,2])).toThrow(/Track count mismatch/)
  })
})
