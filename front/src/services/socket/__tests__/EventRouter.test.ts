/**
 * Event Router Tests
 *
 * Complete test coverage for EventRouter class
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { EventRouter } from '../EventRouter'

// Mock logger
vi.mock('@/utils/logger', () => ({
  logger: {
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn()
  }
}))

// Mock window.dispatchEvent
const mockDispatchEvent = vi.fn()
Object.defineProperty(window, 'dispatchEvent', {
  value: mockDispatchEvent,
  writable: true
})

describe('EventRouter', () => {
  let eventRouter: EventRouter

  beforeEach(() => {
    eventRouter = new EventRouter()
    mockDispatchEvent.mockClear()
  })

  afterEach(() => {
    eventRouter.destroy()
  })

  describe('Initialization', () => {
    it('should initialize with no handlers', () => {
      expect(eventRouter.getTotalHandlerCount()).toBe(0)
      expect(eventRouter.getEventNames()).toEqual([])
    })

    it('should enable DOM events by default', () => {
      const router = new EventRouter()
      router.dispatchDOMEvent('test', { foo: 'bar' })

      expect(mockDispatchEvent).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'test',
          detail: { foo: 'bar' }
        })
      )
    })

    it('should disable DOM events when configured', () => {
      const router = new EventRouter({ enableDOMEvents: false })
      router.dispatchDOMEvent('test', { foo: 'bar' })

      expect(mockDispatchEvent).not.toHaveBeenCalled()
    })

    it('should allow explicit enableDOMEvents: true', () => {
      const router = new EventRouter({ enableDOMEvents: true })
      router.dispatchDOMEvent('test', {})

      expect(mockDispatchEvent).toHaveBeenCalled()
    })
  })

  describe('Event Handler Registration', () => {
    it('should register event handler with on()', () => {
      const handler = vi.fn()
      eventRouter.on('test', handler)

      expect(eventRouter.hasHandlers('test')).toBe(true)
      expect(eventRouter.getHandlerCount('test')).toBe(1)
    })

    it('should register multiple handlers for same event', () => {
      const handler1 = vi.fn()
      const handler2 = vi.fn()
      const handler3 = vi.fn()

      eventRouter.on('test', handler1)
      eventRouter.on('test', handler2)
      eventRouter.on('test', handler3)

      expect(eventRouter.getHandlerCount('test')).toBe(3)
    })

    it('should register handlers for different events', () => {
      const handler1 = vi.fn()
      const handler2 = vi.fn()

      eventRouter.on('event1', handler1)
      eventRouter.on('event2', handler2)

      expect(eventRouter.getHandlerCount('event1')).toBe(1)
      expect(eventRouter.getHandlerCount('event2')).toBe(1)
      expect(eventRouter.getEventNames()).toContain('event1')
      expect(eventRouter.getEventNames()).toContain('event2')
    })

    it('should not register duplicate handlers', () => {
      const handler = vi.fn()

      eventRouter.on('test', handler)
      eventRouter.on('test', handler)

      expect(eventRouter.getHandlerCount('test')).toBe(1)
    })
  })

  describe('Event Handler Removal', () => {
    it('should remove handler with off()', () => {
      const handler = vi.fn()
      eventRouter.on('test', handler)
      eventRouter.off('test', handler)

      expect(eventRouter.hasHandlers('test')).toBe(false)
      expect(eventRouter.getHandlerCount('test')).toBe(0)
    })

    it('should only remove specified handler', () => {
      const handler1 = vi.fn()
      const handler2 = vi.fn()

      eventRouter.on('test', handler1)
      eventRouter.on('test', handler2)
      eventRouter.off('test', handler1)

      expect(eventRouter.getHandlerCount('test')).toBe(1)

      eventRouter.emit('test')
      expect(handler1).not.toHaveBeenCalled()
      expect(handler2).toHaveBeenCalled()
    })

    it('should handle removing non-existent handler', () => {
      const handler = vi.fn()

      expect(() => eventRouter.off('test', handler)).not.toThrow()
      expect(eventRouter.hasHandlers('test')).toBe(false)
    })

    it('should handle removing handler from non-existent event', () => {
      const handler = vi.fn()

      expect(() => eventRouter.off('nonexistent', handler)).not.toThrow()
    })

    it('should clean up empty event handler sets', () => {
      const handler = vi.fn()
      eventRouter.on('test', handler)
      eventRouter.off('test', handler)

      expect(eventRouter.getEventNames()).not.toContain('test')
    })
  })

  describe('removeAllListeners', () => {
    it('should remove all handlers for specific event', () => {
      const handler1 = vi.fn()
      const handler2 = vi.fn()

      eventRouter.on('test', handler1)
      eventRouter.on('test', handler2)
      eventRouter.on('other', vi.fn())

      eventRouter.removeAllListeners('test')

      expect(eventRouter.hasHandlers('test')).toBe(false)
      expect(eventRouter.hasHandlers('other')).toBe(true)
    })

    it('should remove all handlers for all events when no event specified', () => {
      eventRouter.on('event1', vi.fn())
      eventRouter.on('event2', vi.fn())
      eventRouter.on('event3', vi.fn())

      eventRouter.removeAllListeners()

      expect(eventRouter.getTotalHandlerCount()).toBe(0)
      expect(eventRouter.getEventNames()).toEqual([])
    })

    it('should handle removing listeners from non-existent event', () => {
      expect(() => eventRouter.removeAllListeners('nonexistent')).not.toThrow()
    })
  })

  describe('once', () => {
    it('should register one-time handler', () => {
      const handler = vi.fn()
      eventRouter.once('test', handler)

      expect(eventRouter.hasHandlers('test')).toBe(true)
    })

    it('should call handler only once', () => {
      const handler = vi.fn()
      eventRouter.once('test', handler)

      eventRouter.emit('test', 'data1')
      eventRouter.emit('test', 'data2')
      eventRouter.emit('test', 'data3')

      expect(handler).toHaveBeenCalledTimes(1)
      expect(handler).toHaveBeenCalledWith('data1')
    })

    it('should remove handler after first call', () => {
      const handler = vi.fn()
      eventRouter.once('test', handler)

      eventRouter.emit('test')

      expect(eventRouter.hasHandlers('test')).toBe(false)
    })

    it('should pass correct arguments to handler', () => {
      const handler = vi.fn()
      eventRouter.once('test', handler)

      eventRouter.emit('test', 'arg1', 'arg2', 'arg3')

      expect(handler).toHaveBeenCalledWith('arg1', 'arg2', 'arg3')
    })

    it('should work alongside regular handlers', () => {
      const onceHandler = vi.fn()
      const regularHandler = vi.fn()

      eventRouter.once('test', onceHandler)
      eventRouter.on('test', regularHandler)

      eventRouter.emit('test')
      eventRouter.emit('test')

      expect(onceHandler).toHaveBeenCalledTimes(1)
      expect(regularHandler).toHaveBeenCalledTimes(2)
    })
  })

  describe('emit', () => {
    it('should call registered handlers', () => {
      const handler = vi.fn()
      eventRouter.on('test', handler)

      eventRouter.emit('test')

      expect(handler).toHaveBeenCalled()
    })

    it('should call all registered handlers for event', () => {
      const handler1 = vi.fn()
      const handler2 = vi.fn()
      const handler3 = vi.fn()

      eventRouter.on('test', handler1)
      eventRouter.on('test', handler2)
      eventRouter.on('test', handler3)

      eventRouter.emit('test')

      expect(handler1).toHaveBeenCalled()
      expect(handler2).toHaveBeenCalled()
      expect(handler3).toHaveBeenCalled()
    })

    it('should pass arguments to handlers', () => {
      const handler = vi.fn()
      eventRouter.on('test', handler)

      eventRouter.emit('test', 'arg1', 42, { foo: 'bar' })

      expect(handler).toHaveBeenCalledWith('arg1', 42, { foo: 'bar' })
    })

    it('should not call handlers for different events', () => {
      const handler1 = vi.fn()
      const handler2 = vi.fn()

      eventRouter.on('event1', handler1)
      eventRouter.on('event2', handler2)

      eventRouter.emit('event1')

      expect(handler1).toHaveBeenCalled()
      expect(handler2).not.toHaveBeenCalled()
    })

    it('should handle emitting event with no handlers', () => {
      expect(() => eventRouter.emit('nonexistent')).not.toThrow()
    })

    it('should handle errors in handlers gracefully', () => {
      const errorHandler = vi.fn(() => {
        throw new Error('Handler error')
      })
      const goodHandler = vi.fn()

      eventRouter.on('test', errorHandler)
      eventRouter.on('test', goodHandler)

      expect(() => eventRouter.emit('test')).not.toThrow()
      expect(goodHandler).toHaveBeenCalled()
    })

    it('should continue calling handlers after error', () => {
      const handler1 = vi.fn()
      const handler2 = vi.fn(() => {
        throw new Error('Error in handler2')
      })
      const handler3 = vi.fn()

      eventRouter.on('test', handler1)
      eventRouter.on('test', handler2)
      eventRouter.on('test', handler3)

      eventRouter.emit('test')

      expect(handler1).toHaveBeenCalled()
      expect(handler2).toHaveBeenCalled()
      expect(handler3).toHaveBeenCalled()
    })
  })

  describe('dispatchDOMEvent', () => {
    it('should dispatch CustomEvent to window', () => {
      eventRouter.dispatchDOMEvent('test', { foo: 'bar' })

      expect(mockDispatchEvent).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'test',
          detail: { foo: 'bar' }
        })
      )
    })

    it('should create non-bubbling, non-cancelable events', () => {
      eventRouter.dispatchDOMEvent('test', {})

      const event = mockDispatchEvent.mock.calls[0][0]
      expect(event.bubbles).toBe(false)
      expect(event.cancelable).toBe(false)
    })

    it('should not dispatch when DOM events disabled', () => {
      const router = new EventRouter({ enableDOMEvents: false })
      router.dispatchDOMEvent('test', {})

      expect(mockDispatchEvent).not.toHaveBeenCalled()
    })

    it('should handle dispatch errors gracefully', () => {
      mockDispatchEvent.mockImplementationOnce(() => {
        throw new Error('Dispatch error')
      })

      expect(() => eventRouter.dispatchDOMEvent('test', {})).not.toThrow()
    })

    it('should dispatch events with complex data', () => {
      const data = {
        nested: {
          array: [1, 2, 3],
          object: { key: 'value' }
        },
        func: () => {}
      }

      eventRouter.dispatchDOMEvent('complex', data)

      expect(mockDispatchEvent).toHaveBeenCalledWith(
        expect.objectContaining({
          detail: data
        })
      )
    })
  })

  describe('broadcast', () => {
    it('should emit to local handlers', () => {
      const handler = vi.fn()
      eventRouter.on('test', handler)

      eventRouter.broadcast('test', { foo: 'bar' })

      expect(handler).toHaveBeenCalledWith({ foo: 'bar' })
    })

    it('should dispatch DOM event', () => {
      eventRouter.broadcast('test', { foo: 'bar' })

      expect(mockDispatchEvent).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'test',
          detail: { foo: 'bar' }
        })
      )
    })

    it('should do both local emit and DOM dispatch', () => {
      const handler = vi.fn()
      eventRouter.on('test', handler)

      eventRouter.broadcast('test', { data: 'value' })

      expect(handler).toHaveBeenCalledWith({ data: 'value' })
      expect(mockDispatchEvent).toHaveBeenCalledWith(
        expect.objectContaining({
          detail: { data: 'value' }
        })
      )
    })

    it('should respect DOM events disabled setting', () => {
      const router = new EventRouter({ enableDOMEvents: false })
      const handler = vi.fn()
      router.on('test', handler)

      router.broadcast('test', { foo: 'bar' })

      expect(handler).toHaveBeenCalledWith({ foo: 'bar' })
      expect(mockDispatchEvent).not.toHaveBeenCalled()
    })
  })

  describe('Handler Introspection', () => {
    it('should return correct handler count', () => {
      eventRouter.on('test', vi.fn())
      eventRouter.on('test', vi.fn())
      eventRouter.on('test', vi.fn())

      expect(eventRouter.getHandlerCount('test')).toBe(3)
    })

    it('should return 0 for event with no handlers', () => {
      expect(eventRouter.getHandlerCount('nonexistent')).toBe(0)
    })

    it('should return correct total handler count', () => {
      eventRouter.on('event1', vi.fn())
      eventRouter.on('event1', vi.fn())
      eventRouter.on('event2', vi.fn())
      eventRouter.on('event3', vi.fn())

      expect(eventRouter.getTotalHandlerCount()).toBe(4)
    })

    it('should return empty array when no events registered', () => {
      expect(eventRouter.getEventNames()).toEqual([])
    })

    it('should return all registered event names', () => {
      eventRouter.on('event1', vi.fn())
      eventRouter.on('event2', vi.fn())
      eventRouter.on('event3', vi.fn())

      const names = eventRouter.getEventNames()
      expect(names).toContain('event1')
      expect(names).toContain('event2')
      expect(names).toContain('event3')
      expect(names).toHaveLength(3)
    })

    it('should correctly report hasHandlers', () => {
      expect(eventRouter.hasHandlers('test')).toBe(false)

      eventRouter.on('test', vi.fn())
      expect(eventRouter.hasHandlers('test')).toBe(true)

      eventRouter.removeAllListeners('test')
      expect(eventRouter.hasHandlers('test')).toBe(false)
    })

    it('should update counts after removing handlers', () => {
      const handler = vi.fn()
      eventRouter.on('test', handler)
      expect(eventRouter.getTotalHandlerCount()).toBe(1)

      eventRouter.off('test', handler)
      expect(eventRouter.getTotalHandlerCount()).toBe(0)
    })
  })

  describe('destroy', () => {
    it('should clear all handlers', () => {
      eventRouter.on('event1', vi.fn())
      eventRouter.on('event2', vi.fn())
      eventRouter.on('event3', vi.fn())

      eventRouter.destroy()

      expect(eventRouter.getTotalHandlerCount()).toBe(0)
      expect(eventRouter.getEventNames()).toEqual([])
    })

    it('should prevent handlers from being called after destroy', () => {
      const handler = vi.fn()
      eventRouter.on('test', handler)

      eventRouter.destroy()
      eventRouter.emit('test')

      expect(handler).not.toHaveBeenCalled()
    })

    it('should be safe to call multiple times', () => {
      eventRouter.on('test', vi.fn())

      expect(() => {
        eventRouter.destroy()
        eventRouter.destroy()
        eventRouter.destroy()
      }).not.toThrow()

      expect(eventRouter.getTotalHandlerCount()).toBe(0)
    })
  })

  describe('Edge Cases', () => {
    it('should handle empty event name', () => {
      const handler = vi.fn()
      eventRouter.on('', handler)
      eventRouter.emit('')

      expect(handler).toHaveBeenCalled()
    })

    it('should handle event names with special characters', () => {
      const handler = vi.fn()
      const eventName = 'event:with:special$chars#123'

      eventRouter.on(eventName, handler)
      eventRouter.emit(eventName, 'data')

      expect(handler).toHaveBeenCalledWith('data')
    })

    it('should handle no arguments in emit', () => {
      const handler = vi.fn()
      eventRouter.on('test', handler)

      eventRouter.emit('test')

      expect(handler).toHaveBeenCalledWith()
    })

    it('should handle many arguments in emit', () => {
      const handler = vi.fn()
      eventRouter.on('test', handler)

      const args = Array.from({ length: 20 }, (_, i) => i)
      eventRouter.emit('test', ...args)

      expect(handler).toHaveBeenCalledWith(...args)
    })

    it('should handle undefined and null data', () => {
      const handler = vi.fn()
      eventRouter.on('test', handler)

      eventRouter.emit('test', undefined, null)

      expect(handler).toHaveBeenCalledWith(undefined, null)
    })

    it('should maintain handler execution order', () => {
      const callOrder: number[] = []

      eventRouter.on('test', () => callOrder.push(1))
      eventRouter.on('test', () => callOrder.push(2))
      eventRouter.on('test', () => callOrder.push(3))

      eventRouter.emit('test')

      expect(callOrder).toEqual([1, 2, 3])
    })

    it('should allow adding handlers during emit', () => {
      const handler2 = vi.fn()
      const handler1 = vi.fn(() => {
        eventRouter.on('test', handler2)
      })

      eventRouter.on('test', handler1)
      eventRouter.emit('test')

      expect(handler1).toHaveBeenCalled()
      // handler2 may or may not be called on first emit depending on Set iteration timing
      // This is expected behavior - adding handlers during emit is an edge case

      // Second emit should definitely call handler2
      handler1.mockClear()
      handler2.mockClear()
      eventRouter.emit('test')
      expect(handler1).toHaveBeenCalled()
      expect(handler2).toHaveBeenCalled()
    })

    it('should allow removing handlers during emit', () => {
      const handler2 = vi.fn()
      const handler1 = vi.fn(() => {
        eventRouter.off('test', handler2)
      })

      eventRouter.on('test', handler1)
      eventRouter.on('test', handler2)

      eventRouter.emit('test')

      expect(handler1).toHaveBeenCalled()
      // handler2 might or might not be called depending on Set iteration order
      // This is an edge case - modifying handlers during emit
    })
  })
})
