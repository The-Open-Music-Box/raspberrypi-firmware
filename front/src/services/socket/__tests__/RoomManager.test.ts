/**
 * Room Manager Tests
 *
 * Complete test coverage for RoomManager class
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { RoomManager } from '../RoomManager'
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

describe('RoomManager', () => {
  let roomManager: RoomManager
  let mockSocket: Partial<Socket>
  let emitCallback: ((response: any) => void) | undefined

  beforeEach(() => {
    emitCallback = undefined
    mockSocket = {
      id: 'test-socket-id',
      emit: vi.fn((event, data, callback) => {
        // Store callback for later invocation in tests
        if (typeof callback === 'function') {
          emitCallback = callback
        }
      })
    }

    roomManager = new RoomManager()
    roomManager.setSocket(mockSocket as Socket)
  })

  describe('Initialization', () => {
    it('should initialize with no subscriptions', () => {
      const rooms = roomManager.getSubscribedRooms()
      expect(rooms).toEqual([])
      expect(roomManager.getSubscriptionCount()).toBe(0)
    })

    it('should initialize with no pending joins', () => {
      expect(roomManager.getPendingJoinCount()).toBe(0)
    })

    it('should not be subscribed to any room initially', () => {
      expect(roomManager.isSubscribed('test-room')).toBe(false)
    })
  })

  describe('setSocket', () => {
    it('should set socket instance', () => {
      const newManager = new RoomManager()
      expect(() => newManager.setSocket(mockSocket as Socket)).not.toThrow()
    })

    it('should allow changing socket instance', () => {
      const newSocket = { id: 'new-socket', emit: vi.fn() } as Partial<Socket>
      roomManager.setSocket(newSocket as Socket)
      // Socket should be usable after setting
      expect(() => roomManager.joinRoom('test')).not.toThrow()
    })
  })

  describe('joinRoom', () => {
    it('should throw error if socket not initialized', async () => {
      const manager = new RoomManager()
      await expect(manager.joinRoom('test-room')).rejects.toThrow('Socket not initialized')
    })

    it('should emit join_room event', async () => {
      const joinPromise = roomManager.joinRoom('test-room')

      expect(mockSocket.emit).toHaveBeenCalledWith(
        'join_room',
        { room: 'test-room' },
        expect.any(Function)
      )

      // Simulate successful response
      emitCallback!({ success: true })
      await joinPromise
    })

    it('should add room to subscribed rooms on success', async () => {
      const joinPromise = roomManager.joinRoom('test-room')
      emitCallback!({ success: true })
      await joinPromise

      expect(roomManager.isSubscribed('test-room')).toBe(true)
      expect(roomManager.getSubscribedRooms()).toContain('test-room')
    })

    it('should emit room_joined event on success', async () => {
      const handler = vi.fn()
      roomManager.on('room_joined', handler)

      const joinPromise = roomManager.joinRoom('test-room')
      emitCallback!({ success: true })
      await joinPromise

      expect(handler).toHaveBeenCalledWith({ room: 'test-room' })
    })

    it('should reject promise on failure', async () => {
      const joinPromise = roomManager.joinRoom('test-room')
      emitCallback!({ success: false, error: 'Room not found' })

      await expect(joinPromise).rejects.toThrow('Room not found')
    })

    it('should emit room_error event on failure', async () => {
      const handler = vi.fn()
      roomManager.on('room_error', handler)

      const joinPromise = roomManager.joinRoom('test-room')
      emitCallback!({ success: false, error: 'Room not found' })

      await expect(joinPromise).rejects.toThrow()
      expect(handler).toHaveBeenCalledWith({
        room: 'test-room',
        error: 'Room not found'
      })
    })

    it('should not add room to subscriptions on failure', async () => {
      const joinPromise = roomManager.joinRoom('test-room')
      emitCallback!({ success: false, error: 'Room not found' })

      await expect(joinPromise).rejects.toThrow()
      expect(roomManager.isSubscribed('test-room')).toBe(false)
    })

    it('should return immediately if already subscribed', async () => {
      // First join
      const join1 = roomManager.joinRoom('test-room')
      emitCallback!({ success: true })
      await join1

      // Second join should return immediately
      const join2 = roomManager.joinRoom('test-room')
      await join2

      // emit should only be called once
      expect(mockSocket.emit).toHaveBeenCalledTimes(1)
    })

    it('should return existing promise if join in progress', async () => {
      const join1 = roomManager.joinRoom('test-room')
      const join2 = roomManager.joinRoom('test-room')

      // Should return the cached pending promise
      // Both should resolve when the response comes back
      emitCallback!({ success: true })

      await expect(Promise.all([join1, join2])).resolves.toBeDefined()

      // emit should only be called once since second call returned cached promise
      expect(mockSocket.emit).toHaveBeenCalledTimes(1)
    })

    it('should handle multiple room joins', async () => {
      const join1 = roomManager.joinRoom('room1')
      const callback1 = emitCallback!
      const join2 = roomManager.joinRoom('room2')
      const callback2 = emitCallback!

      callback1({ success: true })
      callback2({ success: true })

      await Promise.all([join1, join2])

      expect(roomManager.isSubscribed('room1')).toBe(true)
      expect(roomManager.isSubscribed('room2')).toBe(true)
      expect(roomManager.getSubscriptionCount()).toBe(2)
    })

    it('should timeout after 5 seconds', async () => {
      vi.useFakeTimers()

      const joinPromise = roomManager.joinRoom('test-room')

      // Fast-forward 5 seconds
      vi.advanceTimersByTime(5000)

      await expect(joinPromise).rejects.toThrow('Room join timeout: test-room')

      vi.useRealTimers()
    })

    it('should emit room_error on timeout', async () => {
      vi.useFakeTimers()

      const handler = vi.fn()
      roomManager.on('room_error', handler)

      const joinPromise = roomManager.joinRoom('test-room')
      vi.advanceTimersByTime(5000)

      await expect(joinPromise).rejects.toThrow()
      expect(handler).toHaveBeenCalledWith({
        room: 'test-room',
        error: 'Room join timeout: test-room'
      })

      vi.useRealTimers()
    })

    it('should handle default error message', async () => {
      const joinPromise = roomManager.joinRoom('test-room')
      emitCallback!({ success: false })

      await expect(joinPromise).rejects.toThrow('Unknown error')
    })
  })

  describe('leaveRoom', () => {
    beforeEach(async () => {
      // Subscribe to a room first
      const joinPromise = roomManager.joinRoom('test-room')
      emitCallback!({ success: true })
      await joinPromise
    })

    it('should throw error if socket not initialized', async () => {
      const manager = new RoomManager()
      await expect(manager.leaveRoom('test-room')).rejects.toThrow('Socket not initialized')
    })

    it('should emit leave_room event', async () => {
      const leavePromise = roomManager.leaveRoom('test-room')

      expect(mockSocket.emit).toHaveBeenCalledWith(
        'leave_room',
        { room: 'test-room' },
        expect.any(Function)
      )

      emitCallback!({ success: true })
      await leavePromise
    })

    it('should remove room from subscriptions on success', async () => {
      const leavePromise = roomManager.leaveRoom('test-room')
      emitCallback!({ success: true })
      await leavePromise

      expect(roomManager.isSubscribed('test-room')).toBe(false)
      expect(roomManager.getSubscribedRooms()).not.toContain('test-room')
    })

    it('should emit room_left event on success', async () => {
      const handler = vi.fn()
      roomManager.on('room_left', handler)

      const leavePromise = roomManager.leaveRoom('test-room')
      emitCallback!({ success: true })
      await leavePromise

      expect(handler).toHaveBeenCalledWith({ room: 'test-room' })
    })

    it('should reject promise on failure', async () => {
      const leavePromise = roomManager.leaveRoom('test-room')
      emitCallback!({ success: false, error: 'Permission denied' })

      await expect(leavePromise).rejects.toThrow('Permission denied')
    })

    it('should emit room_error event on failure', async () => {
      const handler = vi.fn()
      roomManager.on('room_error', handler)

      const leavePromise = roomManager.leaveRoom('test-room')
      emitCallback!({ success: false, error: 'Permission denied' })

      await expect(leavePromise).rejects.toThrow()
      expect(handler).toHaveBeenCalledWith({
        room: 'test-room',
        error: 'Permission denied'
      })
    })

    it('should not remove room from subscriptions on failure', async () => {
      const leavePromise = roomManager.leaveRoom('test-room')
      emitCallback!({ success: false, error: 'Error' })

      await expect(leavePromise).rejects.toThrow()
      expect(roomManager.isSubscribed('test-room')).toBe(true)
    })

    it('should return immediately if not subscribed', async () => {
      const initialCallCount = (mockSocket.emit as any).mock.calls.length

      await roomManager.leaveRoom('non-existent-room')

      // emit should not be called for non-existent room
      expect((mockSocket.emit as any).mock.calls.length).toBe(initialCallCount)
    })

    it('should timeout after 5 seconds', async () => {
      vi.useFakeTimers()

      const leavePromise = roomManager.leaveRoom('test-room')
      vi.advanceTimersByTime(5000)

      await expect(leavePromise).rejects.toThrow('Room leave timeout: test-room')

      vi.useRealTimers()
    })

    it('should emit room_error on timeout', async () => {
      vi.useFakeTimers()

      const handler = vi.fn()
      roomManager.on('room_error', handler)

      const leavePromise = roomManager.leaveRoom('test-room')
      vi.advanceTimersByTime(5000)

      await expect(leavePromise).rejects.toThrow()
      expect(handler).toHaveBeenCalledWith({
        room: 'test-room',
        error: 'Room leave timeout: test-room'
      })

      vi.useRealTimers()
    })

    it('should handle default error message', async () => {
      const leavePromise = roomManager.leaveRoom('test-room')
      emitCallback!({ success: false })

      await expect(leavePromise).rejects.toThrow('Unknown error')
    })
  })

  describe('getSubscribedRooms', () => {
    it('should return empty array initially', () => {
      expect(roomManager.getSubscribedRooms()).toEqual([])
    })

    it('should return array of subscribed rooms', async () => {
      const join1 = roomManager.joinRoom('room1')
      const callback1 = emitCallback!
      const join2 = roomManager.joinRoom('room2')
      const callback2 = emitCallback!

      callback1({ success: true })
      callback2({ success: true })

      await Promise.all([join1, join2])

      const rooms = roomManager.getSubscribedRooms()
      expect(rooms).toContain('room1')
      expect(rooms).toContain('room2')
      expect(rooms).toHaveLength(2)
    })

    it('should return copy of rooms array', async () => {
      const join = roomManager.joinRoom('room1')
      emitCallback!({ success: true })
      await join

      const rooms1 = roomManager.getSubscribedRooms()
      rooms1.push('fake-room')

      const rooms2 = roomManager.getSubscribedRooms()
      expect(rooms2).not.toContain('fake-room')
      expect(rooms2).toHaveLength(1)
    })
  })

  describe('isSubscribed', () => {
    it('should return false for non-subscribed room', () => {
      expect(roomManager.isSubscribed('test-room')).toBe(false)
    })

    it('should return true for subscribed room', async () => {
      const join = roomManager.joinRoom('test-room')
      emitCallback!({ success: true })
      await join

      expect(roomManager.isSubscribed('test-room')).toBe(true)
    })

    it('should return false after leaving room', async () => {
      const join = roomManager.joinRoom('test-room')
      emitCallback!({ success: true })
      await join

      const leave = roomManager.leaveRoom('test-room')
      emitCallback!({ success: true })
      await leave

      expect(roomManager.isSubscribed('test-room')).toBe(false)
    })
  })

  describe('resubscribeAll', () => {
    it('should throw error if socket not initialized', async () => {
      const manager = new RoomManager()
      await expect(manager.resubscribeAll()).rejects.toThrow('Socket not initialized')
    })

    it('should do nothing if no rooms subscribed', async () => {
      const initialCallCount = (mockSocket.emit as any).mock.calls.length
      await roomManager.resubscribeAll()

      expect((mockSocket.emit as any).mock.calls.length).toBe(initialCallCount)
    })

    it('should rejoin all subscribed rooms', async () => {
      // Subscribe to multiple rooms
      const join1 = roomManager.joinRoom('room1')
      const callback1 = emitCallback!
      const join2 = roomManager.joinRoom('room2')
      const callback2 = emitCallback!
      const join3 = roomManager.joinRoom('room3')
      const callback3 = emitCallback!

      callback1({ success: true })
      callback2({ success: true })
      callback3({ success: true })

      await Promise.all([join1, join2, join3])

      // Clear mock calls
      ;(mockSocket.emit as any).mockClear()

      // Resubscribe
      const resubPromise = roomManager.resubscribeAll()

      // Simulate successful responses for all rooms
      const calls = (mockSocket.emit as any).mock.calls
      calls.forEach((call: any) => {
        const callback = call[2]
        callback({ success: true })
      })

      await resubPromise

      // Should have called emit for each room
      expect(mockSocket.emit).toHaveBeenCalledTimes(3)
      expect(roomManager.isSubscribed('room1')).toBe(true)
      expect(roomManager.isSubscribed('room2')).toBe(true)
      expect(roomManager.isSubscribed('room3')).toBe(true)
    })

    it('should handle partial failures gracefully', async () => {
      // Subscribe to rooms
      const join1 = roomManager.joinRoom('room1')
      const callback1 = emitCallback!
      const join2 = roomManager.joinRoom('room2')
      const callback2 = emitCallback!

      callback1({ success: true })
      callback2({ success: true })
      await Promise.all([join1, join2])

      ;(mockSocket.emit as any).mockClear()

      // Resubscribe
      const resubPromise = roomManager.resubscribeAll()

      // Simulate mixed responses
      const calls = (mockSocket.emit as any).mock.calls
      calls[0][2]({ success: true })
      calls[1][2]({ success: false, error: 'Failed' })

      await resubPromise

      // Should have attempted both
      expect(roomManager.isSubscribed('room1')).toBe(true)
      expect(roomManager.isSubscribed('room2')).toBe(false)
    })
  })

  describe('clearSubscriptions', () => {
    it('should clear all subscriptions', async () => {
      const join1 = roomManager.joinRoom('room1')
      const callback1 = emitCallback!
      const join2 = roomManager.joinRoom('room2')
      const callback2 = emitCallback!

      callback1({ success: true })
      callback2({ success: true })
      await Promise.all([join1, join2])

      roomManager.clearSubscriptions()

      expect(roomManager.getSubscriptionCount()).toBe(0)
      expect(roomManager.getSubscribedRooms()).toEqual([])
    })

    it('should clear pending joins', () => {
      roomManager.joinRoom('room1')
      roomManager.joinRoom('room2')

      expect(roomManager.getPendingJoinCount()).toBe(2)

      roomManager.clearSubscriptions()

      expect(roomManager.getPendingJoinCount()).toBe(0)
    })
  })

  describe('Event Handlers', () => {
    it('should register event handlers', () => {
      const handler = vi.fn()
      roomManager.on('room_joined', handler)

      // Trigger event by joining room
      const join = roomManager.joinRoom('test-room')
      emitCallback!({ success: true })

      // Handler should be called
      expect(handler).toHaveBeenCalled()
    })

    it('should remove event handlers', async () => {
      const handler = vi.fn()
      roomManager.on('room_joined', handler)
      roomManager.off('room_joined', handler)

      const join = roomManager.joinRoom('test-room')
      emitCallback!({ success: true })
      await join

      expect(handler).not.toHaveBeenCalled()
    })

    it('should handle errors in event handlers gracefully', async () => {
      const errorHandler = vi.fn(() => {
        throw new Error('Handler error')
      })
      const goodHandler = vi.fn()

      roomManager.on('room_joined', errorHandler)
      roomManager.on('room_joined', goodHandler)

      const join = roomManager.joinRoom('test-room')
      emitCallback!({ success: true })

      await expect(join).resolves.toBeUndefined()
      expect(goodHandler).toHaveBeenCalled()
    })

    it('should support multiple handlers for same event', async () => {
      const handler1 = vi.fn()
      const handler2 = vi.fn()
      const handler3 = vi.fn()

      roomManager.on('room_joined', handler1)
      roomManager.on('room_joined', handler2)
      roomManager.on('room_joined', handler3)

      const join = roomManager.joinRoom('test-room')
      emitCallback!({ success: true })
      await join

      expect(handler1).toHaveBeenCalled()
      expect(handler2).toHaveBeenCalled()
      expect(handler3).toHaveBeenCalled()
    })
  })

  describe('getSubscriptionCount', () => {
    it('should return 0 initially', () => {
      expect(roomManager.getSubscriptionCount()).toBe(0)
    })

    it('should return correct count after subscriptions', async () => {
      const join1 = roomManager.joinRoom('room1')
      const callback1 = emitCallback!
      const join2 = roomManager.joinRoom('room2')
      const callback2 = emitCallback!
      const join3 = roomManager.joinRoom('room3')
      const callback3 = emitCallback!

      callback1({ success: true })
      callback2({ success: true })
      callback3({ success: true })

      await Promise.all([join1, join2, join3])

      expect(roomManager.getSubscriptionCount()).toBe(3)
    })

    it('should update after leaving rooms', async () => {
      const join = roomManager.joinRoom('room1')
      emitCallback!({ success: true })
      await join

      expect(roomManager.getSubscriptionCount()).toBe(1)

      const leave = roomManager.leaveRoom('room1')
      emitCallback!({ success: true })
      await leave

      expect(roomManager.getSubscriptionCount()).toBe(0)
    })
  })

  describe('getPendingJoinCount', () => {
    it('should return 0 initially', () => {
      expect(roomManager.getPendingJoinCount()).toBe(0)
    })

    it('should track pending joins', () => {
      roomManager.joinRoom('room1')
      roomManager.joinRoom('room2')

      expect(roomManager.getPendingJoinCount()).toBe(2)
    })

    it('should decrement after join completes', async () => {
      const join = roomManager.joinRoom('room1')
      expect(roomManager.getPendingJoinCount()).toBe(1)

      emitCallback!({ success: true })
      await join

      expect(roomManager.getPendingJoinCount()).toBe(0)
    })

    it('should decrement after join fails', async () => {
      const join = roomManager.joinRoom('room1')
      expect(roomManager.getPendingJoinCount()).toBe(1)

      emitCallback!({ success: false, error: 'Failed' })

      await expect(join).rejects.toThrow()
      expect(roomManager.getPendingJoinCount()).toBe(0)
    })
  })

  describe('destroy', () => {
    it('should clear all subscriptions', async () => {
      const join = roomManager.joinRoom('room1')
      emitCallback!({ success: true })
      await join

      roomManager.destroy()

      expect(roomManager.getSubscriptionCount()).toBe(0)
    })

    it('should clear event handlers', async () => {
      const handler = vi.fn()
      roomManager.on('room_joined', handler)

      roomManager.destroy()

      // Try to join after destroy
      roomManager.setSocket(mockSocket as Socket)
      const join = roomManager.joinRoom('room1')
      emitCallback!({ success: true })
      await join

      expect(handler).not.toHaveBeenCalled()
    })

    it('should null out socket', () => {
      roomManager.destroy()

      expect(async () => {
        await roomManager.joinRoom('test-room')
      }).rejects.toThrow('Socket not initialized')
    })
  })
})
