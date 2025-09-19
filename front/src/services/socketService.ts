/**
 * Refactored Socket Service for TheOpenMusicBox
 * 
 * Updated to handle the new standardized Socket.IO event envelope format.
 * All events now follow the StateEventEnvelope structure for consistency.
 */

import { io, Socket } from 'socket.io-client'
import { logger } from '../utils/logger'
import { socketConfig } from '../config/environment'
import { 
  StateEventEnvelope, 
  OperationAck, 
  PlayerState,
  Playlist,
  TrackProgress,
  UploadProgress,
  YouTubeProgress,
  NFCAssociation
} from '../types/contracts'

/**
 * Socket event type definitions for type safety
 */
export type SocketEventType = 
  | 'connection_status'
  | 'join:playlists' 
  | 'leave:playlists'
  | 'join:playlist'
  | 'leave:playlist'
  | 'join:nfc'
  | 'ack:join'
  | 'ack:leave'
  | 'state:playlists'
  | 'state:playlists_index_update'
  | 'state:playlist'
  | 'state:player'
  | 'state:track_progress'
  | 'state:track_position'  // Lightweight position updates (200ms)
  | 'state:track'
  | 'state:playlist_deleted'
  | 'state:playlist_created'
  | 'state:playlist_updated'
  | 'state:track_deleted'
  | 'state:track_added'
  | 'state:volume_changed'
  | 'state:nfc_state'
  | 'ack:op'
  | 'err:op'
  | 'sync:request'
  | 'sync:complete'
  | 'sync:error'
  | 'upload:progress'
  | 'upload:complete'
  | 'upload:error'
  | 'nfc_status'
  | 'nfc_association_state'
  | 'youtube:progress'
  | 'youtube:complete'
  | 'youtube:error'

/**
 * Event handler type definitions
 */
export interface EventHandlers {
  'connection_status': (data: { status: string; sid: string; server_seq: number; server_time: number }) => void
  'ack:join': (data: { room: string; success: boolean; server_seq?: number; playlist_seq?: number; message?: string }) => void
  'ack:leave': (data: { room: string; success: boolean; message?: string }) => void
  'state:playlists': (data: StateEventEnvelope<Playlist[]>) => void
  'state:playlists_index_update': (data: StateEventEnvelope<any>) => void
  'state:playlist': (data: StateEventEnvelope<Playlist>) => void
  'state:player': (data: StateEventEnvelope<PlayerState>) => void
  'state:track_progress': (data: StateEventEnvelope<TrackProgress>) => void
  'state:track_position': (data: StateEventEnvelope<{ position_ms: number; track_id: string; is_playing: boolean; duration_ms?: number }>) => void
  'state:track': (data: StateEventEnvelope<any>) => void
  'state:playlist_deleted': (data: StateEventEnvelope<{ playlist_id: string; message?: string }>) => void
  'state:playlist_created': (data: StateEventEnvelope<{ playlist: Playlist }>) => void
  'state:playlist_updated': (data: StateEventEnvelope<{ playlist: Playlist }>) => void
  'state:track_deleted': (data: StateEventEnvelope<{ playlist_id: string; track_numbers: number[] }>) => void
  'state:track_added': (data: StateEventEnvelope<{ playlist_id: string; track: any }>) => void
  'state:volume_changed': (data: StateEventEnvelope<{ volume: number }>) => void
  'state:nfc_state': (data: StateEventEnvelope<NFCAssociation>) => void
  'ack:op': (data: OperationAck) => void
  'err:op': (data: OperationAck) => void
  'upload:progress': (data: UploadProgress) => void
  'upload:complete': (data: { playlist_id: string; session_id: string; filename: string; track: any }) => void
  'upload:error': (data: { playlist_id: string; session_id: string; error: string }) => void
  'nfc_status': (data: any) => void
  'nfc_association_state': (data: any) => void
  'youtube:progress': (data: YouTubeProgress) => void
  'youtube:complete': (data: { task_id: string; track: any; playlist_id: string }) => void
  'youtube:error': (data: { task_id: string; message: string }) => void
}

/**
 * Connection status tracking
 */
interface ConnectionStatus {
  connected: boolean
  ready: boolean
  lastSeq: number
  serverId?: string
  serverTime?: number
}

/**
 * Refactored Socket Service with standardized event handling
 */
class SocketService {
  private socket!: Socket
  private eventHandlers = new Map<string, Set<(...args: any[]) => void>>()
  private pendingOperations = new Map<string, { resolve: (...args: any[]) => void; reject: (...args: any[]) => void; timeout: ReturnType<typeof setTimeout> }>()
  private connectionStatus: ConnectionStatus = {
    connected: false,
    ready: false,
    lastSeq: 0
  }
  
  // Event ordering and buffering for reliability
  private eventBuffer = new Map<number, StateEventEnvelope>()
  private expectedSeq = 1
  private maxBufferSize = 100
  private bufferProcessingTimer?: ReturnType<typeof setTimeout>
  
  // Room subscriptions tracking
  private subscribedRooms = new Set<string>()
  private roomJoinPromises = new Map<string, Promise<void>>()
  
  // Connection health monitoring
  private healthCheckInterval?: ReturnType<typeof setTimeout>
  private reconnectionAttempts = 0
  private maxReconnectionAttempts = 10
  
  // Debug flags for logging
  private _firstTrackPositionLogged = false
  private _envelopeLogged = false
  private _domDispatchLogged = false
  private _trackPositionDispatched = false
  
  constructor() {
    logger.info('Initializing refactored Socket Service with standardized event handling')
    this.initializeSocket()
  }
  
  /**
   * Initialize socket connection with enhanced configuration
   */
  private initializeSocket(): void {
    logger.info(`🔊🎵 Initializing WebSocket connection to: ${socketConfig.url}`)
    
    this.socket = io(socketConfig.url, {
      ...socketConfig.options,
      transports: ['websocket', 'polling']
    })
    
    // Force connection if autoConnect was disabled
    if (!this.socket.connected) {
      logger.info('🔊🎵 Manually connecting socket...')
      this.socket.connect()
    }
    
    this.setupConnectionHandlers()
    this.setupStandardizedEventHandlers()
    this.startHealthCheck()
  }
  
  /**
   * Setup connection lifecycle handlers
   */
  private setupConnectionHandlers(): void {
    this.socket.on('connect', () => {
      logger.info('🔊🎵 ✅ SOCKET CONNECTED SUCCESSFULLY!', { 
        url: socketConfig.url,
        id: this.socket.id 
      })
      this.connectionStatus.connected = true
      this.reconnectionAttempts = 0
      this.emitLocal('internal:connection_changed', { connected: true })
      
      // Post-connection synchronization with delay to ensure server is ready
      setTimeout(() => {
        this.performPostConnectionSync()
      }, 1000)
    })
    
    this.socket.on('disconnect', (reason) => {
      logger.warn(`Socket disconnected: ${reason}`)
      this.connectionStatus.connected = false
      this.connectionStatus.ready = false
      this.subscribedRooms.clear()
      this.emitLocal('internal:connection_changed', { connected: false, reason })
    })
    
    this.socket.on('connect_error', (error) => {
      logger.error('🔊🎵 ❌ SOCKET CONNECTION ERROR:', {
        message: error.message,
        type: (error as any).type || 'unknown',
        url: socketConfig.url,
        attempt: this.reconnectionAttempts + 1
      })
      this.reconnectionAttempts++
      
      if (this.reconnectionAttempts >= this.maxReconnectionAttempts) {
        logger.error('Max reconnection attempts reached')
        this.emitLocal('internal:connection_failed', { error })
      }
    })
    
    this.socket.on('reconnect', (attemptNumber) => {
      logger.info(`Socket reconnected after ${attemptNumber} attempts`)
      this.reconnectionAttempts = 0
      
      // Re-subscribe to rooms after reconnection
      this.resubscribeToRooms()
      
      // Post-reconnection synchronization
      setTimeout(() => {
        this.performPostConnectionSync()
      }, 1500)
    })
  }
  
  /**
   * Setup standardized event handlers using the new envelope format
   */
  private setupStandardizedEventHandlers(): void {
    logger.info('🔧 Setting up standardized Socket.IO event handlers...', { url: socketConfig.url })
    
    // Connection status handling
    this.socket.on('connection_status', (data) => {
      logger.debug('Received connection status:', data)
      this.connectionStatus.ready = true
      this.connectionStatus.serverId = data.sid
      this.connectionStatus.lastSeq = data.server_seq
      this.connectionStatus.serverTime = data.server_time
      this.emitLocal('connection_status', data)
    })
    
    // Room acknowledgments
    this.socket.on('ack:join', (data) => {
      logger.debug(`Room join ack: ${data.room} - ${data.success}`)
      if (data.success) {
        this.subscribedRooms.add(data.room)
      }
      this.emitLocal('ack:join', data)
      this.resolveRoomOperation('join', data.room, data)
    })
    
    this.socket.on('ack:leave', (data) => {
      logger.debug(`Room leave ack: ${data.room} - ${data.success}`)
      if (data.success) {
        this.subscribedRooms.delete(data.room)
      }
      this.emitLocal('ack:leave', data)
      this.resolveRoomOperation('leave', data.room, data)
    })
    
    // Standardized state events with envelope handling
    this.setupStateEventHandler('state:playlists')
    this.setupStateEventHandler('state:playlists_index_update')
    this.setupStateEventHandler('state:playlist')
    this.setupStateEventHandler('state:player')
    this.setupStateEventHandler('state:track_progress')
    this.setupStateEventHandler("state:track_position")
    this.setupStateEventHandler("state:track")
    
    // Action-specific events for real-time UI updates
    this.setupStateEventHandler('state:playlist_deleted')
    this.setupStateEventHandler('state:playlist_created')
    this.setupStateEventHandler('state:playlist_updated')
    this.setupStateEventHandler('state:track_deleted')
    this.setupStateEventHandler('state:track_added')
    
    // System state events
    this.setupStateEventHandler('state:volume_changed')
    this.setupStateEventHandler('state:nfc_state')
    
    // Operation acknowledgments
    this.socket.on('ack:op', (data: OperationAck) => {
      logger.debug(`Operation ack: ${data.client_op_id} - ${data.success}`)
      this.resolveOperation(data.client_op_id, data)
      this.emitLocal('ack:op', data)
    })
    
    this.socket.on('err:op', (data: OperationAck) => {
      logger.debug(`Operation error: ${data.client_op_id} - ${data.message}`)
      this.rejectOperation(data.client_op_id, new Error(data.message || 'Operation failed'))
      this.emitLocal('err:op', data)
    })
    
    // Upload events
    this.socket.on('upload:progress', (data) => {
      this.emitLocal('upload:progress', data)
    })
    
    this.socket.on('upload:complete', (data) => {
      this.emitLocal('upload:complete', data)
    })
    
    this.socket.on('upload:error', (data) => {
      this.emitLocal('upload:error', data)
    })
    
    // YouTube events
    this.socket.on('youtube:progress', (data) => {
      this.emitLocal('youtube:progress', data)
    })
    
    this.socket.on('youtube:complete', (data) => {
      this.emitLocal('youtube:complete', data)
    })
    
    this.socket.on('youtube:error', (data) => {
      this.emitLocal('youtube:error', data)
    })
    
    // NFC events
    this.socket.on('nfc_status', (data) => {
      this.emitLocal('nfc_status', data)
    })
    
    // Legacy playback_status events removed - only use modern state:* events
    
    this.socket.on('nfc_association_state', (data) => {
      this.emitLocal('nfc_association_state', data)
    })
    
    // Sync events
    this.socket.on('sync:complete', (data) => {
      logger.debug('Sync complete received')
      this.emitLocal('sync:complete', data)
    })
    
    this.socket.on('sync:error', (data) => {
      logger.error('Sync error received:', data)
      this.emitLocal('sync:error', data)
    })
  }
  
  /**
   * Setup handler for state events with envelope processing
   */
  private setupStateEventHandler(eventType: string): void {
    logger.debug(`🔧 Setting up handler for: ${eventType}`)
    
    this.socket.on(eventType, (rawData) => {
      try {
        // Enhanced logging for debugging
        if (eventType.includes('player') || eventType.includes('playlist_created') || eventType === 'state:track_position') {
          if (eventType === 'state:track_position') {
            // Log first track position event only
            if (!this._firstTrackPositionLogged) {
              logger.info(`🎯 FIRST ${eventType} received via WebSocket!`, rawData)
              this._firstTrackPositionLogged = true
            }
          } else {
            logger.info(`🔊🎵 WebSocket event received: ${eventType}`, {
              eventType,
              rawData,
              hasData: !!rawData?.data,
              dataKeys: rawData?.data ? Object.keys(rawData.data) : []
            })
          }
        }
        
        // All events now use standardized envelope format
        const envelope = rawData
        
        // Log envelope structure for first track_position
        if (eventType === 'state:track_position' && !this._envelopeLogged) {
          logger.info(`📦 Track position envelope:`, envelope)
          this._envelopeLogged = true
        }
        
        // Skip sequence ordering for track position events - they need immediate processing
        if (eventType === 'state:track_position') {
          this.processEvent(envelope)
          this.updateSequenceCounter(envelope.server_seq || 0)
        } else {
          // Process other events with sequence ordering
          if (envelope.server_seq && envelope.server_seq > this.expectedSeq) {
            this.bufferEvent(envelope)
          } else {
            this.processEvent(envelope)
            this.updateSequenceCounter(envelope.server_seq || 0)
          }
        }
      } catch (error) {
        logger.error(`Error processing ${eventType} event:`, error)
      }
    })
  }
  
  // Legacy event normalization removed - all events use standardized format
  
  /**
   * Process event and emit to handlers
   */
  private processEvent(envelope: StateEventEnvelope): void {
    logger.debug(`Processing event: ${envelope.event_type} (seq: ${envelope.server_seq})`)
    this.emitLocal(envelope.event_type, envelope)
    
    // Also dispatch as DOM events for serverStateStore compatibility
    this.dispatchDOMEvent(envelope.event_type, envelope)
  }
  
  /**
   * Dispatch DOM events for serverStateStore to consume
   */
  private dispatchDOMEvent(eventType: string, envelope: StateEventEnvelope): void {
    try {
      const domEvent = new CustomEvent(eventType, {
        detail: envelope,
        bubbles: false,
        cancelable: false
      })
      window.dispatchEvent(domEvent)
      
      // Log DOM dispatch for track_position first time
      if (eventType === 'state:track_position' && !this._domDispatchLogged) {
        logger.info(`🎯 FIRST state:track_position dispatched to DOM!`, { eventType, envelope })
        this._domDispatchLogged = true
      }
      
      // Enhanced logging for debugging
      if (eventType.includes('player') || eventType.includes('playlist_created')) {
        logger.info(`🔊 DOM event dispatched: ${eventType}`, { 
          eventType,
          data: envelope.data,
          envelopeKeys: Object.keys(envelope)
        })
      } else {
        logger.debug(`DOM event dispatched: ${eventType}`)
      }
    } catch (error) {
      logger.error(`Failed to dispatch DOM event ${eventType}:`, error)
    }
  }
  
  /**
   * Buffer out-of-order events
   */
  private bufferEvent(envelope: StateEventEnvelope): void {
    if (this.eventBuffer.size >= this.maxBufferSize) {
      // Remove oldest buffered event
      const oldestSeq = Math.min(...this.eventBuffer.keys())
      this.eventBuffer.delete(oldestSeq)
    }
    
    this.eventBuffer.set(envelope.server_seq!, envelope)
    this.scheduleBufferProcessing()
  }
  
  /**
   * Process buffered events in order
   */
  private scheduleBufferProcessing(): void {
    if (this.bufferProcessingTimer) {
      clearTimeout(this.bufferProcessingTimer)
    }
    
    this.bufferProcessingTimer = setTimeout(() => {
      this.processBufferedEvents()
    }, 100)
  }
  
  private processBufferedEvents(): void {
    while (this.eventBuffer.has(this.expectedSeq)) {
      const envelope = this.eventBuffer.get(this.expectedSeq)!
      this.processEvent(envelope)
      this.eventBuffer.delete(this.expectedSeq)
      this.expectedSeq++
    }
  }
  
  private updateSequenceCounter(serverSeq: number): void {
    if (serverSeq > this.connectionStatus.lastSeq) {
      this.connectionStatus.lastSeq = serverSeq
    }
  }
  
  // Legacy playback_status converter removed - only use modern events

  /**
   * Public API methods
   */
  
  /**
   * Join a room for receiving specific events
   */
  async joinRoom(room: string): Promise<void> {
    if (this.roomJoinPromises.has(room)) {
      return this.roomJoinPromises.get(room)
    }
    
    const promise = new Promise<void>((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.roomJoinPromises.delete(room)
        reject(new Error(`Join room timeout: ${room}`))
      }, 10000)
      
      const cleanup = () => {
        clearTimeout(timeout)
        this.roomJoinPromises.delete(room)
      }
      
      const successHandler = (data: any) => {
        if (data.room === room) {
          this.off('ack:join', successHandler)
          this.off('ack:leave', errorHandler)
          cleanup()
          
          if (data.success) {
            resolve()
          } else {
            reject(new Error(data.message || `Failed to join room: ${room}`))
          }
        }
      }
      
      const errorHandler = (error: any) => {
        this.off('ack:join', successHandler)
        this.off('ack:leave', errorHandler)
        cleanup()
        reject(error)
      }
      
      this.on('ack:join', successHandler)
      this.once('error', errorHandler)
      
      // Emit specific room join events instead of generic pattern
      if (room === 'playlists') {
        this.socket.emit('join:playlists', {})
      } else if (room.startsWith('playlist:')) {
        const playlistId = room.replace('playlist:', '')
        this.socket.emit('join:playlist', { playlist_id: playlistId })
      } else if (room === 'nfc') {
        this.socket.emit('join:nfc', {})
      } else {
        // Fallback for unknown rooms
        this.socket.emit(`join:${room}`, {})
      }
    })
    
    this.roomJoinPromises.set(room, promise)
    return promise
  }
  
  /**
   * Leave a room
   */
  async leaveRoom(room: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error(`Leave room timeout: ${room}`))
      }, 10000)
      
      const successHandler = (data: any) => {
        if (data.room === room) {
          clearTimeout(timeout)
          this.off('ack:leave', successHandler)
          resolve()
        }
      }
      
      this.once('ack:leave', successHandler)
      
      // Emit specific room leave events instead of generic pattern
      if (room === 'playlists') {
        this.socket.emit('leave:playlists', {})
      } else if (room.startsWith('playlist:')) {
        const playlistId = room.replace('playlist:', '')
        this.socket.emit('leave:playlist', { playlist_id: playlistId })
      } else if (room === 'nfc') {
        this.socket.emit('leave:nfc', {})
      } else {
        // Fallback for unknown rooms
        this.socket.emit(`leave:${room}`, {})
      }
    })
  }
  
  /**
   * Send operation with acknowledgment tracking
   */
  async sendOperation(event: string, data: any, clientOpId: string): Promise<any> {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pendingOperations.delete(clientOpId)
        reject(new Error(`Operation timeout: ${event}`))
      }, 30000)
      
      this.pendingOperations.set(clientOpId, { resolve, reject, timeout })
      this.socket.emit(event, data)
    })
  }
  
  /**
   * Request sync for missed events
   */
  requestSync(lastGlobalSeq?: number, playlistSeqs?: Record<string, number>): void {
    this.socket.emit('sync:request', {
      last_global_seq: lastGlobalSeq || this.connectionStatus.lastSeq,
      last_playlist_seqs: playlistSeqs,
      requested_rooms: Array.from(this.subscribedRooms)
    })
  }
  
  /**
   * Event subscription methods
   */
  on<T extends keyof EventHandlers>(event: T, handler: EventHandlers[T]): void
  on(event: string, handler: (...args: any[]) => void): void
  on(event: string, handler: (...args: any[]) => void): void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, new Set())
    }
    this.eventHandlers.get(event)!.add(handler)
  }
  
  off<T extends keyof EventHandlers>(event: T, handler: EventHandlers[T]): void
  off(event: string, handler: (...args: any[]) => void): void
  off(event: string, handler: (...args: any[]) => void): void {
    const handlers = this.eventHandlers.get(event)
    if (handlers) {
      handlers.delete(handler)
      if (handlers.size === 0) {
        this.eventHandlers.delete(event)
      }
    }
  }
  
  once<T extends keyof EventHandlers>(event: T, handler: EventHandlers[T]): void
  once(event: string, handler: (...args: any[]) => void): void
  once(event: string, handler: (...args: any[]) => void): void {
    const onceHandler = (...args: any[]) => {
      this.off(event, onceHandler)
      handler(...args)
    }
    this.on(event, onceHandler)
  }
  
  emit(event: string, ...args: any[]): void {
    // Forward to socket.io client for outgoing events
    if (this.socket && this.isConnected()) {
      this.socket.emit(event, ...args)
    } else {
      logger.warn(`Cannot emit ${event}: socket not connected`)
    }
  }
  
  // Internal emit for local event handlers
  private emitLocal(event: string, ...args: any[]): void {
    const handlers = this.eventHandlers.get(event)
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(...args)
        } catch (error) {
          logger.error(`Error in event handler for ${event}:`, error)
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
   * Private helper methods
   */
  
  private resolveOperation(clientOpId: string, data: any): void {
    const operation = this.pendingOperations.get(clientOpId)
    if (operation) {
      clearTimeout(operation.timeout)
      this.pendingOperations.delete(clientOpId)
      operation.resolve(data)
    }
  }
  
  private rejectOperation(clientOpId: string, error: Error): void {
    const operation = this.pendingOperations.get(clientOpId)
    if (operation) {
      clearTimeout(operation.timeout)
      this.pendingOperations.delete(clientOpId)
      operation.reject(error)
    }
  }
  
  private resolveRoomOperation(type: 'join' | 'leave', room: string, data: any): void {
    // Additional room operation tracking if needed
  }
  
  private async resubscribeToRooms(): Promise<void> {
    const rooms = Array.from(this.subscribedRooms)
    this.subscribedRooms.clear()
    
    for (const room of rooms) {
      try {
        await this.joinRoom(room)
        logger.debug(`Resubscribed to room: ${room}`)
      } catch (error) {
        logger.error(`Failed to resubscribe to room ${room}:`, error)
      }
    }
  }
  
  private startHealthCheck(): void {
    this.healthCheckInterval = setInterval(() => {
      if (this.isConnected()) {
        this.socket.emit('client_ping', { timestamp: Date.now() })
      }
    }, 30000)
  }

  /**
   * Perform post-connection synchronization to catch up on missed events
   */
  private performPostConnectionSync(): void {
    if (!this.isConnected()) {
      logger.warn('Cannot perform post-connection sync - not connected')
      return
    }

    logger.info('🔄 Performing post-connection synchronization...')
    
    try {
      // Emit a custom event to trigger server-side player state broadcast
      this.socket.emit('client:request_current_state', {
        timestamp: Date.now(),
        client_id: this.socket.id,
        requested_states: ['player', 'track_position']
      })
      
      logger.info('✅ Post-connection sync request sent')
    } catch (error) {
      logger.error('❌ Error in post-connection sync:', error)
    }
  }
  
  /**
   * Cleanup on destruction
   */
  destroy(): void {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval)
    }
    if (this.bufferProcessingTimer) {
      clearTimeout(this.bufferProcessingTimer)
    }
    
    // Clear all pending operations
    this.pendingOperations.forEach(({ timeout, reject }) => {
      clearTimeout(timeout)
      reject(new Error('Socket service destroyed'))
    })
    this.pendingOperations.clear()
    
    this.socket.disconnect()
  }
}

// Export singleton instance
export const socketService = new SocketService()
export default socketService