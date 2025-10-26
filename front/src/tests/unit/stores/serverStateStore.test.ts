/**
 * Basic tests for serverStateStore
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useServerStateStore } from '@/stores/serverStateStore'

// Mock socket service
vi.mock('@/services/socketService', () => ({
  default: {
    on: vi.fn(),
    off: vi.fn(),
    emit: vi.fn()
  }
}))

describe('serverStateStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('should initialize successfully', () => {
    const store = useServerStateStore()
    expect(store).toBeDefined()
    expect(typeof store).toBe('object')
  })

  it('should have playlists property', () => {
    const store = useServerStateStore()
    expect(store).toHaveProperty('playlists')
    expect(Array.isArray(store.playlists)).toBe(true)
  })
})
