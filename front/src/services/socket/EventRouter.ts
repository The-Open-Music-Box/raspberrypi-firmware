/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Event Router
 *
 * Single Responsibility: Manage event subscription and dispatching
 * - Register event handlers (on/off/once)
 * - Dispatch events to registered handlers
 * - Dispatch DOM events for cross-component communication
 * - Handle errors in event handlers gracefully
 */

import { logger } from '@/utils/logger'

export type EventHandler = (...args: any[]) => void

export class EventRouter {
  private handlers = new Map<string, Set<EventHandler>>()
  private enableDOMEvents: boolean

  constructor(options: { enableDOMEvents?: boolean } = {}) {
    this.enableDOMEvents = options.enableDOMEvents ?? true
  }

  /**
   * Register event handler
   */
  on(event: string, handler: EventHandler): void {
    if (!this.handlers.has(event)) {
      this.handlers.set(event, new Set())
    }
    this.handlers.get(event)!.add(handler)
  }

  /**
   * Register one-time event handler
   */
  once(event: string, handler: EventHandler): void {
    const onceWrapper: EventHandler = (...args: any[]) => {
      this.off(event, onceWrapper)
      handler(...args)
    }
    this.on(event, onceWrapper)
  }

  /**
   * Remove event handler
   */
  off(event: string, handler: EventHandler): void {
    const eventHandlers = this.handlers.get(event)
    if (eventHandlers) {
      eventHandlers.delete(handler)
      if (eventHandlers.size === 0) {
        this.handlers.delete(event)
      }
    }
  }

  /**
   * Remove all handlers for an event
   */
  removeAllListeners(event?: string): void {
    if (event) {
      this.handlers.delete(event)
    } else {
      this.handlers.clear()
    }
  }

  /**
   * Emit event to registered handlers
   */
  emit(event: string, ...args: any[]): void {
    const eventHandlers = this.handlers.get(event)
    if (eventHandlers) {
      eventHandlers.forEach(handler => {
        try {
          handler(...args)
        } catch (error) {
          logger.error(`Error in event handler for ${event}:`, error)
        }
      })
    }
  }

  /**
   * Dispatch event as DOM CustomEvent
   */
  dispatchDOMEvent(eventType: string, data: any): void {
    if (!this.enableDOMEvents) {
      return
    }

    try {
      const domEvent = new CustomEvent(eventType, {
        detail: data,
        bubbles: false,
        cancelable: false
      })
      window.dispatchEvent(domEvent)

      logger.debug(`DOM event dispatched: ${eventType}`)
    } catch (error) {
      logger.error(`Failed to dispatch DOM event ${eventType}:`, error)
    }
  }

  /**
   * Emit event to both local handlers and DOM
   */
  broadcast(event: string, data: any): void {
    this.emit(event, data)
    this.dispatchDOMEvent(event, data)
  }

  /**
   * Get count of handlers for an event
   */
  getHandlerCount(event: string): number {
    return this.handlers.get(event)?.size ?? 0
  }

  /**
   * Get all registered event names
   */
  getEventNames(): string[] {
    return Array.from(this.handlers.keys())
  }

  /**
   * Check if event has any handlers
   */
  hasHandlers(event: string): boolean {
    const eventHandlers = this.handlers.get(event)
    return eventHandlers ? eventHandlers.size > 0 : false
  }

  /**
   * Get total number of registered handlers across all events
   */
  getTotalHandlerCount(): number {
    let total = 0
    this.handlers.forEach(handlers => {
      total += handlers.size
    })
    return total
  }

  /**
   * Clear all handlers and reset
   */
  destroy(): void {
    this.handlers.clear()
  }
}
