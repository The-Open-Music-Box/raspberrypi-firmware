/**
 * Basic tests for socketService
 * Note: More comprehensive tests exist in src/services/__tests__/socketService.bridge.test.ts
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock socket.io-client
vi.mock('socket.io-client', () => ({
  io: vi.fn(() => ({
    on: vi.fn(),
    off: vi.fn(),
    emit: vi.fn(),
    connect: vi.fn(),
    disconnect: vi.fn(),
    connected: false
  }))
}))

describe('socketService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should be importable', async () => {
    const { default: socketService } = await import('@/services/socketService')
    expect(socketService).toBeDefined()
    expect(typeof socketService.on).toBe('function')
    expect(typeof socketService.emit).toBe('function')
  })

  it('should have required methods', async () => {
    const { default: socketService } = await import('@/services/socketService')
    expect(socketService).toHaveProperty('on')
    expect(socketService).toHaveProperty('off')
    expect(socketService).toHaveProperty('emit')
  })
})
