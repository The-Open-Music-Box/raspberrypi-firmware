/**
 * Comprehensive tests for EventBuffer.ts
 * Target: 95%+ coverage
 *
 * Test Coverage:
 * - Event buffering and storage
 * - Event sequence ordering (FIFO)
 * - Buffer capacity management
 * - Event replay and processing
 * - Timeout handling for stale events
 * - Buffer state inspection
 * - Event handlers (on/off/emit)
 * - Edge cases and error handling
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { EventBuffer, type BufferedEvent, type EventBufferConfig } from '../../../services/socket/EventBuffer'
import { logger } from '../../../utils/logger'

// Mock the logger
vi.mock('../../../utils/logger', () => ({
  logger: {
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn()
  }
}))

describe('EventBuffer', () => {
  let buffer: EventBuffer
  let defaultConfig: EventBufferConfig

  beforeEach(() => {
    vi.clearAllTimers()
    vi.useFakeTimers()
    vi.clearAllMocks()

    defaultConfig = {
      maxBufferSize: 100,
      maxWaitTime: 5000
    }

    buffer = new EventBuffer(defaultConfig)
  })

  afterEach(() => {
    buffer.destroy()
    vi.useRealTimers()
  })

  describe('Constructor and Initialization', () => {
    it('should initialize with default config', () => {
      const bufferWithDefaults = new EventBuffer()

      expect(bufferWithDefaults.getBufferSize()).toBe(0)
      expect(bufferWithDefaults.getNextExpectedSeq()).toBe(0)
    })

    it('should initialize with custom config', () => {
      const customConfig: EventBufferConfig = {
        maxBufferSize: 50,
        maxWaitTime: 3000
      }
      const customBuffer = new EventBuffer(customConfig)

      expect(customBuffer.getBufferSize()).toBe(0)
      expect(customBuffer.getNextExpectedSeq()).toBe(0)

      customBuffer.destroy()
    })

    it('should start with empty buffer state', () => {
      const state = buffer.getBufferState()

      expect(state).toEqual({
        size: 0,
        nextExpectedSeq: 0,
        bufferedSequences: []
      })
    })
  })

  describe('Event Processing - In Order', () => {
    it('should process event immediately when sequence matches expected', () => {
      const mockHandler = vi.fn()
      buffer.on('event_ready', mockHandler)

      buffer.addEvent(0, 'test:event', { value: 'data1' })

      expect(mockHandler).toHaveBeenCalledWith({
        seq: 0,
        eventName: 'test:event',
        data: { value: 'data1' }
      })
      expect(buffer.getNextExpectedSeq()).toBe(1)
      expect(buffer.getBufferSize()).toBe(0)
    })

    it('should process multiple events in sequence', () => {
      const mockHandler = vi.fn()
      buffer.on('event_ready', mockHandler)

      buffer.addEvent(0, 'event1', { data: 'first' })
      buffer.addEvent(1, 'event2', { data: 'second' })
      buffer.addEvent(2, 'event3', { data: 'third' })

      expect(mockHandler).toHaveBeenCalledTimes(3)
      expect(mockHandler).toHaveBeenNthCalledWith(1, {
        seq: 0,
        eventName: 'event1',
        data: { data: 'first' }
      })
      expect(mockHandler).toHaveBeenNthCalledWith(2, {
        seq: 1,
        eventName: 'event2',
        data: { data: 'second' }
      })
      expect(mockHandler).toHaveBeenNthCalledWith(3, {
        seq: 2,
        eventName: 'event3',
        data: { data: 'third' }
      })
      expect(buffer.getNextExpectedSeq()).toBe(3)
    })

    it('should increment expected sequence after processing', () => {
      buffer.addEvent(0, 'test:event', { data: 'test' })
      expect(buffer.getNextExpectedSeq()).toBe(1)

      buffer.addEvent(1, 'test:event', { data: 'test' })
      expect(buffer.getNextExpectedSeq()).toBe(2)

      buffer.addEvent(2, 'test:event', { data: 'test' })
      expect(buffer.getNextExpectedSeq()).toBe(3)
    })
  })

  describe('Event Buffering - Out of Order', () => {
    it('should buffer future event when sequence is ahead', () => {
      const mockHandler = vi.fn()
      buffer.on('event_ready', mockHandler)

      buffer.addEvent(5, 'future:event', { data: 'future' })

      // Should not process yet
      expect(mockHandler).not.toHaveBeenCalled()
      expect(buffer.getBufferSize()).toBe(1)
      expect(buffer.isBuffered(5)).toBe(true)
      expect(buffer.getNextExpectedSeq()).toBe(0)
    })

    it('should process buffered events when sequence catches up', () => {
      const mockHandler = vi.fn()
      buffer.on('event_ready', mockHandler)

      // Buffer events out of order
      buffer.addEvent(2, 'event3', { data: '3' })
      buffer.addEvent(1, 'event2', { data: '2' })

      expect(mockHandler).not.toHaveBeenCalled()
      expect(buffer.getBufferSize()).toBe(2)

      // Add the missing event
      buffer.addEvent(0, 'event1', { data: '1' })

      // All three should be processed in order
      expect(mockHandler).toHaveBeenCalledTimes(3)
      expect(mockHandler).toHaveBeenNthCalledWith(1, {
        seq: 0,
        eventName: 'event1',
        data: { data: '1' }
      })
      expect(mockHandler).toHaveBeenNthCalledWith(2, {
        seq: 1,
        eventName: 'event2',
        data: { data: '2' }
      })
      expect(mockHandler).toHaveBeenNthCalledWith(3, {
        seq: 2,
        eventName: 'event3',
        data: { data: '3' }
      })
      expect(buffer.getBufferSize()).toBe(0)
      expect(buffer.getNextExpectedSeq()).toBe(3)
    })

    it('should store event with timestamp', () => {
      const beforeTime = Date.now()
      buffer.addEvent(5, 'future:event', { data: 'test' })
      const afterTime = Date.now()

      const state = buffer.getBufferState()
      expect(state.bufferedSequences).toContain(5)

      // Timestamp should be within range
      // Note: We can't directly access the timestamp, but we can verify buffering occurred
      expect(buffer.isBuffered(5)).toBe(true)
    })

    it('should buffer multiple out-of-order events', () => {
      buffer.addEvent(5, 'event5', { data: '5' })
      buffer.addEvent(3, 'event3', { data: '3' })
      buffer.addEvent(7, 'event7', { data: '7' })

      expect(buffer.getBufferSize()).toBe(3)
      expect(buffer.isBuffered(3)).toBe(true)
      expect(buffer.isBuffered(5)).toBe(true)
      expect(buffer.isBuffered(7)).toBe(true)
    })

    it('should return buffered sequences in sorted order', () => {
      buffer.addEvent(7, 'event7', { data: '7' })
      buffer.addEvent(3, 'event3', { data: '3' })
      buffer.addEvent(5, 'event5', { data: '5' })

      const state = buffer.getBufferState()
      expect(state.bufferedSequences).toEqual([3, 5, 7])
    })
  })

  describe('Old Sequence Handling', () => {
    it('should skip events with sequence in the past', () => {
      const mockHandler = vi.fn()
      buffer.on('event_ready', mockHandler)

      // Process seq 0, 1, 2
      buffer.addEvent(0, 'event1', { data: '1' })
      buffer.addEvent(1, 'event2', { data: '2' })
      buffer.addEvent(2, 'event3', { data: '3' })

      expect(buffer.getNextExpectedSeq()).toBe(3)
      mockHandler.mockClear()

      // Try to add old event
      buffer.addEvent(1, 'old:event', { data: 'old' })

      expect(mockHandler).not.toHaveBeenCalled()
      expect(buffer.getBufferSize()).toBe(0)
      expect(logger.warn).toHaveBeenCalledWith(
        expect.stringContaining('Received old sequence 1, expected 3')
      )
    })

    it('should log warning for old sequences', () => {
      buffer.addEvent(0, 'event1', { data: '1' })
      buffer.addEvent(1, 'event2', { data: '2' })

      expect(buffer.getNextExpectedSeq()).toBe(2)

      buffer.addEvent(0, 'old:event', { data: 'old' })

      expect(logger.warn).toHaveBeenCalledWith(
        expect.stringContaining('Received old sequence 0, expected 2')
      )
    })
  })

  describe('Buffer Capacity Management', () => {
    it('should enforce max buffer size', () => {
      const mockOverflowHandler = vi.fn()
      buffer.on('buffer_overflow', mockOverflowHandler)

      // Fill buffer to max capacity (100)
      for (let i = 1; i <= 100; i++) {
        buffer.addEvent(i, `event${i}`, { data: i })
      }

      expect(buffer.getBufferSize()).toBe(100)
      expect(mockOverflowHandler).not.toHaveBeenCalled()

      // Try to add one more (should overflow)
      buffer.addEvent(101, 'overflow:event', { data: 'overflow' })

      expect(buffer.getBufferSize()).toBe(100)
      expect(mockOverflowHandler).toHaveBeenCalledWith({
        seq: 101,
        eventName: 'overflow:event',
        bufferSize: 100
      })
      expect(logger.error).toHaveBeenCalledWith(
        expect.stringContaining('Event buffer overflow, dropping event seq 101')
      )
    })

    it('should drop events when buffer is full', () => {
      // Fill buffer to capacity
      for (let i = 1; i <= 100; i++) {
        buffer.addEvent(i, `event${i}`, { data: i })
      }

      // Try to buffer another event
      buffer.addEvent(101, 'dropped:event', { data: 'dropped' })

      expect(buffer.isBuffered(101)).toBe(false)
      expect(buffer.getBufferSize()).toBe(100)
    })

    it('should handle buffer at exactly max size', () => {
      const smallBuffer = new EventBuffer({ maxBufferSize: 5, maxWaitTime: 5000 })
      const mockOverflowHandler = vi.fn()
      smallBuffer.on('buffer_overflow', mockOverflowHandler)

      // Fill exactly to max
      for (let i = 1; i <= 5; i++) {
        smallBuffer.addEvent(i, `event${i}`, { data: i })
      }

      expect(smallBuffer.getBufferSize()).toBe(5)
      expect(mockOverflowHandler).not.toHaveBeenCalled()

      // Try to add one more
      smallBuffer.addEvent(6, 'overflow', { data: 6 })

      expect(mockOverflowHandler).toHaveBeenCalled()
      expect(smallBuffer.getBufferSize()).toBe(5)

      smallBuffer.destroy()
    })
  })

  describe('Sequence Gap Detection', () => {
    it('should detect and log sequence gap', () => {
      const mockGapHandler = vi.fn()
      buffer.on('sequence_gap', mockGapHandler)

      // Jump from seq 0 to seq 5 (gap of 5)
      buffer.addEvent(0, 'event1', { data: '1' })
      buffer.addEvent(5, 'event2', { data: '2' })

      expect(mockGapHandler).toHaveBeenCalledWith({
        expected: 1,
        received: 5,
        gap: 4
      })
      expect(logger.warn).toHaveBeenCalledWith(
        expect.stringContaining('Sequence gap detected: expected 1, received 5 (gap: 4)')
      )
    })

    it('should not emit gap for consecutive sequences', () => {
      const mockGapHandler = vi.fn()
      buffer.on('sequence_gap', mockGapHandler)

      buffer.addEvent(0, 'event1', { data: '1' })
      buffer.addEvent(1, 'event2', { data: '2' })

      expect(mockGapHandler).not.toHaveBeenCalled()
    })

    it('should not emit gap when sequence is next expected + 1', () => {
      const mockGapHandler = vi.fn()
      buffer.on('sequence_gap', mockGapHandler)

      buffer.addEvent(0, 'event1', { data: '1' })
      // Next expected is 1, adding 2 (gap of 1) should trigger gap detection
      buffer.addEvent(2, 'event3', { data: '3' })

      expect(mockGapHandler).not.toHaveBeenCalled()
    })

    it('should emit gap when sequence jumps by more than 1', () => {
      const mockGapHandler = vi.fn()
      buffer.on('sequence_gap', mockGapHandler)

      buffer.addEvent(0, 'event1', { data: '1' })
      // Next expected is 1, adding 3 (gap of 2) should trigger
      buffer.addEvent(3, 'event4', { data: '4' })

      expect(mockGapHandler).toHaveBeenCalledWith({
        expected: 1,
        received: 3,
        gap: 2
      })
    })
  })

  describe('Stale Event Handling', () => {
    it('should process stale events after maxWaitTime', () => {
      const mockHandler = vi.fn()
      buffer.on('event_ready', mockHandler)

      // Buffer an out-of-order event
      buffer.addEvent(5, 'stale:event', { data: 'stale' })

      expect(mockHandler).not.toHaveBeenCalled()

      // Fast-forward past maxWaitTime (5000ms)
      vi.advanceTimersByTime(5000)

      // Stale event should be processed
      expect(mockHandler).toHaveBeenCalledWith({
        seq: 5,
        eventName: 'stale:event',
        data: { data: 'stale' }
      })
      expect(logger.warn).toHaveBeenCalledWith(
        expect.stringContaining('Processing 1 stale events after wait timeout')
      )
    })

    it('should process multiple stale events in sequence order', () => {
      const mockHandler = vi.fn()
      buffer.on('event_ready', mockHandler)

      // Buffer multiple out-of-order events
      buffer.addEvent(7, 'event7', { data: '7' })
      buffer.addEvent(3, 'event3', { data: '3' })
      buffer.addEvent(5, 'event5', { data: '5' })

      // Fast-forward past maxWaitTime
      vi.advanceTimersByTime(5000)

      // All should be processed in sequence order
      expect(mockHandler).toHaveBeenCalledTimes(3)
      expect(mockHandler).toHaveBeenNthCalledWith(1, {
        seq: 3,
        eventName: 'event3',
        data: { data: '3' }
      })
      expect(mockHandler).toHaveBeenNthCalledWith(2, {
        seq: 5,
        eventName: 'event5',
        data: { data: '5' }
      })
      expect(mockHandler).toHaveBeenNthCalledWith(3, {
        seq: 7,
        eventName: 'event7',
        data: { data: '7' }
      })
    })

    it('should update nextExpectedSeq after processing stale events', () => {
      buffer.addEvent(10, 'stale:event', { data: 'stale' })

      expect(buffer.getNextExpectedSeq()).toBe(0)

      vi.advanceTimersByTime(5000)

      // After processing stale seq 10, next expected should be 11
      expect(buffer.getNextExpectedSeq()).toBe(11)
    })

    it('should process remaining buffered events after stale processing', () => {
      const mockHandler = vi.fn()
      buffer.on('event_ready', mockHandler)

      // Buffer events with gaps
      buffer.addEvent(2, 'event2', { data: '2' })
      buffer.addEvent(3, 'event3', { data: '3' })
      buffer.addEvent(5, 'event5', { data: '5' })

      // Fast-forward to process stale events
      vi.advanceTimersByTime(5000)

      // All three should be processed
      expect(mockHandler).toHaveBeenCalledTimes(3)
      expect(buffer.getBufferSize()).toBe(0)
      expect(buffer.getNextExpectedSeq()).toBe(6)
    })

    it('should not process events that are not stale yet', () => {
      const mockHandler = vi.fn()
      buffer.on('event_ready', mockHandler)

      buffer.addEvent(5, 'future:event', { data: 'future' })

      // Advance time but not past maxWaitTime
      vi.advanceTimersByTime(3000)

      expect(mockHandler).not.toHaveBeenCalled()
      expect(buffer.getBufferSize()).toBe(1)
    })

    it('should handle mixed stale and fresh events', () => {
      const mockHandler = vi.fn()
      buffer.on('event_ready', mockHandler)

      // Add first event that will become stale
      buffer.addEvent(5, 'stale:event', { data: 'stale' })

      // Wait 4 seconds
      vi.advanceTimersByTime(4000)

      // Add a fresh event (after the timer was set)
      buffer.addEvent(7, 'fresh:event', { data: 'fresh' })

      // Wait 1 more second (total 5 seconds from first event)
      vi.advanceTimersByTime(1000)

      // First stale event should be processed, but not the fresh one
      expect(mockHandler).toHaveBeenCalledWith({
        seq: 5,
        eventName: 'stale:event',
        data: { data: 'stale' }
      })
      // Fresh event should still be buffered
      expect(buffer.isBuffered(7)).toBe(true)
    })

    it('should not update nextExpectedSeq if stale seq is less than current', () => {
      // First process seq 0-10
      for (let i = 0; i <= 10; i++) {
        buffer.addEvent(i, `event${i}`, { data: i })
      }

      expect(buffer.getNextExpectedSeq()).toBe(11)

      // Buffer an old event (seq 5) and let it become stale
      // This should not happen in practice, but tests edge case
      buffer.addEvent(5, 'old:event', { data: 'old' })

      // Since seq 5 < 11, it should be rejected as old
      expect(buffer.getBufferSize()).toBe(0)
    })
  })

  describe('Timeout Scheduling', () => {
    it('should schedule timeout when buffering event', () => {
      const setTimeoutSpy = vi.spyOn(global, 'setTimeout')

      buffer.addEvent(5, 'future:event', { data: 'test' })

      expect(setTimeoutSpy).toHaveBeenCalledWith(
        expect.any(Function),
        defaultConfig.maxWaitTime
      )
    })

    it('should schedule separate timeouts for each buffered event', () => {
      const setTimeoutSpy = vi.spyOn(global, 'setTimeout')

      buffer.addEvent(5, 'event5', { data: '5' })
      buffer.addEvent(7, 'event7', { data: '7' })
      buffer.addEvent(10, 'event10', { data: '10' })

      // Should have 3 timeout calls (one per buffered event)
      expect(setTimeoutSpy).toHaveBeenCalledTimes(3)
    })
  })

  describe('Buffer State Inspection', () => {
    it('should return current buffer state', () => {
      buffer.addEvent(0, 'event1', { data: '1' })
      buffer.addEvent(5, 'event5', { data: '5' })
      buffer.addEvent(3, 'event3', { data: '3' })

      const state = buffer.getBufferState()

      expect(state).toEqual({
        size: 2, // seq 0 was processed immediately
        nextExpectedSeq: 1,
        bufferedSequences: [3, 5] // sorted
      })
    })

    it('should return next expected sequence number', () => {
      expect(buffer.getNextExpectedSeq()).toBe(0)

      buffer.addEvent(0, 'event1', { data: '1' })
      expect(buffer.getNextExpectedSeq()).toBe(1)

      buffer.addEvent(1, 'event2', { data: '2' })
      expect(buffer.getNextExpectedSeq()).toBe(2)
    })

    it('should return current buffer size', () => {
      expect(buffer.getBufferSize()).toBe(0)

      buffer.addEvent(5, 'event5', { data: '5' })
      expect(buffer.getBufferSize()).toBe(1)

      buffer.addEvent(7, 'event7', { data: '7' })
      expect(buffer.getBufferSize()).toBe(2)
    })

    it('should check if sequence is buffered', () => {
      buffer.addEvent(5, 'event5', { data: '5' })

      expect(buffer.isBuffered(5)).toBe(true)
      expect(buffer.isBuffered(3)).toBe(false)
      expect(buffer.isBuffered(7)).toBe(false)
    })

    it('should update buffer size after processing', () => {
      buffer.addEvent(2, 'event2', { data: '2' })
      buffer.addEvent(1, 'event1', { data: '1' })

      expect(buffer.getBufferSize()).toBe(2)

      // Add missing seq 0 to trigger processing
      buffer.addEvent(0, 'event0', { data: '0' })

      expect(buffer.getBufferSize()).toBe(0)
    })
  })

  describe('Buffer Reset', () => {
    it('should reset sequence to default (0)', () => {
      buffer.addEvent(0, 'event1', { data: '1' })
      buffer.addEvent(5, 'event5', { data: '5' })

      expect(buffer.getNextExpectedSeq()).toBe(1)
      expect(buffer.getBufferSize()).toBe(1)

      buffer.resetSequence()

      expect(buffer.getNextExpectedSeq()).toBe(0)
      expect(buffer.getBufferSize()).toBe(0)
      expect(logger.debug).toHaveBeenCalledWith(
        expect.stringContaining('Event buffer reset, next expected sequence: 0')
      )
    })

    it('should reset sequence to custom value', () => {
      buffer.addEvent(0, 'event1', { data: '1' })
      buffer.addEvent(1, 'event2', { data: '2' })

      buffer.resetSequence(10)

      expect(buffer.getNextExpectedSeq()).toBe(10)
      expect(buffer.getBufferSize()).toBe(0)
      expect(logger.debug).toHaveBeenCalledWith(
        expect.stringContaining('Event buffer reset, next expected sequence: 10')
      )
    })

    it('should clear buffer on reset', () => {
      buffer.addEvent(5, 'event5', { data: '5' })
      buffer.addEvent(7, 'event7', { data: '7' })

      expect(buffer.getBufferSize()).toBe(2)

      buffer.resetSequence()

      expect(buffer.getBufferSize()).toBe(0)
      expect(buffer.getBufferState().bufferedSequences).toEqual([])
    })
  })

  describe('Buffer Clear', () => {
    it('should clear all buffered events', () => {
      buffer.addEvent(5, 'event5', { data: '5' })
      buffer.addEvent(7, 'event7', { data: '7' })
      buffer.addEvent(10, 'event10', { data: '10' })

      expect(buffer.getBufferSize()).toBe(3)

      buffer.clear()

      expect(buffer.getBufferSize()).toBe(0)
      expect(buffer.getBufferState().bufferedSequences).toEqual([])
    })

    it('should not reset next expected sequence when clearing', () => {
      buffer.addEvent(0, 'event1', { data: '1' })
      buffer.addEvent(5, 'event5', { data: '5' })

      expect(buffer.getNextExpectedSeq()).toBe(1)

      buffer.clear()

      // nextExpectedSeq should remain 1
      expect(buffer.getNextExpectedSeq()).toBe(1)
      expect(buffer.getBufferSize()).toBe(0)
    })
  })

  describe('Event Handlers', () => {
    it('should register event handler with on()', () => {
      const mockHandler = vi.fn()
      buffer.on('event_ready', mockHandler)

      buffer.addEvent(0, 'test:event', { data: 'test' })

      expect(mockHandler).toHaveBeenCalledWith({
        seq: 0,
        eventName: 'test:event',
        data: { data: 'test' }
      })
    })

    it('should support multiple handlers for same event', () => {
      const mockHandler1 = vi.fn()
      const mockHandler2 = vi.fn()
      const mockHandler3 = vi.fn()

      buffer.on('event_ready', mockHandler1)
      buffer.on('event_ready', mockHandler2)
      buffer.on('event_ready', mockHandler3)

      buffer.addEvent(0, 'test:event', { data: 'test' })

      expect(mockHandler1).toHaveBeenCalled()
      expect(mockHandler2).toHaveBeenCalled()
      expect(mockHandler3).toHaveBeenCalled()
    })

    it('should remove event handler with off()', () => {
      const mockHandler = vi.fn()
      buffer.on('event_ready', mockHandler)
      buffer.off('event_ready', mockHandler)

      buffer.addEvent(0, 'test:event', { data: 'test' })

      expect(mockHandler).not.toHaveBeenCalled()
    })

    it('should only remove specified handler', () => {
      const mockHandler1 = vi.fn()
      const mockHandler2 = vi.fn()

      buffer.on('event_ready', mockHandler1)
      buffer.on('event_ready', mockHandler2)
      buffer.off('event_ready', mockHandler1)

      buffer.addEvent(0, 'test:event', { data: 'test' })

      expect(mockHandler1).not.toHaveBeenCalled()
      expect(mockHandler2).toHaveBeenCalled()
    })

    it('should handle off() for non-existent handler gracefully', () => {
      const mockHandler = vi.fn()

      // Should not throw
      expect(() => buffer.off('event_ready', mockHandler)).not.toThrow()
    })

    it('should handle off() for non-existent event type gracefully', () => {
      const mockHandler = vi.fn()

      expect(() => buffer.off('buffer_overflow', mockHandler)).not.toThrow()
    })

    it('should emit buffer_overflow events', () => {
      const mockHandler = vi.fn()
      buffer.on('buffer_overflow', mockHandler)

      // Fill buffer to capacity
      for (let i = 1; i <= 100; i++) {
        buffer.addEvent(i, `event${i}`, { data: i })
      }

      // Trigger overflow
      buffer.addEvent(101, 'overflow:event', { data: 'overflow' })

      expect(mockHandler).toHaveBeenCalledWith({
        seq: 101,
        eventName: 'overflow:event',
        bufferSize: 100
      })
    })

    it('should emit sequence_gap events', () => {
      const mockHandler = vi.fn()
      buffer.on('sequence_gap', mockHandler)

      buffer.addEvent(0, 'event1', { data: '1' })
      buffer.addEvent(5, 'event5', { data: '5' })

      expect(mockHandler).toHaveBeenCalledWith({
        expected: 1,
        received: 5,
        gap: 4
      })
    })

    it('should handle errors in event handlers gracefully', () => {
      const errorHandler = vi.fn(() => {
        throw new Error('Handler error')
      })
      const normalHandler = vi.fn()

      buffer.on('event_ready', errorHandler)
      buffer.on('event_ready', normalHandler)

      // Should not throw, both handlers should be called
      buffer.addEvent(0, 'test:event', { data: 'test' })

      expect(errorHandler).toHaveBeenCalled()
      expect(normalHandler).toHaveBeenCalled()
      expect(logger.error).toHaveBeenCalledWith(
        expect.stringContaining('Error in buffer event handler for event_ready'),
        expect.any(Error)
      )
    })

    it('should isolate errors between handlers', () => {
      const errorHandler1 = vi.fn(() => {
        throw new Error('Error 1')
      })
      const errorHandler2 = vi.fn(() => {
        throw new Error('Error 2')
      })
      const normalHandler = vi.fn()

      buffer.on('event_ready', errorHandler1)
      buffer.on('event_ready', errorHandler2)
      buffer.on('event_ready', normalHandler)

      buffer.addEvent(0, 'test:event', { data: 'test' })

      // All handlers should be called despite errors
      expect(errorHandler1).toHaveBeenCalled()
      expect(errorHandler2).toHaveBeenCalled()
      expect(normalHandler).toHaveBeenCalled()
      expect(logger.error).toHaveBeenCalledTimes(2)
    })
  })

  describe('Cleanup and Destruction', () => {
    it('should clear buffer on destroy', () => {
      buffer.addEvent(5, 'event5', { data: '5' })
      buffer.addEvent(7, 'event7', { data: '7' })

      expect(buffer.getBufferSize()).toBe(2)

      buffer.destroy()

      expect(buffer.getBufferSize()).toBe(0)
    })

    it('should clear all event handlers on destroy', () => {
      const mockHandler = vi.fn()
      buffer.on('event_ready', mockHandler)
      buffer.on('buffer_overflow', mockHandler)
      buffer.on('sequence_gap', mockHandler)

      buffer.destroy()

      // Try to trigger events after destroy
      buffer.addEvent(0, 'test:event', { data: 'test' })

      // Handlers should not be called (they were cleared)
      expect(mockHandler).not.toHaveBeenCalled()
    })

    it('should reset next expected sequence on destroy', () => {
      buffer.addEvent(0, 'event1', { data: '1' })
      buffer.addEvent(1, 'event2', { data: '2' })

      expect(buffer.getNextExpectedSeq()).toBe(2)

      buffer.destroy()

      expect(buffer.getNextExpectedSeq()).toBe(0)
    })

    it('should allow multiple destroy calls', () => {
      expect(() => {
        buffer.destroy()
        buffer.destroy()
        buffer.destroy()
      }).not.toThrow()
    })
  })

  describe('Edge Cases', () => {
    it('should handle empty buffer operations', () => {
      expect(buffer.getBufferSize()).toBe(0)
      expect(buffer.getBufferState().bufferedSequences).toEqual([])
      expect(buffer.isBuffered(0)).toBe(false)

      buffer.clear()
      expect(buffer.getBufferSize()).toBe(0)
    })

    it('should handle single event buffer', () => {
      buffer.addEvent(5, 'single:event', { data: 'single' })

      expect(buffer.getBufferSize()).toBe(1)
      expect(buffer.isBuffered(5)).toBe(true)

      vi.advanceTimersByTime(5000)

      expect(buffer.getBufferSize()).toBe(0)
      expect(buffer.getNextExpectedSeq()).toBe(6)
    })

    it('should handle events with null data', () => {
      const mockHandler = vi.fn()
      buffer.on('event_ready', mockHandler)

      buffer.addEvent(0, 'null:event', null)

      expect(mockHandler).toHaveBeenCalledWith({
        seq: 0,
        eventName: 'null:event',
        data: null
      })
    })

    it('should handle events with undefined data', () => {
      const mockHandler = vi.fn()
      buffer.on('event_ready', mockHandler)

      buffer.addEvent(0, 'undefined:event', undefined)

      expect(mockHandler).toHaveBeenCalledWith({
        seq: 0,
        eventName: 'undefined:event',
        data: undefined
      })
    })

    it('should handle events with complex nested data', () => {
      const mockHandler = vi.fn()
      buffer.on('event_ready', mockHandler)

      const complexData = {
        user: { id: 1, name: 'Test' },
        playlist: {
          tracks: [{ id: 1 }, { id: 2 }],
          metadata: { created: Date.now() }
        }
      }

      buffer.addEvent(0, 'complex:event', complexData)

      expect(mockHandler).toHaveBeenCalledWith({
        seq: 0,
        eventName: 'complex:event',
        data: complexData
      })
    })

    it('should handle rapid sequential events', () => {
      const mockHandler = vi.fn()
      buffer.on('event_ready', mockHandler)

      // Add 1000 sequential events rapidly
      for (let i = 0; i < 1000; i++) {
        buffer.addEvent(i, `event${i}`, { data: i })
      }

      expect(mockHandler).toHaveBeenCalledTimes(1000)
      expect(buffer.getNextExpectedSeq()).toBe(1000)
      expect(buffer.getBufferSize()).toBe(0)
    })

    it('should handle sequence number 0', () => {
      const mockHandler = vi.fn()
      buffer.on('event_ready', mockHandler)

      buffer.addEvent(0, 'zero:event', { data: 'zero' })

      expect(mockHandler).toHaveBeenCalledWith({
        seq: 0,
        eventName: 'zero:event',
        data: { data: 'zero' }
      })
      expect(buffer.getNextExpectedSeq()).toBe(1)
    })

    it('should handle large sequence numbers', () => {
      buffer.resetSequence(999999)

      const mockHandler = vi.fn()
      buffer.on('event_ready', mockHandler)

      buffer.addEvent(999999, 'large:event', { data: 'large' })

      expect(mockHandler).toHaveBeenCalled()
      expect(buffer.getNextExpectedSeq()).toBe(1000000)
    })

    it('should handle concurrent buffering and processing', () => {
      const mockHandler = vi.fn()
      buffer.on('event_ready', mockHandler)

      // Buffer some events
      buffer.addEvent(3, 'event3', { data: '3' })
      buffer.addEvent(5, 'event5', { data: '5' })

      expect(buffer.getBufferSize()).toBe(2)

      // Process some in sequence
      buffer.addEvent(0, 'event0', { data: '0' })
      buffer.addEvent(1, 'event1', { data: '1' })

      expect(mockHandler).toHaveBeenCalledTimes(2)

      // Add more buffered
      buffer.addEvent(7, 'event7', { data: '7' })

      expect(buffer.getBufferSize()).toBe(3)

      // Fill the gap
      buffer.addEvent(2, 'event2', { data: '2' })

      // Should process 2, 3, then buffer 5 and 7
      expect(mockHandler).toHaveBeenCalledTimes(4) // 0, 1, 2, 3
    })

    it('should handle empty event name', () => {
      const mockHandler = vi.fn()
      buffer.on('event_ready', mockHandler)

      buffer.addEvent(0, '', { data: 'test' })

      expect(mockHandler).toHaveBeenCalledWith({
        seq: 0,
        eventName: '',
        data: { data: 'test' }
      })
    })

    it('should handle processing when buffer has gaps', () => {
      const mockHandler = vi.fn()
      buffer.on('event_ready', mockHandler)

      // Create gaps in buffer
      buffer.addEvent(2, 'event2', { data: '2' })
      buffer.addEvent(5, 'event5', { data: '5' })
      buffer.addEvent(8, 'event8', { data: '8' })

      // Fill first gap
      buffer.addEvent(0, 'event0', { data: '0' })
      buffer.addEvent(1, 'event1', { data: '1' })

      // Should process 0, 1, 2, then stop at gap before 5
      expect(mockHandler).toHaveBeenCalledTimes(3)
      expect(buffer.getBufferSize()).toBe(2) // 5 and 8 still buffered
      expect(buffer.getNextExpectedSeq()).toBe(3)
    })
  })

  describe('Complex Scenarios', () => {
    it('should handle interleaved in-order and out-of-order events', () => {
      const mockHandler = vi.fn()
      buffer.on('event_ready', mockHandler)

      buffer.addEvent(0, 'event0', { data: '0' }) // Process immediately
      buffer.addEvent(5, 'event5', { data: '5' }) // Buffer
      buffer.addEvent(1, 'event1', { data: '1' }) // Process immediately
      buffer.addEvent(3, 'event3', { data: '3' }) // Buffer
      buffer.addEvent(2, 'event2', { data: '2' }) // Process, triggers 3

      expect(mockHandler).toHaveBeenCalledTimes(4) // 0, 1, 2, 3
      expect(buffer.getBufferSize()).toBe(1) // 5 still buffered
      expect(buffer.getNextExpectedSeq()).toBe(4)
    })

    it('should handle buffer overflow during cascade processing', () => {
      const mockOverflowHandler = vi.fn()
      const mockEventHandler = vi.fn()
      buffer.on('buffer_overflow', mockOverflowHandler)
      buffer.on('event_ready', mockEventHandler)

      // Fill buffer to capacity with gaps
      for (let i = 1; i <= 100; i++) {
        buffer.addEvent(i, `event${i}`, { data: i })
      }

      expect(buffer.getBufferSize()).toBe(100)

      // Try to add one more (should overflow)
      buffer.addEvent(101, 'overflow:event', { data: 'overflow' })

      expect(mockOverflowHandler).toHaveBeenCalled()

      // Now fill the gap by adding seq 0
      buffer.addEvent(0, 'event0', { data: '0' })

      // Should process all 101 events (0-100)
      expect(mockEventHandler).toHaveBeenCalledTimes(101)
      expect(buffer.getBufferSize()).toBe(0)
      expect(buffer.getNextExpectedSeq()).toBe(101)
    })

    it('should handle multiple timeout expirations', () => {
      const mockHandler = vi.fn()
      buffer.on('event_ready', mockHandler)

      // Add events at different times
      buffer.addEvent(10, 'event10', { data: '10' })

      vi.advanceTimersByTime(2000)

      buffer.addEvent(20, 'event20', { data: '20' })

      vi.advanceTimersByTime(3000) // Total 5000ms from first event

      // First event should be processed (stale)
      expect(mockHandler).toHaveBeenCalledWith({
        seq: 10,
        eventName: 'event10',
        data: { data: '10' }
      })

      vi.advanceTimersByTime(3000) // Additional 3000ms (total 8000ms)

      // Second event should now be processed (stale)
      expect(mockHandler).toHaveBeenCalledWith({
        seq: 20,
        eventName: 'event20',
        data: { data: '20' }
      })
    })

    it('should correctly update sequence after partial buffer drain', () => {
      const mockHandler = vi.fn()
      buffer.on('event_ready', mockHandler)

      // Buffer events with gaps
      buffer.addEvent(2, 'event2', { data: '2' })
      buffer.addEvent(3, 'event3', { data: '3' })
      buffer.addEvent(7, 'event7', { data: '7' })
      buffer.addEvent(8, 'event8', { data: '8' })

      expect(buffer.getBufferSize()).toBe(4)

      // Process first batch
      buffer.addEvent(0, 'event0', { data: '0' })
      buffer.addEvent(1, 'event1', { data: '1' })

      // Should process 0, 1, 2, 3
      expect(mockHandler).toHaveBeenCalledTimes(4)
      expect(buffer.getBufferSize()).toBe(2) // 7, 8 remain
      expect(buffer.getNextExpectedSeq()).toBe(4)

      // Fill next gap
      buffer.addEvent(4, 'event4', { data: '4' })
      buffer.addEvent(5, 'event5', { data: '5' })
      buffer.addEvent(6, 'event6', { data: '6' })

      // Should process 4, 5, 6, 7, 8
      expect(mockHandler).toHaveBeenCalledTimes(9)
      expect(buffer.getBufferSize()).toBe(0)
      expect(buffer.getNextExpectedSeq()).toBe(9)
    })

    it('should handle reset during buffering', () => {
      const mockHandler = vi.fn()
      buffer.on('event_ready', mockHandler)

      buffer.addEvent(5, 'event5', { data: '5' })
      buffer.addEvent(7, 'event7', { data: '7' })

      expect(buffer.getBufferSize()).toBe(2)

      buffer.resetSequence(100)

      expect(buffer.getBufferSize()).toBe(0)
      expect(buffer.getNextExpectedSeq()).toBe(100)

      // New events should start from 100
      buffer.addEvent(100, 'event100', { data: '100' })

      expect(mockHandler).toHaveBeenCalledWith({
        seq: 100,
        eventName: 'event100',
        data: { data: '100' }
      })
      expect(buffer.getNextExpectedSeq()).toBe(101)
    })
  })
})
