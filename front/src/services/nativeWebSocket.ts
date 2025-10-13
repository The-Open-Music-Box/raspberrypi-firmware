/**
 * Native WebSocket Client for ESP32
 *
 * Implements plain WebSocket (RFC 6455) connection for ESP32 devices.
 * ESP32 uses AsyncWebSocket which does NOT support Socket.IO protocol.
 *
 * Key differences from Socket.IO:
 * - No Engine.IO handshake (no ?EIO=4 parameters)
 * - No Socket.IO packet framing
 * - Raw JSON message format
 * - Manual reconnection logic
 * - Manual room subscription via JSON messages
 */

import { logger } from '../utils/logger'
import { StateEventEnvelope } from '../types/contracts'

export interface NativeWebSocketConfig {
  url: string
  path?: string
  reconnectionAttempts?: number
  reconnectionDelay?: number
  reconnectionDelayMax?: number
  timeout?: number
}

export type ConnectionStatus = {
  connected: boolean
  ready: boolean
  lastSeq: number
  serverId?: string
  serverTime?: number
}

export class NativeWebSocketClient {
  private ws: WebSocket | null = null
  private config: NativeWebSocketConfig
  private eventHandlers = new Map<string, Set<(...args: any[]) => void>>()
  private connectionStatus: ConnectionStatus = {
    connected: false,
    ready: false,
    lastSeq: 0
  }
  private reconnectionAttempts = 0
  private reconnectTimeout?: ReturnType<typeof setTimeout>
  private pingInterval?: ReturnType<typeof setInterval>
  private subscribedRooms = new Set<string>()
  private isDestroyed = false

  constructor(config: NativeWebSocketConfig) {
    this.config = {
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      timeout: 10000,
      ...config
    }
  }

  /**
   * Connect to ESP32 WebSocket server
   */
  connect(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      logger.warn('WebSocket already connected')
      return
    }

    const wsUrl = this.buildWebSocketUrl()
    logger.info(`[NativeWS] Connecting to ESP32: ${wsUrl}`)

    try {
      this.ws = new WebSocket(wsUrl)
      this.setupWebSocketHandlers()
    } catch (error) {
      logger.error('[NativeWS] Failed to create WebSocket:', error)
      this.scheduleReconnect()
    }
  }

  /**
   * Build clean WebSocket URL without Socket.IO parameters
   */
  private buildWebSocketUrl(): string {
    const url = new URL(this.config.url)
    const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
    const path = this.config.path || '/ws'

    // Build clean WebSocket URL (no query parameters!)
    return `${protocol}//${url.host}${path}`
  }

  /**
   * Setup WebSocket event handlers
   */
  private setupWebSocketHandlers(): void {
    if (!this.ws) return

    this.ws.onopen = () => {
      logger.info('[NativeWS] ✅ Connected to ESP32 via plain WebSocket')
      this.connectionStatus.connected = true
      this.reconnectionAttempts = 0
      this.emitLocal('internal:connection_changed', { connected: true })
      this.startPingInterval()

      // Resubscribe to rooms after connection
      this.resubscribeToRooms()
    }

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        this.handleMessage(data)
      } catch (error) {
        logger.error('[NativeWS] Failed to parse message:', error, event.data)
      }
    }

    this.ws.onerror = (error) => {
      logger.error('[NativeWS] WebSocket error:', error)
      this.emitLocal('internal:connection_error', { error })
    }

    this.ws.onclose = (event) => {
      logger.warn('[NativeWS] Disconnected:', {
        code: event.code,
        reason: event.reason || 'No reason provided',
        wasClean: event.wasClean
      })

      this.connectionStatus.connected = false
      this.connectionStatus.ready = false
      this.stopPingInterval()
      this.emitLocal('internal:connection_changed', { connected: false, reason: event.reason })

      if (!this.isDestroyed) {
        this.scheduleReconnect()
      }
    }
  }

  /**
   * Handle incoming messages from ESP32
   */
  private handleMessage(data: any): void {
    // ESP32 sends different message types:
    // 1. Connection status: {status: "connected", sid: "...", server_seq: N}
    // 2. State events: {event_type: "...", data: {...}, server_seq: N, timestamp: "..."}
    // 3. Room acks: {room: "...", success: true, server_seq: N}
    // 4. Operation acks: {client_op_id: "...", success: true, ...}

    if (data.status === 'connected') {
      // Connection status message
      logger.info('[NativeWS] Connection status received:', data)
      this.connectionStatus.ready = true
      this.connectionStatus.serverId = data.sid
      this.connectionStatus.lastSeq = data.server_seq || 0
      this.emitLocal('connection_status', data)
    } else if (data.event_type) {
      // State event envelope
      const envelope = data as StateEventEnvelope
      logger.debug(`[NativeWS] State event received: ${envelope.event_type} (seq: ${envelope.server_seq})`)

      // Update sequence counter
      if (envelope.server_seq) {
        this.connectionStatus.lastSeq = Math.max(
          this.connectionStatus.lastSeq,
          envelope.server_seq
        )
      }

      // Emit to local handlers
      this.emitLocal(envelope.event_type, envelope)

      // Also dispatch as DOM event for compatibility with existing stores
      this.dispatchDOMEvent(envelope.event_type, envelope)
    } else if (data.room !== undefined && data.success !== undefined) {
      // Room join/leave acknowledgment
      const eventType = data.success ? 'ack:join' : 'ack:leave'
      logger.debug(`[NativeWS] Room ${eventType}: ${data.room} - ${data.success}`)

      if (data.success) {
        this.subscribedRooms.add(data.room)
      } else {
        this.subscribedRooms.delete(data.room)
      }

      this.emitLocal(eventType, data)
    } else if (data.client_op_id !== undefined) {
      // Operation acknowledgment or error
      const eventType = data.success ? 'ack:op' : 'err:op'
      logger.debug(`[NativeWS] Operation ${eventType}: ${data.client_op_id}`)
      this.emitLocal(eventType, data)
    } else if (data.event === 'pong' || data.event === 'client_pong') {
      // Ping/pong response (both formats supported)
      logger.debug('[NativeWS] Pong received:', data)
    } else {
      // Unknown message type - log for debugging
      logger.warn('[NativeWS] Unknown message type:', data)
    }
  }

  /**
   * Dispatch DOM event for compatibility with existing stores
   */
  private dispatchDOMEvent(eventType: string, envelope: StateEventEnvelope): void {
    try {
      const domEvent = new CustomEvent(eventType, {
        detail: envelope,
        bubbles: false,
        cancelable: false
      })
      window.dispatchEvent(domEvent)
      logger.debug(`[NativeWS] DOM event dispatched: ${eventType}`)
    } catch (error) {
      logger.error(`[NativeWS] Failed to dispatch DOM event ${eventType}:`, error)
    }
  }

  /**
   * Send message to ESP32
   */
  private send(data: any): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      logger.warn('[NativeWS] Cannot send message: not connected')
      return
    }

    try {
      const json = JSON.stringify(data)
      this.ws.send(json)
      logger.debug('[NativeWS] Message sent:', data)
    } catch (error) {
      logger.error('[NativeWS] Failed to send message:', error)
    }
  }

  /**
   * Join a room for receiving specific events
   */
  async joinRoom(room: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error(`[NativeWS] Join room timeout: ${room}`))
      }, this.config.timeout!)

      const successHandler = (data: any) => {
        if (data.room === room) {
          clearTimeout(timeout)
          this.off('ack:join', successHandler)

          if (data.success) {
            resolve()
          } else {
            reject(new Error(data.message || `Failed to join room: ${room}`))
          }
        }
      }

      this.on('ack:join', successHandler)

      // Send room join message
      // ESP32 expects: {event: "join:playlists"} or {event: "join:playlist", playlist_id: "..."}
      if (room === 'playlists') {
        this.send({ event: 'join:playlists' })
      } else if (room.startsWith('playlist:')) {
        const playlistId = room.replace('playlist:', '')
        this.send({ event: 'join:playlist', playlist_id: playlistId })
      } else if (room === 'nfc') {
        this.send({ event: 'join:nfc' })
      } else {
        this.send({ event: `join:${room}` })
      }
    })
  }

  /**
   * Leave a room
   */
  async leaveRoom(room: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error(`[NativeWS] Leave room timeout: ${room}`))
      }, this.config.timeout!)

      const successHandler = (data: any) => {
        if (data.room === room) {
          clearTimeout(timeout)
          this.off('ack:leave', successHandler)
          resolve()
        }
      }

      this.once('ack:leave', successHandler)

      // Send room leave message
      if (room === 'playlists') {
        this.send({ event: 'leave:playlists' })
      } else if (room.startsWith('playlist:')) {
        const playlistId = room.replace('playlist:', '')
        this.send({ event: 'leave:playlist', playlist_id: playlistId })
      } else if (room === 'nfc') {
        this.send({ event: 'leave:nfc' })
      } else {
        this.send({ event: `leave:${room}` })
      }
    })
  }

  /**
   * Send operation with acknowledgment tracking
   */
  async sendOperation(event: string, data: any, clientOpId: string): Promise<any> {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error(`[NativeWS] Operation timeout: ${event}`))
      }, 30000)

      const successHandler = (ack: any) => {
        if (ack.client_op_id === clientOpId) {
          clearTimeout(timeout)
          this.off('ack:op', successHandler)
          this.off('err:op', errorHandler)
          resolve(ack)
        }
      }

      const errorHandler = (err: any) => {
        if (err.client_op_id === clientOpId) {
          clearTimeout(timeout)
          this.off('ack:op', successHandler)
          this.off('err:op', errorHandler)
          reject(new Error(err.message || 'Operation failed'))
        }
      }

      this.on('ack:op', successHandler)
      this.on('err:op', errorHandler)

      // Send operation
      this.send({ event, ...data, client_op_id: clientOpId })
    })
  }

  /**
   * Emit generic event to server
   */
  emit(event: string, data: any): void {
    this.send({ event, ...data })
  }

  /**
   * Event subscription methods
   */
  on(event: string, handler: (...args: any[]) => void): void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, new Set())
    }
    this.eventHandlers.get(event)!.add(handler)
  }

  off(event: string, handler: (...args: any[]) => void): void {
    const handlers = this.eventHandlers.get(event)
    if (handlers) {
      handlers.delete(handler)
      if (handlers.size === 0) {
        this.eventHandlers.delete(event)
      }
    }
  }

  once(event: string, handler: (...args: any[]) => void): void {
    const onceHandler = (...args: any[]) => {
      this.off(event, onceHandler)
      handler(...args)
    }
    this.on(event, onceHandler)
  }

  private emitLocal(event: string, ...args: any[]): void {
    const handlers = this.eventHandlers.get(event)
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(...args)
        } catch (error) {
          logger.error(`[NativeWS] Error in event handler for ${event}:`, error)
        }
      })
    }
  }

  /**
   * Utility methods
   */
  isConnected(): boolean {
    return this.connectionStatus.connected
  }

  isReady(): boolean {
    return this.connectionStatus.ready
  }

  getLastServerSeq(): number {
    return this.connectionStatus.lastSeq
  }

  getSubscribedRooms(): string[] {
    return Array.from(this.subscribedRooms)
  }

  /**
   * Reconnection logic
   */
  private scheduleReconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
    }

    if (this.reconnectionAttempts >= (this.config.reconnectionAttempts || 5)) {
      logger.error('[NativeWS] Max reconnection attempts reached')
      this.emitLocal('internal:connection_failed', { error: 'Max reconnection attempts reached' })
      return
    }

    const delay = Math.min(
      this.config.reconnectionDelay! * Math.pow(2, this.reconnectionAttempts),
      this.config.reconnectionDelayMax!
    )

    logger.info(`[NativeWS] Reconnecting in ${delay}ms (attempt ${this.reconnectionAttempts + 1})`)

    this.reconnectTimeout = setTimeout(() => {
      this.reconnectionAttempts++
      this.connect()
    }, delay)
  }

  /**
   * Resubscribe to rooms after reconnection
   */
  private async resubscribeToRooms(): Promise<void> {
    const rooms = Array.from(this.subscribedRooms)
    this.subscribedRooms.clear()

    for (const room of rooms) {
      try {
        await this.joinRoom(room)
        logger.debug(`[NativeWS] Resubscribed to room: ${room}`)
      } catch (error) {
        logger.error(`[NativeWS] Failed to resubscribe to room ${room}:`, error)
      }
    }
  }

  /**
   * Ping/pong for connection health
   */
  private startPingInterval(): void {
    this.pingInterval = setInterval(() => {
      if (this.isConnected()) {
        this.send({ event: 'ping', timestamp: Date.now() })
      }
    }, 30000)
  }

  private stopPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval)
      this.pingInterval = undefined
    }
  }

  /**
   * Request sync for missed events
   */
  requestSync(lastGlobalSeq?: number, playlistSeqs?: Record<string, number>): void {
    this.send({
      event: 'sync:request',
      last_global_seq: lastGlobalSeq || this.connectionStatus.lastSeq,
      last_playlist_seqs: playlistSeqs,
      requested_rooms: Array.from(this.subscribedRooms)
    })
  }

  /**
   * Cleanup and disconnect
   */
  disconnect(): void {
    this.isDestroyed = true

    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
    }

    this.stopPingInterval()

    if (this.ws) {
      this.ws.close(1000, 'Client disconnect')
      this.ws = null
    }

    this.connectionStatus.connected = false
    this.connectionStatus.ready = false
    this.subscribedRooms.clear()
  }

  destroy(): void {
    this.disconnect()
    this.eventHandlers.clear()
  }
}
