/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Connection Manager
 *
 * Single Responsibility: Manage Socket.IO connection lifecycle
 * - Connect/disconnect
 * - Connection status tracking
 * - Reconnection attempts
 */

import { Socket } from 'socket.io-client'
import { logger } from '@/utils/logger'

export interface ConnectionStatus {
  connected: boolean
  ready: boolean
  lastSeq: number
  serverId?: string
  serverTime?: number
}

export interface ConnectionConfig {
  maxReconnectionAttempts: number
  reconnectionDelay: number
}

export type ConnectionEventType = 'connected' | 'disconnected' | 'reconnecting' | 'connection_failed' | 'ready'

export class ConnectionManager {
  private status: ConnectionStatus = {
    connected: false,
    ready: false,
    lastSeq: 0
  }

  private reconnectionAttempts = 0
  private eventHandlers = new Map<ConnectionEventType, Set<(data?: any) => void>>()

  constructor(private config: ConnectionConfig) {}

  /**
   * Setup connection event handlers on socket
   */
  setupHandlers(socket: Socket): void {
    socket.on('connect', () => {
      logger.info('🔊🎵 ✅ SOCKET CONNECTED SUCCESSFULLY!', {
        id: socket.id
      })
      this.status.connected = true
      this.reconnectionAttempts = 0
      this.emit('connected', { socketId: socket.id })
    })

    socket.on('disconnect', (reason) => {
      logger.warn(`Socket disconnected: ${reason}`)
      this.status.connected = false
      this.status.ready = false
      this.emit('disconnected', { reason })
    })

    socket.on('connect_error', (error) => {
      logger.error('🔊🎵 ❌ SOCKET CONNECTION ERROR:', {
        message: error.message,
        type: (error as any).type || 'unknown',
        attempt: this.reconnectionAttempts + 1
      })
      this.reconnectionAttempts++

      this.emit('reconnecting', {
        attempt: this.reconnectionAttempts,
        error: error.message
      })

      if (this.reconnectionAttempts >= this.config.maxReconnectionAttempts) {
        logger.error('Max reconnection attempts reached')
        this.emit('connection_failed', { error })
      }
    })

    socket.on('reconnect', (attemptNumber) => {
      logger.info(`Socket reconnected after ${attemptNumber} attempts`)
      this.reconnectionAttempts = 0
      this.emit('connected', { socketId: socket.id, reconnected: true })
    })

    // Connection status event from server
    socket.on('connection_status', (data: any) => {
      logger.debug('Received connection status:', data)
      this.status.ready = true
      this.status.serverId = data.sid
      this.status.lastSeq = data.server_seq
      this.status.serverTime = data.server_time
      this.emit('ready', data)
    })
  }

  /**
   * Get current connection status
   */
  getStatus(): Readonly<ConnectionStatus> {
    return { ...this.status }
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.status.connected
  }

  /**
   * Check if ready (connected + received status from server)
   */
  isReady(): boolean {
    return this.status.ready
  }

  /**
   * Get reconnection attempt count
   */
  getReconnectionAttempts(): number {
    return this.reconnectionAttempts
  }

  /**
   * Update last sequence number
   */
  updateLastSeq(seq: number): void {
    if (seq > this.status.lastSeq) {
      this.status.lastSeq = seq
    }
  }

  /**
   * Get last server sequence
   */
  getLastSeq(): number {
    return this.status.lastSeq
  }

  /**
   * Reset connection state
   */
  reset(): void {
    this.status = {
      connected: false,
      ready: false,
      lastSeq: 0
    }
    this.reconnectionAttempts = 0
  }

  /**
   * Event subscription
   */
  on(event: ConnectionEventType, handler: (data?: any) => void): void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, new Set())
    }
    this.eventHandlers.get(event)!.add(handler)
  }

  /**
   * Remove event listener
   */
  off(event: ConnectionEventType, handler: (data?: any) => void): void {
    const handlers = this.eventHandlers.get(event)
    if (handlers) {
      handlers.delete(handler)
    }
  }

  /**
   * Emit event to handlers
   */
  private emit(event: ConnectionEventType, data?: any): void {
    const handlers = this.eventHandlers.get(event)
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(data)
        } catch (error) {
          logger.error(`Error in connection event handler for ${event}:`, error)
        }
      })
    }
  }

  /**
   * Cleanup
   */
  destroy(): void {
    this.eventHandlers.clear()
    this.reset()
  }
}
