/**
 * Comprehensive tests for SocketService.class.ts
 * Target: 100% coverage
 *
 * Test Coverage:
 * - ✅ Socket.IO mode initialization and lifecycle
 * - ✅ Native WebSocket mode initialization and lifecycle
 * - ✅ Event subscription (on/off/once)
 * - ✅ Event emission
 * - ✅ Room management (join/leave)
 * - ✅ Operation tracking with acknowledgments
 * - ✅ Event buffering and sequence ordering
 * - ✅ Error handling
 * - ✅ Health monitoring
 * - ✅ State synchronization
 * - ✅ Reconnection logic
 * - ✅ Cleanup and destruction
 */

import { describe, it, expect, vi, beforeEach, afterEach, type Mock } from 'vitest'
import {
  SocketService,
  type SocketServiceDependencies,
  type ISocketFactory,
  type ILogger,
  type ISocketConfig
} from '../../../services/SocketService.class'
import type { Socket } from 'socket.io-client'

describe('SocketService', () => {
  let mockLogger: ILogger
  let mockSocketFactory: ISocketFactory
  let mockConfig: ISocketConfig
  let mockSocket: Partial<Socket>
  let mockNativeWebSocket: any
  let mockSocketEventHandlers: Map<string, Function>
  let service: SocketService

  beforeEach(() => {
    // Clear all timers
    vi.clearAllTimers()
    vi.useFakeTimers()

    mockSocketEventHandlers = new Map()

    // Mock logger
    mockLogger = {
      info: vi.fn(),
      debug: vi.fn(),
      warn: vi.fn(),
      error: vi.fn()
    }

    // Mock Socket.IO socket
    mockSocket = {
      id: 'test-socket-id',
      connected: false,
      connect: vi.fn().mockImplementation(function(this: any) {
        this.connected = true
        return this
      }),
      disconnect: vi.fn().mockImplementation(function(this: any) {
        this.connected = false
        return this
      }),
      on: vi.fn().mockImplementation((event: string, handler: Function) => {
        mockSocketEventHandlers.set(event, handler)
        return mockSocket
      }),
      emit: vi.fn(),
      off: vi.fn()
    }

    // Mock Native WebSocket
    mockNativeWebSocket = {
      connect: vi.fn(),
      disconnect: vi.fn(),
      destroy: vi.fn(),
      emit: vi.fn(),
      on: vi.fn().mockImplementation((event: string, handler: Function) => {
        mockSocketEventHandlers.set(event, handler)
      }),
      joinRoom: vi.fn().mockResolvedValue(undefined),
      leaveRoom: vi.fn().mockResolvedValue(undefined),
      sendOperation: vi.fn().mockResolvedValue({ success: true }),
      requestSync: vi.fn()
    }

    // Mock socket factory
    mockSocketFactory = {
      createSocketIO: vi.fn().mockReturnValue(mockSocket),
      createNativeWebSocket: vi.fn().mockReturnValue(mockNativeWebSocket)
    }

    // Default config (Socket.IO mode)
    mockConfig = {
      url: 'http://localhost:3000',
      options: {
        path: '/socket.io',
        transports: ['websocket', 'polling']
      }
    }
  })

  afterEach(() => {
    if (service) {
      service.destroy()
    }
    vi.useRealTimers()
  })

  describe('Constructor and Initialization', () => {
    it('should initialize with Socket.IO mode when path is /socket.io', () => {
      service = new SocketService({
        socketFactory: mockSocketFactory,
        logger: mockLogger,
        config: mockConfig
      })

      expect(mockSocketFactory.createSocketIO).toHaveBeenCalledWith(
        'http://localhost:3000',
        expect.objectContaining({
          path: '/socket.io',
          transports: ['websocket', 'polling']
        })
      )
      expect(mockLogger.info).toHaveBeenCalledWith(
        expect.stringContaining('Initializing SocketService')
      )
      expect(mockLogger.info).toHaveBeenCalledWith(
        expect.stringContaining('RPI Backend (Socket.IO)')
      )
    })

    it('should initialize with Native WebSocket mode when path is /ws', () => {
      mockConfig.options.path = '/ws'

      service = new SocketService({
        socketFactory: mockSocketFactory,
        logger: mockLogger,
        config: mockConfig
      })

      expect(mockSocketFactory.createNativeWebSocket).toHaveBeenCalledWith({
        url: 'http://localhost:3000',
        path: '/ws',
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        timeout: 10000
      })
      expect(mockLogger.info).toHaveBeenCalledWith(
        expect.stringContaining('ESP32 (Native WebSocket)')
      )
      expect(mockNativeWebSocket.connect).toHaveBeenCalled()
    })

    it('should setup connection handlers for Socket.IO', () => {
      service = new SocketService({
        socketFactory: mockSocketFactory,
        logger: mockLogger,
        config: mockConfig
      })

      expect(mockSocket.on).toHaveBeenCalledWith('connect', expect.any(Function))
      expect(mockSocket.on).toHaveBeenCalledWith('disconnect', expect.any(Function))
      expect(mockSocket.on).toHaveBeenCalledWith('connect_error', expect.any(Function))
      expect(mockSocket.on).toHaveBeenCalledWith('reconnect', expect.any(Function))
    })

    it('should setup standardized event handlers for Socket.IO', () => {
      service = new SocketService({
        socketFactory: mockSocketFactory,
        logger: mockLogger,
        config: mockConfig
      })

      expect(mockSocket.on).toHaveBeenCalledWith('connection_status', expect.any(Function))
      expect(mockSocket.on).toHaveBeenCalledWith('ack:join', expect.any(Function))
      expect(mockSocket.on).toHaveBeenCalledWith('ack:leave', expect.any(Function))
      expect(mockSocket.on).toHaveBeenCalledWith('ack:op', expect.any(Function))
      expect(mockSocket.on).toHaveBeenCalledWith('err:op', expect.any(Function))
    })

    it('should start health check interval', () => {
      service = new SocketService({
        socketFactory: mockSocketFactory,
        logger: mockLogger,
        config: mockConfig
      })

      // Trigger connect to set connected = true
      mockSocket.connected = true
      const connectHandler = mockSocketEventHandlers.get('connect')
      connectHandler!()

      // Fast-forward 30 seconds
      vi.advanceTimersByTime(30000)

      expect(mockSocket.emit).toHaveBeenCalledWith('client_ping', {
        timestamp: expect.any(Number)
      })
    })

    it('should manually connect Socket.IO if not auto-connected', () => {
      mockSocket.connected = false

      service = new SocketService({
        socketFactory: mockSocketFactory,
        logger: mockLogger,
        config: mockConfig
      })

      expect(mockSocket.connect).toHaveBeenCalled()
      expect(mockLogger.info).toHaveBeenCalledWith(
        expect.stringContaining('Manually connecting')
      )
    })
  })

  describe('Socket.IO Connection Lifecycle', () => {
    beforeEach(() => {
      service = new SocketService({
        socketFactory: mockSocketFactory,
        logger: mockLogger,
        config: mockConfig
      })
    })

    it('should handle successful connection', () => {
      const connectHandler = mockSocketEventHandlers.get('connect')

      connectHandler!()

      expect(mockLogger.info).toHaveBeenCalledWith(
        expect.stringContaining('CONNECTED'),
        expect.any(Object)
      )
      expect(service.isConnected()).toBe(true)
    })

    it('should emit internal connection_changed event on connect', () => {
      const mockHandler = vi.fn()
      service.on('internal:connection_changed', mockHandler)

      const connectHandler = mockSocketEventHandlers.get('connect')
      connectHandler!()

      // Fast-forward to allow async emit
      vi.advanceTimersByTime(0)

      expect(mockHandler).toHaveBeenCalledWith({ connected: true })
    })

    it('should perform post-connection sync after connect', () => {
      mockSocket.connected = true
      const connectHandler = mockSocketEventHandlers.get('connect')
      connectHandler!()

      // Fast-forward past sync delay (1000ms)
      vi.advanceTimersByTime(1000)

      expect(mockSocket.emit).toHaveBeenCalledWith(
        'client:request_current_state',
        expect.objectContaining({
          timestamp: expect.any(Number),
          client_id: 'test-socket-id',
          requested_states: ['player', 'track_position']
        })
      )
    })

    it('should handle disconnection', () => {
      const disconnectHandler = mockSocketEventHandlers.get('disconnect')

      disconnectHandler!('transport close')

      expect(mockLogger.warn).toHaveBeenCalledWith(
        expect.stringContaining('disconnected')
      )
      expect(service.isConnected()).toBe(false)
      expect(service.isReady()).toBe(false)
    })

    it('should emit internal connection_changed event on disconnect', () => {
      const mockHandler = vi.fn()
      service.on('internal:connection_changed', mockHandler)

      const disconnectHandler = mockSocketEventHandlers.get('disconnect')
      disconnectHandler!('transport error')

      expect(mockHandler).toHaveBeenCalledWith({
        connected: false,
        reason: 'transport error'
      })
    })

    it('should handle connection errors', () => {
      const errorHandler = mockSocketEventHandlers.get('connect_error')
      const error = new Error('Connection failed')

      errorHandler!(error)

      expect(mockLogger.error).toHaveBeenCalledWith(
        expect.stringContaining('ERROR'),
        expect.any(Object)
      )
    })

    it('should stop reconnection after max attempts', () => {
      const mockFailureHandler = vi.fn()
      service.on('internal:connection_failed', mockFailureHandler)

      const errorHandler = mockSocketEventHandlers.get('connect_error')

      // Trigger 10 connection errors
      for (let i = 0; i < 10; i++) {
        errorHandler!(new Error('Connection failed'))
      }

      expect(mockFailureHandler).toHaveBeenCalledWith({
        error: expect.any(Error)
      })
    })

    it('should handle reconnection', () => {
      const reconnectHandler = mockSocketEventHandlers.get('reconnect')

      reconnectHandler!(3)

      expect(mockLogger.info).toHaveBeenCalledWith(
        expect.stringContaining('reconnected')
      )
    })

    it('should resubscribe to rooms after reconnection', async () => {
      // Join a room first
      mockSocket.connected = true
      const joinPromise = service.joinRoom('playlists')

      const joinAckHandler = mockSocketEventHandlers.get('ack:join')
      joinAckHandler!({ room: 'playlists', success: true })
      await joinPromise

      // Clear previous emit calls
      vi.clearAllMocks()

      // Mock the rejoin acknowledgment handler
      const rejoinAckHandler = vi.fn((data: any) => {
        if (data.room === 'playlists') {
          // Auto-acknowledge the rejoin
          const handler = mockSocketEventHandlers.get('ack:join')
          if (handler) {
            handler({ room: 'playlists', success: true })
          }
        }
      })

      // Replace the emit mock to auto-acknowledge
      ;(mockSocket.emit as Mock).mockImplementation(rejoinAckHandler)

      // Trigger reconnect
      const reconnectHandler = mockSocketEventHandlers.get('reconnect')
      reconnectHandler!(1)

      // Fast-forward for sync delay
      vi.advanceTimersByTime(1500)

      // Room should have been rejoined
      expect(rejoinAckHandler).toHaveBeenCalledWith('join:playlists', {})
    })

    it('should log debug message on successful resubscription', async () => {
      // Join a room first
      mockSocket.connected = true
      const joinPromise = service.joinRoom('playlists')

      const joinAckHandler = mockSocketEventHandlers.get('ack:join')
      joinAckHandler!({ room: 'playlists', success: true })
      await joinPromise

      // Clear previous logs
      vi.clearAllMocks()

      // Mock the rejoin acknowledgment handler - call it immediately
      ;(mockSocket.emit as Mock).mockImplementation((event: string, data: any) => {
        if (event === 'join:playlists') {
          // Immediately trigger the ack handler
          const handler = mockSocketEventHandlers.get('ack:join')
          if (handler) {
            // Use queueMicrotask to ensure async behavior
            queueMicrotask(() => handler({ room: 'playlists', success: true }))
          }
        }
      })

      // Trigger reconnect
      const reconnectHandler = mockSocketEventHandlers.get('reconnect')
      reconnectHandler!(1)

      // Flush all pending microtasks and timers
      await vi.advanceTimersByTimeAsync(1)

      // Debug log should have been called
      expect(mockLogger.debug).toHaveBeenCalledWith(
        expect.stringContaining('Resubscribed to room: playlists')
      )
    })

    it('should handle errors during resubscription', async () => {
      // Join a room first
      mockSocket.connected = true
      const joinPromise = service.joinRoom('playlists')

      const joinAckHandler = mockSocketEventHandlers.get('ack:join')
      joinAckHandler!({ room: 'playlists', success: true })
      await joinPromise

      // Clear previous calls
      vi.clearAllMocks()

      // Mock rejoin to fail (timeout)
      ;(mockSocket.emit as Mock).mockImplementation(() => {
        // Don't call the ack handler - let it timeout
      })

      // Trigger reconnect
      const reconnectHandler = mockSocketEventHandlers.get('reconnect')
      reconnectHandler!(1)

      // Flush pending promises and advance past timeout
      await vi.advanceTimersByTimeAsync(10000)

      // Error log should have been called
      expect(mockLogger.error).toHaveBeenCalledWith(
        expect.stringContaining('Failed to resubscribe to room playlists'),
        expect.any(Error)
      )
    })
  })

  describe('Native WebSocket Mode', () => {
    beforeEach(() => {
      mockConfig.options.path = '/ws'
      service = new SocketService({
        socketFactory: mockSocketFactory,
        logger: mockLogger,
        config: mockConfig
      })
    })

    it('should handle native websocket connection', () => {
      const connectionHandler = mockSocketEventHandlers.get('internal:connection_changed')

      connectionHandler!({ connected: true })

      expect(mockLogger.info).toHaveBeenCalledWith(
        expect.stringContaining('NATIVE WEBSOCKET CONNECTED'),
        expect.any(Object)
      )
      expect(service.isConnected()).toBe(true)
    })

    it('should handle native websocket disconnection', () => {
      const connectionHandler = mockSocketEventHandlers.get('internal:connection_changed')

      connectionHandler!({ connected: false, reason: 'server closed' })

      expect(mockLogger.warn).toHaveBeenCalledWith(
        expect.stringContaining('disconnected')
      )
      expect(service.isConnected()).toBe(false)
    })

    it('should handle native websocket connection error', () => {
      const errorHandler = mockSocketEventHandlers.get('internal:connection_error')

      errorHandler!({ error: 'Connection timeout' })

      expect(mockLogger.error).toHaveBeenCalledWith(
        expect.stringContaining('WEBSOCKET CONNECTION ERROR'),
        'Connection timeout'
      )
    })

    it('should delegate joinRoom to native websocket', async () => {
      const joinPromise = service.joinRoom('playlists')

      await joinPromise

      expect(mockNativeWebSocket.joinRoom).toHaveBeenCalledWith('playlists')
    })

    it('should delegate leaveRoom to native websocket', async () => {
      const leavePromise = service.leaveRoom('playlists')

      await leavePromise

      expect(mockNativeWebSocket.leaveRoom).toHaveBeenCalledWith('playlists')
    })

    it('should delegate sendOperation to native websocket', async () => {
      const result = await service.sendOperation('player:play', { playlist_id: '123' }, 'op-123')

      expect(mockNativeWebSocket.sendOperation).toHaveBeenCalledWith(
        'player:play',
        { playlist_id: '123' },
        'op-123'
      )
      expect(result).toEqual({ success: true })
    })

    it('should delegate requestSync to native websocket', () => {
      service.requestSync(10, { 'playlist-1': 5 })

      expect(mockNativeWebSocket.requestSync).toHaveBeenCalledWith(10, { 'playlist-1': 5 })
    })

    it('should perform post-connection sync in ESP32 mode', () => {
      // Set up connection
      const connectionHandler = mockSocketEventHandlers.get('internal:connection_changed')
      connectionHandler!({ connected: true })

      // Fast-forward to trigger sync delay (1000ms)
      vi.advanceTimersByTime(1000)

      expect(mockNativeWebSocket.emit).toHaveBeenCalledWith(
        'client:request_current_state',
        expect.objectContaining({
          timestamp: expect.any(Number),
          requested_states: ['player', 'track_position']
        })
      )
    })
  })

  describe('Event Subscription (on/off/once)', () => {
    beforeEach(() => {
      service = new SocketService({
        socketFactory: mockSocketFactory,
        logger: mockLogger,
        config: mockConfig
      })
    })

    it('should register event handler with on()', () => {
      const mockHandler = vi.fn()
      service.on('state:player', mockHandler)

      const playerHandler = mockSocketEventHandlers.get('state:player')
      const testData = {
        event_type: 'state:player',
        data: { is_playing: true },
        server_seq: 1,
        timestamp: Date.now()
      }
      playerHandler!(testData)

      expect(mockHandler).toHaveBeenCalledWith(testData)
    })

    it('should unregister event handler with off()', () => {
      const mockHandler = vi.fn()
      service.on('state:player', mockHandler)
      service.off('state:player', mockHandler)

      const playerHandler = mockSocketEventHandlers.get('state:player')
      const testData = {
        event_type: 'state:player',
        data: { is_playing: true },
        server_seq: 1,
        timestamp: Date.now()
      }
      playerHandler!(testData)

      expect(mockHandler).not.toHaveBeenCalled()
    })

    it('should register one-time event handler with once()', () => {
      const mockHandler = vi.fn()
      service.once('state:player', mockHandler)

      const playerHandler = mockSocketEventHandlers.get('state:player')
      const testData1 = {
        event_type: 'state:player',
        data: { is_playing: true },
        server_seq: 1,
        timestamp: Date.now()
      }
      playerHandler!(testData1)

      expect(mockHandler).toHaveBeenCalledTimes(1)

      // Second emission should not trigger handler
      const testData2 = {
        event_type: 'state:player',
        data: { is_playing: false },
        server_seq: 2,
        timestamp: Date.now()
      }
      playerHandler!(testData2)

      expect(mockHandler).toHaveBeenCalledTimes(1)
    })

    it('should handle multiple handlers for same event', () => {
      const mockHandler1 = vi.fn()
      const mockHandler2 = vi.fn()
      service.on('state:player', mockHandler1)
      service.on('state:player', mockHandler2)

      const playerHandler = mockSocketEventHandlers.get('state:player')
      const testData = {
        event_type: 'state:player',
        data: { is_playing: true },
        server_seq: 1,
        timestamp: Date.now()
      }
      playerHandler!(testData)

      expect(mockHandler1).toHaveBeenCalledWith(testData)
      expect(mockHandler2).toHaveBeenCalledWith(testData)
    })

    it('should handle errors in event handlers gracefully', () => {
      const errorHandler = vi.fn(() => {
        throw new Error('Handler error')
      })
      const normalHandler = vi.fn()

      service.on('state:player', errorHandler)
      service.on('state:player', normalHandler)

      const playerHandler = mockSocketEventHandlers.get('state:player')
      const testData = {
        event_type: 'state:player',
        data: { is_playing: true },
        server_seq: 1,
        timestamp: Date.now()
      }
      playerHandler!(testData)

      // Both handlers should be called despite error
      expect(errorHandler).toHaveBeenCalled()
      expect(normalHandler).toHaveBeenCalled()
      expect(mockLogger.error).toHaveBeenCalledWith(
        expect.stringContaining('Error in event handler'),
        expect.any(Error)
      )
    })
  })

  describe('Event Emission', () => {
    beforeEach(() => {
      service = new SocketService({
        socketFactory: mockSocketFactory,
        logger: mockLogger,
        config: mockConfig
      })
    })

    it('should emit events when connected', () => {
      mockSocket.connected = true
      const connectHandler = mockSocketEventHandlers.get('connect')
      connectHandler!()

      service.emit('test:event', { data: 'test' })

      expect(mockSocket.emit).toHaveBeenCalledWith('test:event', { data: 'test' })
    })

    it('should log warning when emitting while disconnected', () => {
      mockSocket.connected = false

      service.emit('test:event', { data: 'test' })

      expect(mockLogger.warn).toHaveBeenCalledWith(
        expect.stringContaining('Cannot emit')
      )
    })

    it('should emit to native websocket in ESP32 mode', () => {
      mockConfig.options.path = '/ws'
      service.destroy()
      service = new SocketService({
        socketFactory: mockSocketFactory,
        logger: mockLogger,
        config: mockConfig
      })

      // Set up connection
      const connectionHandler = mockSocketEventHandlers.get('internal:connection_changed')
      connectionHandler!({ connected: true })

      service.emit('test:event', { data: 'test' })

      expect(mockNativeWebSocket.emit).toHaveBeenCalledWith('test:event', { data: 'test' })
    })
  })

  describe('Room Management', () => {
    beforeEach(() => {
      service = new SocketService({
        socketFactory: mockSocketFactory,
        logger: mockLogger,
        config: mockConfig
      })
      mockSocket.connected = true
    })

    it('should successfully join playlists room', async () => {
      const joinPromise = service.joinRoom('playlists')

      const ackHandler = mockSocketEventHandlers.get('ack:join')
      ackHandler!({ room: 'playlists', success: true })

      await expect(joinPromise).resolves.toBeUndefined()
      expect(mockSocket.emit).toHaveBeenCalledWith('join:playlists', {})
    })

    it('should successfully join specific playlist room', async () => {
      const joinPromise = service.joinRoom('playlist:123')

      const ackHandler = mockSocketEventHandlers.get('ack:join')
      ackHandler!({ room: 'playlist:123', success: true })

      await expect(joinPromise).resolves.toBeUndefined()
      expect(mockSocket.emit).toHaveBeenCalledWith('join:playlist', {
        playlist_id: '123'
      })
    })

    it('should successfully join nfc room', async () => {
      const joinPromise = service.joinRoom('nfc')

      const ackHandler = mockSocketEventHandlers.get('ack:join')
      ackHandler!({ room: 'nfc', success: true })

      await expect(joinPromise).resolves.toBeUndefined()
      expect(mockSocket.emit).toHaveBeenCalledWith('join:nfc', {})
    })

    it('should handle generic room join', async () => {
      const joinPromise = service.joinRoom('custom-room')

      const ackHandler = mockSocketEventHandlers.get('ack:join')
      ackHandler!({ room: 'custom-room', success: true })

      await expect(joinPromise).resolves.toBeUndefined()
      expect(mockSocket.emit).toHaveBeenCalledWith('join:custom-room', {})
    })

    it('should reject join on failure', async () => {
      const joinPromise = service.joinRoom('playlists')

      const ackHandler = mockSocketEventHandlers.get('ack:join')
      ackHandler!({
        room: 'playlists',
        success: false,
        message: 'Room not found'
      })

      await expect(joinPromise).rejects.toThrow('Room not found')
    })

    it('should timeout join after 10 seconds', async () => {
      const joinPromise = service.joinRoom('playlists')

      vi.advanceTimersByTime(10000)

      await expect(joinPromise).rejects.toThrow('Join room timeout')
    })

    it('should reuse existing join promise for same room', async () => {
      // Start two joinRoom calls before any resolves
      const joinPromise1 = service.joinRoom('playlists')
      const joinPromise2 = service.joinRoom('playlists')

      // Should only emit once (cached promise is reused)
      expect(mockSocket.emit).toHaveBeenCalledTimes(1)
      expect(mockSocket.emit).toHaveBeenCalledWith('join:playlists', {})

      // Resolve the promise
      const ackHandler = mockSocketEventHandlers.get('ack:join')
      ackHandler!({ room: 'playlists', success: true })

      // Both promises should resolve successfully
      await expect(joinPromise1).resolves.toBeUndefined()
      await expect(joinPromise2).resolves.toBeUndefined()
    })

    it('should track subscribed rooms', async () => {
      const joinPromise = service.joinRoom('playlists')

      const ackHandler = mockSocketEventHandlers.get('ack:join')
      ackHandler!({ room: 'playlists', success: true })

      await joinPromise

      expect(service.getSubscribedRooms()).toContain('playlists')
    })

    it('should successfully leave room', async () => {
      const leavePromise = service.leaveRoom('playlists')

      const ackHandler = mockSocketEventHandlers.get('ack:leave')
      ackHandler!({ room: 'playlists', success: true })

      await expect(leavePromise).resolves.toBeUndefined()
      expect(mockSocket.emit).toHaveBeenCalledWith('leave:playlists', {})
    })

    it('should handle generic room leave', async () => {
      const leavePromise = service.leaveRoom('custom-room')

      const ackHandler = mockSocketEventHandlers.get('ack:leave')
      ackHandler!({ room: 'custom-room', success: true })

      await expect(leavePromise).resolves.toBeUndefined()
      expect(mockSocket.emit).toHaveBeenCalledWith('leave:custom-room', {})
    })

    it('should successfully leave specific playlist room', async () => {
      const leavePromise = service.leaveRoom('playlist:abc123')

      const ackHandler = mockSocketEventHandlers.get('ack:leave')
      ackHandler!({ room: 'playlist:abc123', success: true })

      await expect(leavePromise).resolves.toBeUndefined()
      expect(mockSocket.emit).toHaveBeenCalledWith('leave:playlist', { playlist_id: 'abc123' })
    })

    it('should successfully leave nfc room', async () => {
      const leavePromise = service.leaveRoom('nfc')

      const ackHandler = mockSocketEventHandlers.get('ack:leave')
      ackHandler!({ room: 'nfc', success: true })

      await expect(leavePromise).resolves.toBeUndefined()
      expect(mockSocket.emit).toHaveBeenCalledWith('leave:nfc', {})
    })

    it('should timeout leave after 10 seconds', async () => {
      const leavePromise = service.leaveRoom('playlists')

      vi.advanceTimersByTime(10000)

      await expect(leavePromise).rejects.toThrow('Leave room timeout')
    })

    it('should remove room from subscribed list on leave', async () => {
      // Join first
      const joinPromise = service.joinRoom('playlists')
      const joinAckHandler = mockSocketEventHandlers.get('ack:join')
      joinAckHandler!({ room: 'playlists', success: true })
      await joinPromise

      // Then leave
      const leavePromise = service.leaveRoom('playlists')
      const leaveAckHandler = mockSocketEventHandlers.get('ack:leave')
      leaveAckHandler!({ room: 'playlists', success: true })
      await leavePromise

      expect(service.getSubscribedRooms()).not.toContain('playlists')
    })
  })

  describe('Operation Tracking', () => {
    beforeEach(() => {
      service = new SocketService({
        socketFactory: mockSocketFactory,
        logger: mockLogger,
        config: mockConfig
      })
      mockSocket.connected = true
    })

    it('should successfully track operation with acknowledgment', async () => {
      const opPromise = service.sendOperation(
        'player:play',
        { playlist_id: '123' },
        'op-123'
      )

      const ackHandler = mockSocketEventHandlers.get('ack:op')
      ackHandler!({
        client_op_id: 'op-123',
        success: true,
        server_seq: 5,
        playlist_seq: 3
      })

      await expect(opPromise).resolves.toEqual({
        client_op_id: 'op-123',
        success: true,
        server_seq: 5,
        playlist_seq: 3
      })

      expect(mockSocket.emit).toHaveBeenCalledWith('player:play', {
        playlist_id: '123'
      })
    })

    it('should reject operation on error', async () => {
      const opPromise = service.sendOperation(
        'player:play',
        { playlist_id: '123' },
        'op-123'
      )

      const errHandler = mockSocketEventHandlers.get('err:op')
      errHandler!({
        client_op_id: 'op-123',
        success: false,
        message: 'Playlist not found'
      })

      await expect(opPromise).rejects.toThrow('Playlist not found')
    })

    it('should timeout operation after 30 seconds', async () => {
      const opPromise = service.sendOperation(
        'player:play',
        { playlist_id: '123' },
        'op-123'
      )

      vi.advanceTimersByTime(30000)

      await expect(opPromise).rejects.toThrow('Operation timeout')
    })
  })

  describe('State Synchronization', () => {
    beforeEach(() => {
      service = new SocketService({
        socketFactory: mockSocketFactory,
        logger: mockLogger,
        config: mockConfig
      })
      mockSocket.connected = true
    })

    it('should request sync with current state', () => {
      service.requestSync(10, { 'playlist-1': 5, 'playlist-2': 3 })

      expect(mockSocket.emit).toHaveBeenCalledWith('sync:request', {
        last_global_seq: 10,
        last_playlist_seqs: { 'playlist-1': 5, 'playlist-2': 3 },
        requested_rooms: expect.any(Array)
      })
    })

    it('should use last known seq if not provided', () => {
      const statusHandler = mockSocketEventHandlers.get('connection_status')
      statusHandler!({ sid: 'test', server_seq: 15, server_time: Date.now() })

      service.requestSync()

      expect(mockSocket.emit).toHaveBeenCalledWith('sync:request', {
        last_global_seq: 15,
        last_playlist_seqs: undefined,
        requested_rooms: expect.any(Array)
      })
    })

    it('should handle connection_status event', () => {
      const statusHandler = mockSocketEventHandlers.get('connection_status')
      const testData = {
        sid: 'server-123',
        server_seq: 42,
        server_time: 1234567890,
        status: 'connected'
      }

      statusHandler!(testData)

      expect(service.isReady()).toBe(true)
      expect(service.getLastServerSeq()).toBe(42)
    })

    it('should handle state event with sequence ordering', () => {
      const mockHandler = vi.fn()
      service.on('state:player', mockHandler)

      const playerHandler = mockSocketEventHandlers.get('state:player')

      // Send in order
      playerHandler!({
        event_type: 'state:player',
        data: { is_playing: true },
        server_seq: 1,
        timestamp: Date.now()
      })

      expect(mockHandler).toHaveBeenCalledTimes(1)
    })

    it('should buffer out-of-order events', () => {
      const mockHandler = vi.fn()
      service.on('state:player', mockHandler)

      const playerHandler = mockSocketEventHandlers.get('state:player')

      // Send out of order (seq 3 before 1)
      playerHandler!({
        event_type: 'state:player',
        data: { is_playing: true },
        server_seq: 3,
        timestamp: Date.now()
      })

      // Should not be processed yet
      expect(mockHandler).not.toHaveBeenCalled()

      // Send seq 1
      playerHandler!({
        event_type: 'state:player',
        data: { is_playing: false },
        server_seq: 1,
        timestamp: Date.now()
      })

      // Should process seq 1
      expect(mockHandler).toHaveBeenCalledTimes(1)
    })

    it('should skip sequence ordering for track_position events', () => {
      const mockHandler = vi.fn()
      service.on('state:track_position', mockHandler)

      const trackPosHandler = mockSocketEventHandlers.get('state:track_position')

      // Track position should be processed immediately regardless of sequence
      trackPosHandler!({
        event_type: 'state:track_position',
        data: { position_ms: 1000 },
        server_seq: 999,
        timestamp: Date.now()
      })

      expect(mockHandler).toHaveBeenCalledTimes(1)
    })

    it('should dispatch DOM events for state changes', () => {
      const domEventSpy = vi.spyOn(window, 'dispatchEvent')

      const playerHandler = mockSocketEventHandlers.get('state:player')
      const testData = {
        event_type: 'state:player',
        data: { is_playing: true },
        server_seq: 1,
        timestamp: Date.now()
      }

      playerHandler!(testData)

      expect(domEventSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'state:player',
          detail: testData
        })
      )
    })
  })

  describe('Utility Methods', () => {
    beforeEach(() => {
      service = new SocketService({
        socketFactory: mockSocketFactory,
        logger: mockLogger,
        config: mockConfig
      })
    })

    it('should return connection status', () => {
      expect(service.isConnected()).toBe(false)

      mockSocket.connected = true
      const connectHandler = mockSocketEventHandlers.get('connect')
      connectHandler!()

      expect(service.isConnected()).toBe(true)
    })

    it('should return ready status', () => {
      expect(service.isReady()).toBe(false)

      const statusHandler = mockSocketEventHandlers.get('connection_status')
      statusHandler!({ sid: 'test', server_seq: 1, server_time: Date.now() })

      expect(service.isReady()).toBe(true)
    })

    it('should return last server sequence', () => {
      const statusHandler = mockSocketEventHandlers.get('connection_status')
      statusHandler!({ sid: 'test', server_seq: 99, server_time: Date.now() })

      expect(service.getLastServerSeq()).toBe(99)
    })

    it('should return subscribed rooms', async () => {
      mockSocket.connected = true

      const joinPromise = service.joinRoom('playlists')
      const ackHandler = mockSocketEventHandlers.get('ack:join')
      ackHandler!({ room: 'playlists', success: true })
      await joinPromise

      const rooms = service.getSubscribedRooms()
      expect(rooms).toContain('playlists')
      expect(rooms).toHaveLength(1)
    })
  })

  describe('Cleanup and Destruction', () => {
    beforeEach(() => {
      service = new SocketService({
        socketFactory: mockSocketFactory,
        logger: mockLogger,
        config: mockConfig
      })
    })

    it('should cleanup resources on destroy', () => {
      service.destroy()

      expect(mockSocket.disconnect).toHaveBeenCalled()
    })

    it('should reject pending operations on destroy', async () => {
      mockSocket.connected = true

      const opPromise = service.sendOperation(
        'player:play',
        { playlist_id: '123' },
        'op-123'
      )

      service.destroy()

      await expect(opPromise).rejects.toThrow('Socket service destroyed')
    })

    it('should clear timers on destroy', () => {
      const clearIntervalSpy = vi.spyOn(global, 'clearInterval')
      const clearTimeoutSpy = vi.spyOn(global, 'clearTimeout')

      service.destroy()

      expect(clearIntervalSpy).toHaveBeenCalled()
    })

    it('should destroy native websocket in ESP32 mode', () => {
      mockConfig.options.path = '/ws'
      service.destroy()
      service = new SocketService({
        socketFactory: mockSocketFactory,
        logger: mockLogger,
        config: mockConfig
      })

      service.destroy()

      expect(mockNativeWebSocket.destroy).toHaveBeenCalled()
    })
  })

  describe('Error Handling', () => {
    beforeEach(() => {
      service = new SocketService({
        socketFactory: mockSocketFactory,
        logger: mockLogger,
        config: mockConfig
      })
    })

    it('should handle errors in DOM event dispatch', () => {
      const domEventSpy = vi.spyOn(window, 'dispatchEvent').mockImplementation(() => {
        throw new Error('DOM error')
      })

      const playerHandler = mockSocketEventHandlers.get('state:player')
      const testData = {
        event_type: 'state:player',
        data: { is_playing: true },
        server_seq: 1,
        timestamp: Date.now()
      }

      // Should not throw
      playerHandler!(testData)

      expect(mockLogger.error).toHaveBeenCalledWith(
        expect.stringContaining('Failed to dispatch DOM event'),
        expect.any(Error)
      )
    })

    it('should handle errors in state event processing', () => {
      const playerHandler = mockSocketEventHandlers.get('state:player')

      // Send invalid data that might cause errors
      playerHandler!(null)

      expect(mockLogger.error).toHaveBeenCalledWith(
        expect.stringContaining('Error processing'),
        expect.any(Error)
      )
    })

    it('should not perform sync when not connected', () => {
      // Set socket as disconnected initially
      mockSocket.connected = false

      // Trigger connect (this will schedule a sync after 1000ms)
      const connectHandler = mockSocketEventHandlers.get('connect')
      connectHandler!()

      // Disconnect before the sync executes
      const disconnectHandler = mockSocketEventHandlers.get('disconnect')
      disconnectHandler!('test disconnect')

      // Clear mocks to check what happens during sync attempt
      vi.clearAllMocks()

      // Fast-forward to when sync would execute
      vi.advanceTimersByTime(1000)

      // Should log warning since we're not connected
      expect(mockLogger.warn).toHaveBeenCalledWith(
        expect.stringContaining('Cannot perform post-connection sync')
      )

      // Should NOT emit sync request
      expect(mockSocket.emit).not.toHaveBeenCalledWith(
        'client:request_current_state',
        expect.any(Object)
      )
    })

    it('should handle errors in post-connection sync', () => {
      // Mock socket.emit to throw an error
      ;(mockSocket.emit as Mock).mockImplementation(() => {
        throw new Error('Socket emit failed')
      })

      mockSocket.connected = true
      const connectHandler = mockSocketEventHandlers.get('connect')
      connectHandler!()

      // Fast-forward to trigger sync
      vi.advanceTimersByTime(1000)

      // Should log error
      expect(mockLogger.error).toHaveBeenCalledWith(
        expect.stringContaining('Error in post-connection sync'),
        expect.any(Error)
      )
    })
  })
})
