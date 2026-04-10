import { describe, it, expect, vi, beforeEach } from 'vitest'
import { TimerManager, timerManager } from '@/utils/TimerManager'

describe('TimerManager', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    timerManager.cleanup()
  })

  it('setTimeout schedules and auto-cleans', () => {
    const cb = vi.fn()
    const id = timerManager.setTimeout(cb, 100, 'test timeout')
    expect(id).toBeDefined()
    vi.advanceTimersByTime(100)
    expect(cb).toHaveBeenCalledTimes(1)
    // After execution, stats should reflect no timeouts
    const stats = timerManager.getStats()
    expect(stats.timeouts).toBe(0)
  })

  it('setInterval can be cleared and cleanup clears all', () => {
    const cb = vi.fn()
    const id = timerManager.setInterval(cb, 50, 'tick')
    vi.advanceTimersByTime(200)
    expect(cb).toHaveBeenCalledTimes(4)

    timerManager.clearInterval(id)
    const calls = cb.mock.calls.length
    vi.advanceTimersByTime(200)
    expect(cb.mock.calls.length).toBe(calls) // no more calls

    // Recreate and cleanup
    timerManager.setInterval(cb, 50, 'tick2')
    expect(timerManager.getStats().intervals).toBeGreaterThan(0)
    timerManager.cleanup()
    expect(timerManager.getStats().intervals).toBe(0)
  })

  it('cleanupOldTimers prunes aged timers', () => {
    const tm = TimerManager.getInstance()
    tm.setInterval(() => {}, 1000, 'old')
    const before = Date.now()
    vi.spyOn(Date, 'now').mockReturnValue(before + 61_000)
    tm.cleanupOldTimers(60_000)
    expect(tm.getStats().intervals).toBe(0)
  })

  it('aliases and cleanup handlers are invoked', () => {
    const tm = TimerManager.getInstance()
    const handler = vi.fn()
    tm.registerCleanupHandler(handler)

    // setTimeout alias and clearTimeout alias
    const id = tm.setTimeout(() => {}, 50, 'tmp')
    tm.clearTimeout(id)

    // setInterval and clear via alias
    const iid = tm.setInterval(() => {}, 100, 'tmp')
    tm.clearInterval(iid)

    tm.cleanup()
    expect(handler).toHaveBeenCalled()
    tm.unregisterCleanupHandler(handler)
  })

  it('logStats runs and global __cleanupTimers exists', () => {
    timerManager.logStats()
    expect(typeof (window as any).__cleanupTimers).toBe('function')
    ;(window as any).__cleanupTimers()
  })

  it('handles beforeunload and interval error path', () => {
    // beforeunload should trigger cleanup without throwing
    window.dispatchEvent(new Event('beforeunload'))

    // Interval callback throws to exercise catch branch
    const throwing = vi.fn(() => { throw new Error('boom') })
    timerManager.setInterval(throwing, 10, 'throwing')
    vi.advanceTimersByTime(20)
    expect(throwing).toHaveBeenCalled()
  })
})
