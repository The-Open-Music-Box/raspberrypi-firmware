/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Event Buffer
 *
 * Single Responsibility: Buffer and order events by sequence number
 * - Buffer out-of-order events
 * - Process buffered events in order
 * - Manage buffer size limits
 * - Track sequence numbers
 */

import { logger } from '@/utils/logger'

export interface BufferedEvent {
  seq: number
  eventName: string
  data: any
  receivedAt: number
}

export interface EventBufferConfig {
  maxBufferSize: number
  maxWaitTime: number // milliseconds to wait for missing sequences
}

export type BufferEventType = 'event_ready' | 'buffer_overflow' | 'sequence_gap'

export class EventBuffer {
  private buffer: Map<number, BufferedEvent> = new Map()
  private nextExpectedSeq = 0
  private eventHandlers = new Map<BufferEventType, Set<(data?: any) => void>>()
  private config: EventBufferConfig

  constructor(config: EventBufferConfig = { maxBufferSize: 100, maxWaitTime: 5000 }) {
    this.config = config
  }

  /**
   * Add event to buffer and process if ready
   */
  addEvent(seq: number, eventName: string, data: any): void {
    // If this is the next expected sequence, process immediately
    if (seq === this.nextExpectedSeq) {
      this.processEvent(seq, eventName, data)
      this.nextExpectedSeq++
      this.processBufferedEvents()
      return
    }

    // If sequence is in the past, log warning and skip
    if (seq < this.nextExpectedSeq) {
      logger.warn(`Received old sequence ${seq}, expected ${this.nextExpectedSeq}`)
      return
    }

    // Future sequence - buffer it
    this.bufferEvent(seq, eventName, data)
  }

  /**
   * Buffer an out-of-order event
   */
  private bufferEvent(seq: number, eventName: string, data: any): void {
    // Check buffer size limit
    if (this.buffer.size >= this.config.maxBufferSize) {
      logger.error(`Event buffer overflow, dropping event seq ${seq}`)
      this.emit('buffer_overflow', { seq, eventName, bufferSize: this.buffer.size })
      return
    }

    // Add to buffer
    const bufferedEvent: BufferedEvent = {
      seq,
      eventName,
      data,
      receivedAt: Date.now()
    }

    this.buffer.set(seq, bufferedEvent)

    // Emit sequence gap warning
    const gap = seq - this.nextExpectedSeq
    if (gap > 1) {
      logger.warn(`Sequence gap detected: expected ${this.nextExpectedSeq}, received ${seq} (gap: ${gap})`)
      this.emit('sequence_gap', {
        expected: this.nextExpectedSeq,
        received: seq,
        gap
      })
    }

    // Set timeout to process buffered events even if gap persists
    setTimeout(() => {
      this.checkStaleEvents()
    }, this.config.maxWaitTime)
  }

  /**
   * Process buffered events in sequence
   */
  private processBufferedEvents(): void {
    while (this.buffer.has(this.nextExpectedSeq)) {
      const event = this.buffer.get(this.nextExpectedSeq)!
      this.buffer.delete(this.nextExpectedSeq)

      this.processEvent(event.seq, event.eventName, event.data)
      this.nextExpectedSeq++
    }
  }

  /**
   * Process a single event
   */
  private processEvent(seq: number, eventName: string, data: any): void {
    this.emit('event_ready', { seq, eventName, data })
  }

  /**
   * Check for stale events and process them if wait time exceeded
   */
  private checkStaleEvents(): void {
    const now = Date.now()
    const staleEvents: BufferedEvent[] = []

    // Find events that have waited too long
    this.buffer.forEach(event => {
      if (now - event.receivedAt >= this.config.maxWaitTime) {
        staleEvents.push(event)
      }
    })

    if (staleEvents.length === 0) {
      return
    }

    // Sort by sequence and process
    staleEvents.sort((a, b) => a.seq - b.seq)

    logger.warn(
      `Processing ${staleEvents.length} stale events after wait timeout, ` +
      `expected seq: ${this.nextExpectedSeq}, processing from: ${staleEvents[0].seq}`
    )

    staleEvents.forEach(event => {
      this.buffer.delete(event.seq)
      this.processEvent(event.seq, event.eventName, event.data)
    })

    // Update next expected sequence to after the last processed stale event
    const lastProcessedSeq = staleEvents[staleEvents.length - 1].seq
    if (lastProcessedSeq >= this.nextExpectedSeq) {
      this.nextExpectedSeq = lastProcessedSeq + 1
    }

    // Try to process any remaining buffered events
    this.processBufferedEvents()
  }

  /**
   * Reset sequence tracking
   */
  resetSequence(startSeq = 0): void {
    this.nextExpectedSeq = startSeq
    this.buffer.clear()
    logger.debug(`Event buffer reset, next expected sequence: ${startSeq}`)
  }

  /**
   * Get current buffer state
   */
  getBufferState(): {
    size: number
    nextExpectedSeq: number
    bufferedSequences: number[]
  } {
    return {
      size: this.buffer.size,
      nextExpectedSeq: this.nextExpectedSeq,
      bufferedSequences: Array.from(this.buffer.keys()).sort((a, b) => a - b)
    }
  }

  /**
   * Get next expected sequence number
   */
  getNextExpectedSeq(): number {
    return this.nextExpectedSeq
  }

  /**
   * Get buffer size
   */
  getBufferSize(): number {
    return this.buffer.size
  }

  /**
   * Check if sequence is buffered
   */
  isBuffered(seq: number): boolean {
    return this.buffer.has(seq)
  }

  /**
   * Event subscription
   */
  on(event: BufferEventType, handler: (data?: any) => void): void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, new Set())
    }
    this.eventHandlers.get(event)!.add(handler)
  }

  /**
   * Remove event listener
   */
  off(event: BufferEventType, handler: (data?: any) => void): void {
    const handlers = this.eventHandlers.get(event)
    if (handlers) {
      handlers.delete(handler)
    }
  }

  /**
   * Emit event to handlers
   */
  private emit(event: BufferEventType, data?: any): void {
    const handlers = this.eventHandlers.get(event)
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(data)
        } catch (error) {
          logger.error(`Error in buffer event handler for ${event}:`, error)
        }
      })
    }
  }

  /**
   * Clear buffer
   */
  clear(): void {
    this.buffer.clear()
  }

  /**
   * Cleanup
   */
  destroy(): void {
    this.buffer.clear()
    this.eventHandlers.clear()
    this.nextExpectedSeq = 0
  }
}
