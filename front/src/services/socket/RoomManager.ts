/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Room Manager
 *
 * Single Responsibility: Manage Socket.IO room subscriptions
 * - Join/leave rooms
 * - Track subscribed rooms
 * - Handle room acknowledgments
 * - Re-subscribe after reconnect
 */

import { Socket } from 'socket.io-client'
import { logger } from '@/utils/logger'

export interface RoomSubscription {
  room: string
  subscribedAt: number
}

export type RoomEventType = 'room_joined' | 'room_left' | 'room_error'

export class RoomManager {
  private subscribedRooms = new Set<string>()
  private pendingJoins = new Map<string, Promise<void>>()
  private eventHandlers = new Map<RoomEventType, Set<(data?: any) => void>>()
  private socket: Socket | null = null

  /**
   * Set the socket instance to use for room operations
   */
  setSocket(socket: Socket): void {
    this.socket = socket
  }

  /**
   * Join a Socket.IO room
   */
  async joinRoom(room: string): Promise<void> {
    if (!this.socket) {
      throw new Error('Socket not initialized')
    }

    // If already subscribed, return immediately
    if (this.subscribedRooms.has(room)) {
      logger.debug(`Already subscribed to room: ${room}`)
      return
    }

    // If join is already in progress, return existing promise
    if (this.pendingJoins.has(room)) {
      return this.pendingJoins.get(room)
    }

    // Create new join promise
    const joinPromise = new Promise<void>((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        this.pendingJoins.delete(room)
        const error = new Error(`Room join timeout: ${room}`)
        this.emit('room_error', { room, error: error.message })
        reject(error)
      }, 5000)

      this.socket!.emit(
        'join_room',
        { room },
        (response: { success: boolean; error?: string }) => {
          clearTimeout(timeoutId)
          this.pendingJoins.delete(room)

          if (response.success) {
            this.subscribedRooms.add(room)
            logger.info(`Joined room: ${room}`)
            this.emit('room_joined', { room })
            resolve()
          } else {
            const error = response.error || 'Unknown error'
            logger.error(`Failed to join room ${room}: ${error}`)
            this.emit('room_error', { room, error })
            reject(new Error(error))
          }
        }
      )
    })

    this.pendingJoins.set(room, joinPromise)
    return joinPromise
  }

  /**
   * Leave a Socket.IO room
   */
  async leaveRoom(room: string): Promise<void> {
    if (!this.socket) {
      throw new Error('Socket not initialized')
    }

    if (!this.subscribedRooms.has(room)) {
      logger.debug(`Not subscribed to room: ${room}`)
      return
    }

    return new Promise<void>((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        const error = new Error(`Room leave timeout: ${room}`)
        this.emit('room_error', { room, error: error.message })
        reject(error)
      }, 5000)

      this.socket!.emit(
        'leave_room',
        { room },
        (response: { success: boolean; error?: string }) => {
          clearTimeout(timeoutId)

          if (response.success) {
            this.subscribedRooms.delete(room)
            logger.info(`Left room: ${room}`)
            this.emit('room_left', { room })
            resolve()
          } else {
            const error = response.error || 'Unknown error'
            logger.error(`Failed to leave room ${room}: ${error}`)
            this.emit('room_error', { room, error })
            reject(new Error(error))
          }
        }
      )
    })
  }

  /**
   * Get list of currently subscribed rooms
   */
  getSubscribedRooms(): string[] {
    return Array.from(this.subscribedRooms)
  }

  /**
   * Check if subscribed to a room
   */
  isSubscribed(room: string): boolean {
    return this.subscribedRooms.has(room)
  }

  /**
   * Re-subscribe to all rooms (used after reconnect)
   */
  async resubscribeAll(): Promise<void> {
    if (!this.socket) {
      throw new Error('Socket not initialized')
    }

    const rooms = Array.from(this.subscribedRooms)
    if (rooms.length === 0) {
      return
    }

    logger.info(`Re-subscribing to ${rooms.length} rooms`)

    // Clear current subscriptions since we're reconnecting
    this.subscribedRooms.clear()

    // Re-join all rooms
    const promises = rooms.map(room => this.joinRoom(room))
    await Promise.allSettled(promises)
  }

  /**
   * Clear all subscriptions (used on disconnect)
   */
  clearSubscriptions(): void {
    this.subscribedRooms.clear()
    this.pendingJoins.clear()
  }

  /**
   * Event subscription
   */
  on(event: RoomEventType, handler: (data?: any) => void): void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, new Set())
    }
    this.eventHandlers.get(event)!.add(handler)
  }

  /**
   * Remove event listener
   */
  off(event: RoomEventType, handler: (data?: any) => void): void {
    const handlers = this.eventHandlers.get(event)
    if (handlers) {
      handlers.delete(handler)
    }
  }

  /**
   * Emit event to handlers
   */
  private emit(event: RoomEventType, data?: any): void {
    const handlers = this.eventHandlers.get(event)
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(data)
        } catch (error) {
          logger.error(`Error in room event handler for ${event}:`, error)
        }
      })
    }
  }

  /**
   * Get count of subscribed rooms
   */
  getSubscriptionCount(): number {
    return this.subscribedRooms.size
  }

  /**
   * Get count of pending joins
   */
  getPendingJoinCount(): number {
    return this.pendingJoins.size
  }

  /**
   * Cleanup
   */
  destroy(): void {
    this.clearSubscriptions()
    this.eventHandlers.clear()
    this.socket = null
  }
}
