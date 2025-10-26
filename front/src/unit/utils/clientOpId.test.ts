import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  generateClientOpId,
  pendingOperations,
  trackPendingOperation,
  resolvePendingOperation,
  rejectPendingOperation,
  cleanupExpiredOperations
} from '@/utils/clientOpId'

describe('clientOpId', () => {
  beforeEach(() => {
    pendingOperations.clear()
  })

  it('generateClientOpId produces unique keys', () => {
    const a = generateClientOpId('op')
    const b = generateClientOpId('op')
    expect(a).not.toEqual(b)
    expect(a.startsWith('op_')).toBe(true)
  })

  it('tracks and resolves pending operations', () => {
    const id = 'op_1_token'
    trackPendingOperation(id, 'op')
    // attach resolvers (as in real usage)
    const pending = pendingOperations.get(id)!
    const resolve = vi.fn()
    const reject = vi.fn()
    pending.resolve = resolve
    pending.reject = reject

    resolvePendingOperation(id, { ok: true })
    expect(resolve).toHaveBeenCalledWith({ ok: true })
    expect(pendingOperations.has(id)).toBe(false)

    // Rejection path
    trackPendingOperation(id, 'op')
    const pend2 = pendingOperations.get(id)!
    pend2.reject = reject
    const err = new Error('boom')
    rejectPendingOperation(id, err)
    expect(reject).toHaveBeenCalledWith(err)
    expect(pendingOperations.has(id)).toBe(false)
  })

  it('cleanupExpiredOperations rejects aged entries', () => {
    const id = 'cleanup_1'
    trackPendingOperation(id, 'op')
    const pend = pendingOperations.get(id)!
    const reject = vi.fn()
    pend.reject = reject

    // Age the entry
    const now = Date.now()
    vi.spyOn(Date, 'now').mockReturnValue(now + 31_000)
    cleanupExpiredOperations(30_000)
    expect(reject).toHaveBeenCalled()
    expect(pendingOperations.has(id)).toBe(false)
  })
})

