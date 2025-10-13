/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-non-null-assertion, @typescript-eslint/no-unused-vars */
/**
 * Refactored Socket Service for TheOpenMusicBox
 *
 * Updated to handle the new standardized Socket.IO event envelope format.
 * All events now follow the StateEventEnvelope structure for consistency.
 */

import { io, Socket } from 'socket.io-client'
import { logger } from '../utils/logger'
import { socketConfig, appConfig } from '../config/environment'
import { NativeWebSocketClient } from './nativeWebSocket'
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
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  'state:playlists_index_update': (data: StateEventEnvelope<any>) => void
  'state:playlist': (data: StateEventEnvelope<Playlist>) => void
  'state:player': (data: StateEventEnvelope<PlayerState>) => void
  'state:track_progress': (data: StateEventEnvelope<TrackProgress>) => void
  'state:track_position': (data: StateEventEnvelope<{ position_ms: number; track_id: string; is_playing: boolean; duration_ms?: number }>) => void
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  'state:track': (data: StateEventEnvelope<any>) => void
  'state:playlist_deleted': (data: StateEventEnvelope<{ playlist_id: string; message?: string }>) => void
  'state:playlist_created': (data: StateEventEnvelope<{ playlist: Playlist }>) => void
  'state:playlist_updated': (data: StateEventEnvelope<{ playlist: Playlist }>) => void
  'state:track_deleted': (data: StateEventEnvelope<{ playlist_id: string; track_numbers: number[] }>) => void
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  'state:track_added': (data: StateEventEnvelope<{ playlist_id: string; track: any }>) => void
  'state:volume_changed': (data: StateEventEnvelope<{ volume: number }>) => void
  'state:nfc_state': (data: StateEventEnvelope<NFCAssociation>) => void
  'ack:op': (data: OperationAck) => void
  'err:op': (data: OperationAck) => void
  'upload:progress': (data: UploadProgress) => void
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  'upload:complete': (data: { playlist_id: string; session_id: string; filename: string; track: any }) => void
  'upload:error': (data: { playlist_id: string; session_id: string; error: string }) => void
  'nfc_status': (data: unknown) => void
  'nfc_association_state': (data: unknown) => void
  'youtube:progress': (data: YouTubeProgress) => void
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
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
 * Supports dual-mode: Socket.IO for RPI Backend, native WebSocket for ESP32
 */
class SocketService {
  private socket!: Socket | NativeWebSocketClient
  private isESP32Mode = false
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
    logger.info('Initializing refactored Socket Service with dual-mode support (Socket.IO / Native WebSocket)')
    this.initializeSocket()
  }
  
  /**
   * Initialize socket connection with enhanced configuration
   * Auto-detects ESP32 vs RPI Backend and uses appropriate client
   */
  private initializeSocket(): void {
    // Detect backend type from config
    this.isESP32Mode = socketConfig.options.path === '/ws'

    logger.info(`🔊🎵 Initializing ${this.isESP32Mode ? 'ESP32 (Native WebSocket)' : 'RPI Backend (Socket.IO)'} connection to: ${socketConfig.url}`)

    if (this.isESP32Mode) {
      // Use native WebSocket for ESP32
      this.socket = new NativeWebSocketClient({
        url: socketConfig.url,
        path: '/ws',
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        timeout: 10000
      })

      this.setupNativeWebSocketHandlers()
      this.socket.connect()
    } else {
      // Use Socket.IO for RPI Backend
      this.socket = io(socketConfig.url, {
        ...socketConfig.options,
        transports: ['websocket', 'polling']
      }) as Socket

      // Force connection if autoConnect was disabled
      if (!(this.socket as Socket).connected) {
        logger.info('🔊🎵 Manually connecting Socket.IO...')
        ;(this.socket as Socket).connect()
      }

      this.setupConnectionHandlers()
      this.setupStandardizedEventHandlers()
    }

    this.startHealthCheck()
  }
  
  /**
   * Setup handlers for native WebSocket (ESP32 mode)
   */
  private setupNativeWebSocketHandlers(): void {
    const ws = this.socket as NativeWebSocketClient

    // Connection status
    ws.on('internal:connection_changed', (data: any) => {
      this.connectionStatus.connected = data.connected
      if (data.connected) {
        logger.info('🔊🎵 ✅ NATIVE WEBSOCKET CONNECTED TO ESP32!', {
          url: socketConfig.url
        })
        this.reconnectionAttempts = 0
        this.emitLocal('internal:connection_changed', { connected: true })
      } else {
        logger.warn(`Native WebSocket disconnected: ${data.reason}`)
        this.connectionStatus.ready = false
        this.subscribedRooms.clear()
        this.emitLocal('internal:connection_changed', { connected: false, reason: data.reason })
      }
    })

    ws.on('internal:connection_error', (data: any) => {
      logger.error('🔊🎵 ❌ NATIVE WEBSOCKET CONNECTION ERROR:', data.error)
      this.reconnectionAttempts++

      if (this.reconnectionAttempts >= this.maxReconnectionAttempts) {
        logger.error('Max reconnection attempts reached')
        this.emitLocal('internal:connection_failed', { error: data.error })
      }
    })

    ws.on('internal:connection_failed', (data: any) => {
      logger.error('Native WebSocket connection failed:', data)
      this.emitLocal('internal:connection_failed', data)
    })

    // Forward all other events to local handlers
    ws.on('connection_status', (data: any) => {
      this.connectionStatus.ready = true
      this.connectionStatus.serverId = data.sid
      this.connectionStatus.lastSeq = data.server_seq
      this.connectionStatus.serverTime = data.server_time
      this.emitLocal('connection_status', data)
    })

    ws.on('ack:join', (data: any) => {
      if (data.success) {
        this.subscribedRooms.add(data.room)
      }
      this.emitLocal('ack:join', data)
      this.resolveRoomOperation('join', data.room, data)
    })

    ws.on('ack:leave', (data: any) => {
      if (data.success) {
        this.subscribedRooms.delete(data.room)
      }
      this.emitLocal('ack:leave', data)
      this.resolveRoomOperation('leave', data.room, data)
    })

    ws.on('ack:op', (data: any) => {
      this.resolveOperation(data.client_op_id, data)
      this.emitLocal('ack:op', data)
    })

    ws.on('err:op', (data: any) => {
      this.rejectOperation(data.client_op_id, new Error(data.message || 'Operation failed'))
      this.emitLocal('err:op', data)
    })

    // State events - forward all to local handlers
    const stateEvents = [
      'state:playlists',
      'state:playlists_index_update',
      'state:playlist',
      'state:player',
      'state:track_progress',
      'state:track_position',
      'state:track',
      'state:playlist_deleted',
      'state:playlist_created',
      'state:playlist_updated',
      'state:track_deleted',
      'state:track_added',
      'state:volume_changed',
      'state:nfc_state',
      'upload:progress',
      'upload:complete',
      'upload:error',
      'nfc_status',
      'nfc_association_state',
      'youtube:progress',
      'youtube:complete',
      'youtube:error'
    ]

    stateEvents.forEach(eventType => {
      ws.on(eventType, (data: any) => {
        // Update sequence counter
        if (data.server_seq) {
          this.connectionStatus.lastSeq = Math.max(
            this.connectionStatus.lastSeq,
            data.server_seq
          )
        }

        // Forward to local handlers
        this.emitLocal(eventType, data)
      })
    })
  }

  /**
   * Setup connection lifecycle handlers (Socket.IO mode)
   */
  private setupConnectionHandlers(): void {
    const socketIO = this.socket as Socket

    socketIO.on('connect', () => {
      logger.info('🔊🎵 ✅ SOCKET.IO CONNECTED TO RPI BACKEND!', {
        url: socketConfig.url,
        id: socketIO.id
      })
      this.connectionStatus.connected = true
      this.reconnectionAttempts = 0
      this.emitLocal('internal:connection_changed', { connected: true })

      // Post-connection synchronization with delay to ensure server is ready
      setTimeout(() => {
        this.performPostConnectionSync()
      }, 1000)
    })

    socketIO.on('disconnect', (reason) => {
      logger.warn(`Socket disconnected: ${reason}`)
      this.connectionStatus.connected = false
      this.connectionStatus.ready = false
      this.subscribedRooms.clear()
      this.emitLocal('internal:connection_changed', { connected: false, reason })
    })

    socketIO.on('connect_error', (error) => {
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

    socketIO.on('reconnect', (attemptNumber) => {
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
   * Setup standardized event handlers using the new envelope format (Socket.IO mode)
   */
  private setupStandardizedEventHandlers(): void {
    const socketIO = this.socket as Socket
    logger.info('🔧 Setting up standardized Socket.IO event handlers...', { url: socketConfig.url })

    // Connection status handling
    socketIO.on('connection_status', (data) => {
      logger.debug('Received connection status:', data)
      this.connectionStatus.ready = true
      this.connectionStatus.serverId = data.sid
      this.connectionStatus.lastSeq = data.server_seq
      this.connectionStatus.serverTime = data.server_time
      this.emitLocal('connection_status', data)
    })

    // Room acknowledgments
    socketIO.on('ack:join', (data) => {
      logger.debug(`Room join ack: ${data.room} - ${data.success}`)
      if ((data as { success?: boolean; message?: string }).success) {
        this.subscribedRooms.add(data.room)
      }
      this.emitLocal('ack:join', data)
      this.resolveRoomOperation('join', data.room, data)
    })

    socketIO.on('ack:leave', (data) => {
      logger.debug(`Room leave ack: ${data.room} - ${data.success}`)
      if ((data as { success?: boolean; message?: string }).success) {
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
    socketIO.on('ack:op', (data: OperationAck) => {
      logger.debug(`Operation ack: ${data.client_op_id} - ${data.success}`)
      this.resolveOperation(data.client_op_id, data)
      this.emitLocal('ack:op', data)
    })

    socketIO.on('err:op', (data: OperationAck) => {
      logger.debug(`Operation error: ${data.client_op_id} - ${data.message}`)
      this.rejectOperation(data.client_op_id, new Error((data as { message?: string }).message || 'Operation failed'))
      this.emitLocal('err:op', data)
    })
    
    // Upload events
    socketIO.on('upload:progress', (data) => {
      this.emitLocal('upload:progress', data)
    })

    socketIO.on('upload:complete', (data) => {
      this.emitLocal('upload:complete', data)
    })

    socketIO.on('upload:error', (data) => {
      this.emitLocal('upload:error', data)
    })

    // YouTube events
    socketIO.on('youtube:progress', (data) => {
      this.emitLocal('youtube:progress', data)
    })

    socketIO.on('youtube:complete', (data) => {
      this.emitLocal('youtube:complete', data)
    })

    socketIO.on('youtube:error', (data) => {
      this.emitLocal('youtube:error', data)
    })

    // NFC events
    socketIO.on('nfc_status', (data) => {
      this.emitLocal('nfc_status', data)
    })

    // Legacy playback_status events removed - only use modern state:* events

    socketIO.on('nfc_association_state', (data) => {
      this.emitLocal('nfc_association_state', data)
    })

    // Sync events
    socketIO.on('sync:complete', (data) => {
      logger.debug('Sync complete received')
      this.emitLocal('sync:complete', data)
    })

    socketIO.on('sync:error', (data) => {
      logger.error('Sync error received:', data)
      this.emitLocal('sync:error', data)
    })
  }
  
  /**
   * Setup handler for state events with envelope processing (Socket.IO mode)
   */
  private setupStateEventHandler(eventType: string): void {
    const socketIO = this.socket as Socket
    logger.debug(`🔧 Setting up handler for: ${eventType}`)

    socketIO.on(eventType, (rawData) => {
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

    // Delegate to native WebSocket client if in ESP32 mode
    if (this.isESP32Mode) {
      const ws = this.socket as NativeWebSocketClient
      const promise = ws.joinRoom(room)
      this.roomJoinPromises.set(room, promise)
      promise.finally(() => this.roomJoinPromises.delete(room))
      return promise
    }

    // Socket.IO mode
    const socketIO = this.socket as Socket

    const promise = new Promise<void>((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.roomJoinPromises.delete(room)
        reject(new Error(`Join room timeout: ${room}`))
      }, 10000)

      const cleanup = () => {
        clearTimeout(timeout)
        this.roomJoinPromises.delete(room)
      }

      const successHandler = (data: unknown) => {
        if ((data as { room?: string; success?: boolean; message?: string }).room === room) {
          this.off('ack:join', successHandler)
          this.off('ack:leave', errorHandler)
          cleanup()

          if ((data as { success?: boolean; message?: string }).success) {
            resolve()
          } else {
            reject(new Error((data as { message?: string }).message || `Failed to join room: ${room}`))
          }
        }
      }

      const errorHandler = (error: unknown) => {
        this.off('ack:join', successHandler)
        this.off('ack:leave', errorHandler)
        cleanup()
        reject(error)
      }

      this.on('ack:join', successHandler)
      this.once('error', errorHandler)

      // Emit specific room join events instead of generic pattern
      if (room === 'playlists') {
        socketIO.emit('join:playlists', {})
      } else if (room.startsWith('playlist:')) {
        const playlistId = room.replace('playlist:', '')
        socketIO.emit('join:playlist', { playlist_id: playlistId })
      } else if (room === 'nfc') {
        socketIO.emit('join:nfc', {})
      } else {
        // Fallback for unknown rooms
        socketIO.emit(`join:${room}`, {})
      }
    })

    this.roomJoinPromises.set(room, promise)
    return promise
  }
  
  /**
   * Leave a room
   */
  async leaveRoom(room: string): Promise<void> {
    // Delegate to native WebSocket client if in ESP32 mode
    if (this.isESP32Mode) {
      const ws = this.socket as NativeWebSocketClient
      return ws.leaveRoom(room)
    }

    // Socket.IO mode
    const socketIO = this.socket as Socket

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error(`Leave room timeout: ${room}`))
      }, 10000)

      const successHandler = (data: unknown) => {
        if ((data as { room?: string; success?: boolean; message?: string }).room === room) {
          clearTimeout(timeout)
          this.off('ack:leave', successHandler)
          resolve()
        }
      }

      this.once('ack:leave', successHandler)

      // Emit specific room leave events instead of generic pattern
      if (room === 'playlists') {
        socketIO.emit('leave:playlists', {})
      } else if (room.startsWith('playlist:')) {
        const playlistId = room.replace('playlist:', '')
        socketIO.emit('leave:playlist', { playlist_id: playlistId })
      } else if (room === 'nfc') {
        socketIO.emit('leave:nfc', {})
      } else {
        // Fallback for unknown rooms
        socketIO.emit(`leave:${room}`, {})
      }
    })
  }
  
  /**
   * Send operation with acknowledgment tracking
   */
  async sendOperation(event: string, data: any, clientOpId: string): Promise<any> {
    // Delegate to native WebSocket client if in ESP32 mode
    if (this.isESP32Mode) {
      const ws = this.socket as NativeWebSocketClient
      return ws.sendOperation(event, data, clientOpId)
    }

    // Socket.IO mode
    const socketIO = this.socket as Socket

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pendingOperations.delete(clientOpId)
        reject(new Error(`Operation timeout: ${event}`))
      }, 30000)

      this.pendingOperations.set(clientOpId, { resolve, reject, timeout })
      socketIO.emit(event, data)
    })
  }
  
  /**
   * Request sync for missed events
   */
  requestSync(lastGlobalSeq?: number, playlistSeqs?: Record<string, number>): void {
    if (this.isESP32Mode) {
      const ws = this.socket as NativeWebSocketClient
      ws.requestSync(lastGlobalSeq, playlistSeqs)
    } else {
      const socketIO = this.socket as Socket
      socketIO.emit('sync:request', {
        last_global_seq: lastGlobalSeq || this.connectionStatus.lastSeq,
        last_playlist_seqs: playlistSeqs,
        requested_rooms: Array.from(this.subscribedRooms)
      })
    }
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
    // Forward to appropriate client for outgoing events
    if (this.socket && this.isConnected()) {
      if (this.isESP32Mode) {
        const ws = this.socket as NativeWebSocketClient
        ws.emit(event, args[0] || {})
      } else {
        const socketIO = this.socket as Socket
        socketIO.emit(event, ...args)
      }
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
  
  private resolveOperation(clientOpId: string, data: unknown): void {
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
  
  private resolveRoomOperation(_type: 'join' | 'leave', _room: string, _data: unknown): void {
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
      if (this.isESP32Mode) {
        const ws = this.socket as NativeWebSocketClient
        ws.emit('client:request_current_state', {
          timestamp: Date.now(),
          requested_states: ['player', 'track_position']
        })
      } else {
        const socketIO = this.socket as Socket
        socketIO.emit('client:request_current_state', {
          timestamp: Date.now(),
          client_id: socketIO.id,
          requested_states: ['player', 'track_position']
        })
      }

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

    // Disconnect appropriate client
    if (this.isESP32Mode) {
      const ws = this.socket as NativeWebSocketClient
      ws.destroy()
    } else {
      const socketIO = this.socket as Socket
      socketIO.disconnect()
    }
  }
}

// Export singleton instance
export const socketService = new SocketService()
export default socketService