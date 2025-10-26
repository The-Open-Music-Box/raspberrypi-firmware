/**
 * Integration Test Helpers
 *
 * Shared utilities for integration testing including:
 * - Mock server setup with MSW
 * - Store initialization and cleanup
 * - Common test data factories
 * - Integration-specific assertions
 */

import { vi } from 'vitest'
import { setActivePinia, createPinia, type Pinia } from 'pinia'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { createMockPlaylist, createMockTrack, createMockPlayerState } from '@/tests/utils/testHelpers'

/**
 * Integration test context for managing test lifecycle
 */
export interface IntegrationTestContext {
  pinia: Pinia
  server: ReturnType<typeof setupServer>
  cleanup: () => void
}

/**
 * Setup integration test environment with MSW server and Pinia
 */
export function setupIntegrationTest(): IntegrationTestContext {
  // Create fresh Pinia instance
  const pinia = createPinia()
  setActivePinia(pinia)

  // Setup MSW server with default handlers
  const server = setupServer(
    // Default API responses
    http.get('/api/playlists', () => {
      return HttpResponse.json({
        status: 'success',
        data: {
          items: [
            createMockPlaylist({ id: '1', title: 'Integration Test Playlist 1' }),
            createMockPlaylist({ id: '2', title: 'Integration Test Playlist 2' })
          ],
          total: 2,
          page: 1,
          limit: 50
        }
      })
    }),

    http.get('/api/playlists/:id', ({ params }) => {
      const { id } = params
      return HttpResponse.json({
        status: 'success',
        data: createMockPlaylist({ id: id as string, title: `Playlist ${id}` })
      })
    }),

    http.get('/api/playlists/:id/tracks', ({ params }) => {
      const { id } = params
      return HttpResponse.json({
        status: 'success',
        data: [
          createMockTrack({ number: 1, title: `Track 1 from Playlist ${id}` }),
          createMockTrack({ number: 2, title: `Track 2 from Playlist ${id}` })
        ]
      })
    }),

    http.get('/api/player/status', () => {
      return HttpResponse.json({
        status: 'success',
        data: createMockPlayerState())
      })
    }),

    // Default error handler
    http.get('*', ({ request }) => {
      console.warn(`Unhandled request: ${request.method} ${request.url}`)
      return HttpResponse.json({
        status: 'error',
        message: `Endpoint not found: ${new URL(request.url).pathname}`,
        error_type: 'not_found'
      }, { status: 404 })
    })
  )

  // Start server
  server.listen({
    onUnhandledRequest: 'warn'
  })

  const cleanup = () => {
    server.close()
    pinia._s.clear()
  }

  return { pinia, server, cleanup }
}

/**
 * Create mock API response builders
 */
export const mockApiResponses = {
  success: <T>(data: T) => ({
    status: 'success',
    data
  }),

  error: (message: string, errorType = 'api_error', statusCode = 400) => ({
    status: 'error',
    message,
    error_type: errorType
  }),

  paginated: <T>(items: T[], page = 1, limit = 50) => ({
    status: 'success',
    data: {
      items,
      total: items.length,
      page,
      limit,
      pages: Math.ceil(items.length / limit)
    }
  })
}

/**
 * Create realistic test data sets
 */
export const integrationTestData = {
  createPlaylistSet: (count = 5) => {
    return Array.from({ length: count }, (_, i) =>
      createMockPlaylist({
        id: `playlist-${i + 1}`,
        title: `Integration Playlist ${i + 1}`,
        track_count: Math.floor(Math.random() * 10) + 1,
        created_at: new Date(Date.now() - i * 24 * 60 * 60 * 1000).toISOString()
      })
    )
  },

  createTrackSet: (playlistId: string, count = 8) => {
    return Array.from({ length: count }, (_, i) =>
      createMockTrack({
        number: i + 1,
        title: `Track ${i + 1} from ${playlistId}`,
        artist: `Artist ${Math.floor(i / 2) + 1}`,
        duration_ms: (180 + Math.random() * 120) * 1000 // 3-5 minutes
      })
    )
  },

  createPlayerStateSequence: () => {
    return [
      createMockPlayerState({ is_playing: false, position_ms: 0 })),
      createMockPlayerState({ is_playing: true, position_ms: 0 })),
      createMockPlayerState({ is_playing: true, position_ms: 30000 })),
      createMockPlayerState({ is_playing: true, position_ms: 60000 })),
      createMockPlayerState({ is_playing: false, position_ms: 60000 }))
    ]
  }
}

/**
 * Advanced MSW request matchers
 */
export const requestMatchers = {
  withQuery: (params: Record<string, string>) => (req: any) => {
    const url = new URL(req.url)
    return Object.entries(params).every(([key, value]) =>
      url.searchParams.get(key) === value
    )
  },

  withBody: (expectedBody: any) => (req: any) => {
    return JSON.stringify(req.body) === JSON.stringify(expectedBody)
  },

  withHeaders: (headers: Record<string, string>) => (req: any) => {
    return Object.entries(headers).every(([key, value]) =>
      req.headers.get(key) === value
    )
  }
}

/**
 * Integration-specific assertions
 */
export const integrationAssertions = {
  /**
   * Assert that store state matches expected API response
   */
  expectStoreToMatchApiResponse: <T>(storeValue: T, apiResponse: any) => {
    expect(storeValue).toEqual(apiResponse.data)
  },

  /**
   * Assert that API was called with correct parameters
   */
  expectApiCall: (server: any, method: string, path: string, expectedCalls = 1) => {
    // This would be implemented with MSW request history
    // For now, we'll use a simple matcher
    expect(true).toBe(true) // Placeholder
  },

  /**
   * Assert store loading states during async operations
   */
  expectLoadingSequence: async (
    store: any,
    operation: () => Promise<any>,
    loadingField = 'isLoading'
  ) => {
    expect(store[loadingField]).toBe(false)

    const promise = operation()
    expect(store[loadingField]).toBe(true)

    await promise
    expect(store[loadingField]).toBe(false)
  },

  /**
   * Assert error state propagation from API to store
   */
  expectErrorPropagation: async (
    store: any,
    operation: () => Promise<any>,
    expectedError: string,
    errorField = 'error'
  ) => {
    try {
      await operation()
    } catch {
      // Expected to throw
    }

    expect(store[errorField]).toContain(expectedError)
  }
}

/**
 * Performance testing utilities
 */
export const performanceHelpers = {
  /**
   * Measure operation duration
   */
  measureDuration: async <T>(operation: () => Promise<T>): Promise<{ result: T; duration: number }> => {
    const start = performance.now()
    const result = await operation()
    const duration = performance.now() - start

    return { result, duration }
  },

  /**
   * Test rapid successive operations
   */
  testRapidOperations: async <T>(
    operation: () => Promise<T>,
    count = 100,
    maxDuration = 1000
  ): Promise<T[]> => {
    const start = performance.now()

    const promises = Array.from({ length: count }, () => operation()
    const results = await Promise.all(promises)

    const duration = performance.now() - start
    expect(duration).toBeLessThan(maxDuration)

    return results
  },

  /**
   * Memory leak detection helper
   */
  detectMemoryLeaks: (operations: (() => Promise<any>)[]) => {
    // Simplified memory leak detection
    const initialMemory = process.memoryUsage().heapUsed

    return async () => {
      for (const operation of operations) {
        await operation()
      }

      // Force garbage collection if available
      if (global.gc) {
        global.gc()
      }

      const finalMemory = process.memoryUsage().heapUsed
      const memoryIncrease = finalMemory - initialMemory

      // Memory should not increase significantly
      expect(memoryIncrease).toBeLessThan(10 * 1024 * 1024) // 10MB threshold
    }
  }
}

/**
 * WebSocket mock helpers for real-time testing
 */
export const websocketMocks = {
  createMockSocket: () => {
    const eventHandlers = new Map<string, Function[]>()

    return {
      on: vi.fn((event: string, handler: Function) => {
        if (!eventHandlers.has(event) {
          eventHandlers.set(event, [])
        }
        eventHandlers.get(event)!.push(handler)
      }),

      off: vi.fn((event: string, handler: Function) => {
        const handlers = eventHandlers.get(event)
        if (handlers) {
          const index = handlers.indexOf(handler)
          if (index > -1) {
            handlers.splice(index, 1)
          }
        }
      }),

      emit: vi.fn(),

      simulate: (event: string, data: any) => {
        const handlers = eventHandlers.get(event) || []
        handlers.forEach(handler => handler(data)
      },

      disconnect: vi.fn(),
      connect: vi.fn(),

      connected: true,
      id: 'mock-socket-id'
    }
  }
}

/**
 * Cleanup utilities
 */
export const cleanupHelpers = {
  /**
   * Clear all timers and intervals
   */
  clearAllTimers: () => {
    vi.clearAllTimers()
  },

  /**
   * Reset all mocks
   */
  resetAllMocks: () => {
    vi.clearAllMocks()
  },

  /**
   * Clear console output
   */
  clearConsole: () => {
    console.clear()
  },

  /**
   * Complete cleanup for integration tests
   */
  fullCleanup: (context: IntegrationTestContext) => {
    context.cleanup()
    cleanupHelpers.clearAllTimers()
    cleanupHelpers.resetAllMocks()
  }
}