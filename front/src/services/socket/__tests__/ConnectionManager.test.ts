/**
 * Connection Manager Tests
 *
 * Complete test coverage for ConnectionManager class
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { ConnectionManager } from '../ConnectionManager'
import type { Socket } from 'socket.io-client'

// Mock logger
vi.mock('@/utils/logger', () => ({
  logger: {
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn()
  }
}))

describe('ConnectionManager', () => {
  let connectionManager: ConnectionManager
  let mockSocket: Partial<Socket>
  let socketHandlers: Map<string, Function>

  beforeEach(() => {
    socketHandlers = new Map()
    mockSocket = {
      id: 'test-socket-id',
      on: vi.fn((event, handler) => {
        socketHandlers.set(event, handler)
      })
    }

    connectionManager = new ConnectionManager({
      maxReconnectionAttempts: 5,
      reconnectionDelay: 1000
    })
  })

  describe('Initialization', () => {
    it('should initialize with disconnected status', () => {
      const status = connectionManager.getStatus()

      expect(status.connected).toBe(false)
      expect(status.ready).toBe(false)
      expect(status.lastSeq).toBe(0)
    })

    it('should not be connected initially', () => {
      expect(connectionManager.isConnected()).toBe(false)
    })

    it('should not be ready initially', () => {
      expect(connectionManager.isReady()).toBe(false)
    })

    it('should have zero reconnection attempts initially', () => {
      expect(connectionManager.getReconnectionAttempts()).toBe(0)
    })
  })

  describe('setupHandlers', () => {
    beforeEach(() => {
      connectionManager.setupHandlers(mockSocket as Socket)
    })

    it('should register socket event handlers', () => {
      expect(mockSocket.on).toHaveBeenCalledWith('connect', expect.any(Function))
      expect(mockSocket.on).toHaveBeenCalledWith('disconnect', expect.any(Function))
      expect(mockSocket.on).toHaveBeenCalledWith('connect_error', expect.any(Function))
      expect(mockSocket.on).toHaveBeenCalledWith('reconnect', expect.any(Function))
      expect(mockSocket.on).toHaveBeenCalledWith('connection_status', expect.any(Function))
    })

    describe('connect event', () => {
      it('should update status on connect', () => {
        const connectHandler = socketHandlers.get('connect')!
        connectHandler()

        expect(connectionManager.isConnected()).toBe(true)
        expect(connectionManager.getReconnectionAttempts()).toBe(0)
      })

      it('should emit connected event', () => {
        const handler = vi.fn()
        connectionManager.on('connected', handler)

        const connectHandler = socketHandlers.get('connect')!
        connectHandler()

        expect(handler).toHaveBeenCalledWith({ socketId: 'test-socket-id' })
      })
    })

    describe('disconnect event', () => {
      it('should update status on disconnect', () => {
        // First connect
        socketHandlers.get('connect')!()
        expect(connectionManager.isConnected()).toBe(true)

        // Then disconnect
        const disconnectHandler = socketHandlers.get('disconnect')!
        disconnectHandler('transport close')

        expect(connectionManager.isConnected()).toBe(false)
        expect(connectionManager.isReady()).toBe(false)
      })

      it('should emit disconnected event with reason', () => {
        const handler = vi.fn()
        connectionManager.on('disconnected', handler)

        const disconnectHandler = socketHandlers.get('disconnect')!
        disconnectHandler('transport close')

        expect(handler).toHaveBeenCalledWith({ reason: 'transport close' })
      })
    })

    describe('connect_error event', () => {
      it('should increment reconnection attempts', () => {
        const errorHandler = socketHandlers.get('connect_error')!
        const error = new Error('Connection failed')

        errorHandler(error)
        expect(connectionManager.getReconnectionAttempts()).toBe(1)

        errorHandler(error)
        expect(connectionManager.getReconnectionAttempts()).toBe(2)
      })

      it('should emit reconnecting event', () => {
        const handler = vi.fn()
        connectionManager.on('reconnecting', handler)

        const errorHandler = socketHandlers.get('connect_error')!
        errorHandler(new Error('Connection failed'))

        expect(handler).toHaveBeenCalledWith({
          attempt: 1,
          error: 'Connection failed'
        })
      })

      it('should emit connection_failed when max attempts reached', () => {
        const handler = vi.fn()
        connectionManager.on('connection_failed', handler)

        const errorHandler = socketHandlers.get('connect_error')!
        const error = new Error('Connection failed')

        // Trigger 5 errors (max attempts)
        for (let i = 0; i < 5; i++) {
          errorHandler(error)
        }

        expect(handler).toHaveBeenCalledWith({ error })
      })

      it('should not emit connection_failed before max attempts', () => {
        const handler = vi.fn()
        connectionManager.on('connection_failed', handler)

        const errorHandler = socketHandlers.get('connect_error')!
        const error = new Error('Connection failed')

        // Trigger 4 errors (below max)
        for (let i = 0; i < 4; i++) {
          errorHandler(error)
        }

        expect(handler).not.toHaveBeenCalled()
      })
    })

    describe('reconnect event', () => {
      it('should reset reconnection attempts on successful reconnect', () => {
        const errorHandler = socketHandlers.get('connect_error')!
        const error = new Error('Connection failed')

        // Fail 3 times
        errorHandler(error)
        errorHandler(error)
        errorHandler(error)
        expect(connectionManager.getReconnectionAttempts()).toBe(3)

        // Then reconnect
        const reconnectHandler = socketHandlers.get('reconnect')!
        reconnectHandler(3)

        expect(connectionManager.getReconnectionAttempts()).toBe(0)
      })

      it('should emit connected event with reconnected flag', () => {
        const handler = vi.fn()
        connectionManager.on('connected', handler)

        const reconnectHandler = socketHandlers.get('reconnect')!
        reconnectHandler(2)

        expect(handler).toHaveBeenCalledWith({
          socketId: 'test-socket-id',
          reconnected: true
        })
      })
    })

    describe('connection_status event', () => {
      it('should mark connection as ready', () => {
        const statusHandler = socketHandlers.get('connection_status')!
        statusHandler({
          sid: 'server-123',
          server_seq: 42,
          server_time: 1234567890
        })

        expect(connectionManager.isReady()).toBe(true)
      })

      it('should update connection status with server data', () => {
        const statusHandler = socketHandlers.get('connection_status')!
        statusHandler({
          sid: 'server-123',
          server_seq: 42,
          server_time: 1234567890
        })

        const status = connectionManager.getStatus()
        expect(status.serverId).toBe('server-123')
        expect(status.lastSeq).toBe(42)
        expect(status.serverTime).toBe(1234567890)
      })

      it('should emit ready event', () => {
        const handler = vi.fn()
        connectionManager.on('ready', handler)

        const statusHandler = socketHandlers.get('connection_status')!
        const data = {
          sid: 'server-123',
          server_seq: 42,
          server_time: 1234567890
        }
        statusHandler(data)

        expect(handler).toHaveBeenCalledWith(data)
      })
    })
  })

  describe('Sequence Management', () => {
    it('should update last sequence when higher', () => {
      connectionManager.updateLastSeq(10)
      expect(connectionManager.getLastSeq()).toBe(10)

      connectionManager.updateLastSeq(20)
      expect(connectionManager.getLastSeq()).toBe(20)
    })

    it('should not update last sequence when lower or equal', () => {
      connectionManager.updateLastSeq(20)
      expect(connectionManager.getLastSeq()).toBe(20)

      connectionManager.updateLastSeq(15)
      expect(connectionManager.getLastSeq()).toBe(20)

      connectionManager.updateLastSeq(20)
      expect(connectionManager.getLastSeq()).toBe(20)
    })
  })

  describe('Event Handlers', () => {
    it('should add event listeners', () => {
      const handler1 = vi.fn()
      const handler2 = vi.fn()

      connectionManager.on('connected', handler1)
      connectionManager.on('connected', handler2)

      connectionManager.setupHandlers(mockSocket as Socket)
      socketHandlers.get('connect')!()

      expect(handler1).toHaveBeenCalled()
      expect(handler2).toHaveBeenCalled()
    })

    it('should remove event listeners', () => {
      const handler = vi.fn()
      connectionManager.on('connected', handler)
      connectionManager.off('connected', handler)

      connectionManager.setupHandlers(mockSocket as Socket)
      socketHandlers.get('connect')!()

      expect(handler).not.toHaveBeenCalled()
    })

    it('should handle errors in event handlers gracefully', () => {
      const errorHandler = vi.fn(() => {
        throw new Error('Handler error')
      })
      const goodHandler = vi.fn()

      connectionManager.on('connected', errorHandler)
      connectionManager.on('connected', goodHandler)

      connectionManager.setupHandlers(mockSocket as Socket)

      // Should not throw
      expect(() => socketHandlers.get('connect')!()).not.toThrow()

      // Good handler should still be called
      expect(goodHandler).toHaveBeenCalled()
    })
  })

  describe('reset', () => {
    it('should reset connection state', () => {
      // Set some state
      connectionManager.setupHandlers(mockSocket as Socket)
      socketHandlers.get('connect')!()
      socketHandlers.get('connection_status')!({
        sid: 'server-123',
        server_seq: 42,
        server_time: 1234567890
      })
      connectionManager.updateLastSeq(100)

      // Reset
      connectionManager.reset()

      const status = connectionManager.getStatus()
      expect(status.connected).toBe(false)
      expect(status.ready).toBe(false)
      expect(status.lastSeq).toBe(0)
      expect(status.serverId).toBeUndefined()
      expect(connectionManager.getReconnectionAttempts()).toBe(0)
    })
  })

  describe('destroy', () => {
    it('should clear all event handlers', () => {
      const handler = vi.fn()
      connectionManager.on('connected', handler)

      connectionManager.destroy()

      connectionManager.setupHandlers(mockSocket as Socket)
      socketHandlers.get('connect')!()

      expect(handler).not.toHaveBeenCalled()
    })

    it('should reset connection state', () => {
      connectionManager.setupHandlers(mockSocket as Socket)
      socketHandlers.get('connect')!()

      connectionManager.destroy()

      expect(connectionManager.isConnected()).toBe(false)
      expect(connectionManager.isReady()).toBe(false)
    })
  })

  describe('getStatus immutability', () => {
    it('should return a copy of status, not the original', () => {
      const status1 = connectionManager.getStatus()
      status1.connected = true
      status1.lastSeq = 999

      const status2 = connectionManager.getStatus()
      expect(status2.connected).toBe(false)
      expect(status2.lastSeq).toBe(0)
    })
  })
})
