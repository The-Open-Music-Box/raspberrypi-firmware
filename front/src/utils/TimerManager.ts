/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Global Timer Manager
 * 
 * Centralized management of setTimeout and setInterval to prevent memory leaks
 * and ensure proper cleanup of all timers across the application.
 */

interface TimerInfo {
  id: number
  type: 'timeout' | 'interval'
  description?: string
  created: number
}

export class TimerManager {
  private static instance: TimerManager
  private timers = new Map<number, TimerInfo>()
  private cleanupHandlers = new Set<() => void>()

  private constructor() {
    // Register cleanup on page unload
    if (typeof window !== 'undefined') {
      window.addEventListener('beforeunload', () => {
        this.cleanup()
      })
    }
  }

  static getInstance(): TimerManager {
    if (!TimerManager.instance) {
      TimerManager.instance = new TimerManager()
    }
    return TimerManager.instance
  }

  /**
   * Managed setTimeout with automatic cleanup
   */
  setTimeout(callback: () => void, ms: number, description?: string): number {
    const id = window.setTimeout(() => {
      try {
        callback()
      } finally {
        this.timers.delete(id)
      }
    }, ms)

    this.timers.set(id, {
      id,
      type: 'timeout',
      description,
      created: Date.now()
    })

    return id
  }

  /**
   * Managed setInterval with automatic cleanup
   */
  setInterval(callback: () => void, ms: number, description?: string): number {
    const id = window.setInterval(() => {
      try {
        callback()
      } catch (error) {
        // console.error(`Error in managed interval (${description}):`, error)
        // Don't clear interval on error to maintain expected behavior
      }
    }, ms)

    this.timers.set(id, {
      id,
      type: 'interval',
      description,
      created: Date.now()
    })

    return id
  }

  /**
   * Clear a specific timer
   */
  clearTimer(id: number): void {
    const timer = this.timers.get(id)
    if (timer) {
      if (timer.type === 'timeout') {
        window.clearTimeout(id)
      } else {
        window.clearInterval(id)
      }
      this.timers.delete(id)
    }
  }

  /**
   * Clear timeout (alias for consistency)
   */
  clearTimeout(id: number): void {
    this.clearTimer(id)
  }

  /**
   * Clear interval (alias for consistency)
   */
  clearInterval(id: number): void {
    this.clearTimer(id)
  }

  /**
   * Register a cleanup handler to be called on app shutdown
   */
  registerCleanupHandler(handler: () => void): void {
    this.cleanupHandlers.add(handler)
  }

  /**
   * Unregister a cleanup handler
   */
  unregisterCleanupHandler(handler: () => void): void {
    this.cleanupHandlers.delete(handler)
  }

  /**
   * Clean up all timers and call cleanup handlers
   */
  cleanup(): void {
    // console.log(`[TimerManager] Cleaning up ${this.timers.size} active timers`)
    
    // Clear all active timers
    this.timers.forEach((timer) => {
      if (timer.type === 'timeout') {
        window.clearTimeout(timer.id)
      } else {
        window.clearInterval(timer.id)
      }
    })

    this.timers.clear()

    // Call all cleanup handlers
    this.cleanupHandlers.forEach(handler => {
      try {
        handler()
      } catch (error) {
        // console.error('[TimerManager] Error in cleanup handler:', error)
      }
    })

    // console.log('[TimerManager] Cleanup completed')
  }

  /**
   * Get active timer statistics for debugging
   */
  getStats(): {
    totalTimers: number
    timeouts: number
    intervals: number
    oldestTimer: number | null
    timerList: Array<{ id: number; type: string; description?: string; ageMs: number }>
  } {
    const now = Date.now()
    const timerArray = Array.from(this.timers.values())
    
    const timeouts = timerArray.filter(t => t.type === 'timeout').length
    const intervals = timerArray.filter(t => t.type === 'interval').length
    
    const oldestTimer = timerArray.reduce((oldest, current) => {
      return current.created < oldest ? current.created : oldest
    }, now)

    const timerList = timerArray.map(timer => ({
      id: timer.id,
      type: timer.type,
      description: timer.description,
      ageMs: now - timer.created
    }))

    return {
      totalTimers: this.timers.size,
      timeouts,
      intervals,
      oldestTimer: oldestTimer === now ? null : now - oldestTimer,
      timerList
    }
  }

  /**
   * Log current timer stats (for debugging)
   */
  logStats(): void {
    // const stats = this.getStats()
    // console.log('[TimerManager] Timer Statistics:', {
    //   ...stats,
    //   timerList: stats.timerList.length > 10 
    //     ? [...stats.timerList.slice(0, 10), { truncated: `... ${stats.timerList.length - 10} more` }]
    //     : stats.timerList
    // })
  }

  /**
   * Force cleanup of old timers (for memory management)
   */
  cleanupOldTimers(maxAgeMs = 60000): void {
    const now = Date.now()
    let cleaned = 0

    this.timers.forEach((timer, id) => {
      if (now - timer.created > maxAgeMs) {
        this.clearTimer(id)
        cleaned++
      }
    })

    if (cleaned > 0) {
      // console.log(`[TimerManager] Cleaned up ${cleaned} old timers`)
    }
  }
}

// Export singleton instance
export const timerManager = TimerManager.getInstance()

// Global cleanup function for emergency use
if (typeof window !== 'undefined') {
  (window as any).__cleanupTimers = () => {
    timerManager.cleanup()
  }
}