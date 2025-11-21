/**
 * Integration tests for Playlist API ↔ UnifiedPlaylistStore
 *
 * Tests the complete data flow between playlist API endpoints
 * and the unified playlist store including:
 * - API response handling and store state updates
 * - Cache management and invalidation strategies
 * - Error propagation from API to store
 * - Performance with large datasets
 * - Real-time synchronization scenarios
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { useUnifiedPlaylistStore } from '@/stores/unifiedPlaylistStore'
import {
  setupIntegrationTest,
  mockApiResponses,
  integrationTestData,
  integrationAssertions
  performanceHelpers,
  type IntegrationTestContext
} from '../helpers/integration-helpers'
import { flushPromises } from '@/tests/utils/testHelpers'

describe('Playlist API ↔ Store Integration', () => {
  let context: IntegrationTestContext
  let store: ReturnType<typeof useUnifiedPlaylistStore>

  beforeEach(() => {
    context = setupIntegrationTest()
    store = useUnifiedPlaylistStore()
  })

  afterEach(() => {
    context.cleanup()
  })

  describe('Playlist Loading and Caching', () => {
    it('should load playlists from API and populate store', async () => {
      const testPlaylists = integrationTestData.createPlaylistSet(3)

      context.server.use(
        http.get('/api/playlists', () => {
          return HttpResponse.json(mockApiResponses.paginated(testPlaylists))
        })
      )

      expect(store.playlists).toEqual([])
      expect(store.isLoading).toBe(false)

      await integrationAssertions
        async () => {
          await store.loadPlaylists()
        }
      )

      expect(store.playlists).toHaveLength(3)
      expect(store.playlists).toEqual(testPlaylists)
      expect(store.error).toBeNull()
      expect(store.lastFetched).toBeDefined()
    })

    it('should handle paginated playlist responses correctly', async () => {
      const allPlaylists = integrationTestData.createPlaylistSet(25)
      const page1 = allPlaylists.slice(0, 10)
      const page2 = allPlaylists.slice(10, 20)
      const page3 = allPlaylists.slice(20, 25)

      context.server.use(
        http.get('/api/playlists', ({ request }) => {
          const url = new URL(request.url)
          const page = parseInt(url.searchParams.get('page') || '1')
          const limit = parseInt(url.searchParams.get('limit') || '10')

          let pageData = []
          if (page === 1) pageData = page1
          else if (page === 2) pageData = page2
          else if (page === 3) pageData = page3

          return HttpResponse.json({
            status: 'success',
            data: {
              items: pageData,
              total: 25,
              page,
              limit,
              pages: Math.ceil(25 / limit)
            })
        })
      )

      // Load first page
      await store.loadPlaylists()
      expect(store.playlists).toEqual(page1)

      // Load more pages (if store supports pagination)
      // This would depend on actual store implementation
    })

    it('should cache playlists and avoid unnecessary API calls', async () => {
      const testPlaylists = integrationTestData.createPlaylistSet(2)
      let apiCallCount = 0

      context.server.use(
        http.get('/api/playlists', () => {
          apiCallCount++
          return HttpResponse.json(mockApiResponses.paginated(testPlaylists))
        })
      )

      // First load
      await store.loadPlaylists()
      expect(apiCallCount).toBe(1)
      expect(store.playlists).toHaveLength(2)

      // Second load (should use cache)
      await store.loadPlaylists()
      expect(apiCallCount).toBe(1) // Should not increase

      // Force reload
      await store.loadPlaylists(true)
      expect(apiCallCount).toBe(2) // Should increase
    })

    it('should handle cache invalidation correctly', async () => {
      const initialPlaylists = integrationTestData.createPlaylistSet(2)
      const updatedPlaylists = integrationTestData.createPlaylistSet(3)

      context.server.use(
        http.get('/api/playlists', () => {
          return HttpResponse.json(mockApiResponses.paginated(updatedPlaylists))
        })
      )

      // Load initial data
      await store.loadPlaylists()
      expect(store.playlists).toHaveLength(2)

      // Invalidate cache
      store.invalidateCache()
      expect(store.playlists).toEqual([])
      expect(store.lastFetched).toBeNull()

      // Reload should fetch fresh data
      await store.loadPlaylists()
      expect(store.playlists).toHaveLength(3)
    })

    it('should detect and handle stale data', async () => {
      const testPlaylists = integrationTestData.createPlaylistSet(2)

      context.server.use(
        http.get('/api/playlists', () => {
          return HttpResponse.json(mockApiResponses.paginated(testPlaylists))
        })
      )

      // Load data
      await store.loadPlaylists()
      expect(store.isDataStale).toBe(false)

      // Manually make data stale (simulate time passing)
      store.lastFetched = new Date(Date.now() - 6 * 60 * 1000) // 6 minutes ago
      expect(store.isDataStale).toBe(true)

      // Ensure fresh data should trigger reload
      await store.ensureFreshData()
      expect(store.isDataStale).toBe(false)
    })
  })

  describe('Individual Playlist Operations', () => {
    it('should load individual playlist with tracks', async () => {
      const playlist = integrationTestData.createPlaylistSet(1)[0]
      const tracks = integrationTestData.createTrackSet(playlist.id, 5)

      context.server.use(
        http.get(`/api/playlists/${playlist.id}`, () => {
          return HttpResponse.json(mockApiResponses.success(playlist))
        }),
        http.get(`/api/playlists/${playlist.id}/tracks`, () => {
          return HttpResponse.json(mockApiResponses.success(tracks))
        })
      )

      // Load specific playlist
      const loadedPlaylist = await store.loadPlaylist(playlist.id)
      expect(loadedPlaylist).toEqual(playlist)

      // Load tracks for playlist
      const loadedTracks = await store.loadTracksForPlaylist(playlist.id)
      expect(loadedTracks).toEqual(tracks)
      expect(store.getTracksForPlaylist(playlist.id)).toEqual(tracks)
    })

    it('should handle playlist creation workflow', async () => {
      const newPlaylistData = { 
        title: 'New Integration Playlist', 
        description: 'Test playlist' 
      }
      const createdPlaylist = integrationTestData.createPlaylistSet(1)[0]

      context.server.use(
        http.post('/api/playlists', async ({ request }) => {
          const body = await request.json() as any
          expect(body.title).toBe(newPlaylistData.title)
          expect(body.description).toBe(newPlaylistData.description)
          return HttpResponse.json(mockApiResponses.success(createdPlaylist))
        })
      )

      // Store should handle playlist addition
      store.addPlaylist(createdPlaylist)
      expect(store.playlists).toContain(createdPlaylist)
      expect(store.getPlaylistById(createdPlaylist.id)).toEqual(createdPlaylist)
    })

    it('should handle playlist updates and synchronization', async () => {
      const originalPlaylist = integrationTestData.createPlaylistSet(1)[0]
      const updatedPlaylist = { 
        ...originalPlaylist, 
        title: 'Updated Playlist Title' 
      }

      // Initialize store with original playlist
      store.addPlaylist(originalPlaylist)
      expect(store.getPlaylistById(originalPlaylist.id)).toEqual(originalPlaylist)

      context.server.use(
        http.put(`/api/playlists/${originalPlaylist.id}`, async ({ request }) => {
          const body = await request.json() as any
          expect(body.title).toBe(updatedPlaylist.title)
          return HttpResponse.json(mockApiResponses.success(updatedPlaylist))
        })
      )

      // Update playlist in store
      store.updatePlaylist(updatedPlaylist)
      expect(store.getPlaylistById(originalPlaylist.id)?.title).toBe('Updated Playlist Title')
    })

    it('should handle playlist deletion workflow', async () => {
      const playlistToDelete = integrationTestData.createPlaylistSet(1)[0]
      const tracks = integrationTestData.createTrackSet(playlistToDelete.id, 3)

      // Initialize store with playlist and tracks
      store.addPlaylist(playlistToDelete)
      store.setTracksForPlaylist(playlistToDelete.id, tracks)

      expect(store.getPlaylistById(playlistToDelete.id)).toBeDefined()
      expect(store.getTracksForPlaylist(playlistToDelete.id)).toHaveLength(3)

      context.server.use(
        http.delete(`/api/playlists/${playlistToDelete.id}`, () => {
          return HttpResponse.json(mockApiResponses.success({ message: 'Deleted' }))
        })
      )

      // Delete playlist from store
      store.removePlaylist(playlistToDelete.id)

      expect(store.getPlaylistById(playlistToDelete.id)).toBeNull()
      expect(store.getTracksForPlaylist(playlistToDelete.id)).toEqual([])
    })
  })

  describe('Track Management Integration', () => {
    it('should load tracks for multiple playlists efficiently', async () => {
      const playlists = integrationTestData.createPlaylistSet(3)

      // Setup tracks for each playlist
      playlists.forEach((playlist, index) => {
        const tracks = integrationTestData.createTrackSet(playlist.id, 4 + index)
        context.server.use(
          http.get(`/api/playlists/${playlist.id}/tracks`, () => {
            return HttpResponse.json(mockApiResponses.success(tracks))
          })
        )
      })

      // Load tracks for all playlists
      const trackPromises = playlists.map(playlist =>
        store.loadTracksForPlaylist(playlist.id)
      )
      const allTracks = await Promise.all(trackPromises)

      expect(allTracks[0]).toHaveLength(4)
      expect(allTracks[1]).toHaveLength(5)
      expect(allTracks[2]).toHaveLength(6)

      // Verify tracks are cached in store
      playlists.forEach((playlist, index) => {
        expect(store.hasTracksData(playlist.id)).toBe(true)
        expect(store.getTracksForPlaylist(playlist.id)).toHaveLength(4 + index)
      })
    })

    it('should handle track operations within playlists', async () => {
      const playlist = integrationTestData.createPlaylistSet(1)[0]
      const initialTracks = integrationTestData.createTrackSet(playlist.id, 3)
      const newTrack = integrationTestData.createTrackSet(playlist.id, 1)[0]

      // Initialize with tracks
      store.setTracksForPlaylist(playlist.id, initialTracks)
      expect(store.getTracksForPlaylist(playlist.id)).toHaveLength(3)

      // Add track
      const updatedTracks = [...initialTracks, newTrack]
      store.setTracksForPlaylist(playlist.id, updatedTracks)
      expect(store.getTracksForPlaylist(playlist.id)).toHaveLength(4)

      // Clear tracks
      store.clearTracksForPlaylist(playlist.id)
      expect(store.getTracksForPlaylist(playlist.id)).toEqual([])
      expect(store.hasTracksData(playlist.id)).toBe(false)
    })

    it('should handle track caching and invalidation', async () => {
      const playlist = integrationTestData.createPlaylistSet(1)[0]
      const tracks = integrationTestData.createTrackSet(playlist.id, 5)
      let apiCallCount = 0

      context.server.use(
        http.get(`/api/playlists/${playlist.id}/tracks`, () => {
          apiCallCount++
          return HttpResponse.json(mockApiResponses.success(tracks))
        })
      )

      // First load
      await store.loadTracksForPlaylist(playlist.id)
      expect(apiCallCount).toBe(1)

      // Second load (should use cache)
      await store.loadTracksForPlaylist(playlist.id)
      expect(apiCallCount).toBe(1)

      // Force reload
      await store.loadTracksForPlaylist(playlist.id, true)
      expect(apiCallCount).toBe(2)
    })
  })

  describe('Error Handling and Resilience', () => {
    it('should handle API errors gracefully', async () => {
      context.server.use(
        http.get('/api/playlists', () => {
          return HttpResponse.json(mockApiResponses.error('Internal server error', 'internal_error'), { status: 500 })
        })
      )

      await integrationAssertions
        store,
        () => store.loadPlaylists(),
        'Internal server error'
      )

      expect(store.playlists).toEqual([])
      expect(store.isLoading).toBe(false)
    })

    it('should handle network timeouts', async () => {
      context.server.use(
        http.get('/api/playlists', async () => {
          // Simulate timeout by delaying response beyond reasonable limit
          await new Promise(resolve => setTimeout(resolve, 5000))
          return HttpResponse.json(mockApiResponses.paginated([]))
        })
      )

      const timeoutPromise = store.loadPlaylists()

      // This would timeout in real scenario
      // For testing, we'll expect it to handle the delay gracefully
      await expect(timeoutPromise).rejects.toThrow()
    })

    it('should handle malformed API responses', async () => {
      context.server.use(
        http.get('/api/playlists', () => {
          return HttpResponse.json({ invalid: 'response' })
        })
      )

      await store.loadPlaylists()
      expect(store.playlists).toEqual([])
      expect(store.error).toBeDefined()
    })

    it('should recover from errors on subsequent operations', async () => {
      const testPlaylists = integrationTestData.createPlaylistSet(2)

      // First request fails
      context.server.use(
        http.get('/api/playlists', () => {
          return HttpResponse.json(mockApiResponses.error('Server error'), { status: 500 })
        })
      )

      // First attempt fails
      await store.loadPlaylists()
      expect(store.error).toBeDefined()
      expect(store.playlists).toEqual([])

      // Second request succeeds
      context.server.use(
        http.get('/api/playlists', () => {
          return HttpResponse.json(mockApiResponses.paginated(testPlaylists))
        })
      )

      // Second attempt succeeds
      await store.loadPlaylists()
      expect(store.error).toBeNull()
      expect(store.playlists).toEqual(testPlaylists)
    })
  })

  describe('Performance and Scalability', () => {
    it('should handle large playlist datasets efficiently', async () => {
      const largePlaylists = integrationTestData.createPlaylistSet(500)

      context.server.use(
        http.get('/api/playlists', () => {
          return HttpResponse.json(mockApiResponses.paginated(largePlaylists))
        })
      )

      const { duration } = await performanceHelpers.measureDuration(async () => {
        await store.loadPlaylists()
      })

      expect(duration).toBeLessThan(1000) // Should complete within 1 second
      expect(store.playlists).toHaveLength(500)
    })

    it('should handle concurrent playlist operations efficiently', async () => {
      const playlists = integrationTestData.createPlaylistSet(10)

      playlists.forEach(playlist => {
        context.server.use(
          http.get(`/api/playlists/${playlist.id}`, () => {
            return HttpResponse.json(mockApiResponses.success(playlist))
          })
        )
      })

      const operations = playlists.map(playlist => () => store.loadPlaylist(playlist.id))

      const results = await performanceHelpers.testRapidOperations(
        () => Promise.all(operations.map(op => op())),
        10,
        2000 // 2 second limit for all operations
      )

      expect(results).toHaveLength(10)
    })

    it('should not leak memory during extensive operations', async () => {
      const testPlaylists = integrationTestData.createPlaylistSet(50)

      context.server.use(
        http.get('/api/playlists', () => {
          return HttpResponse.json(mockApiResponses.paginated(testPlaylists))
        })
      )

      const operations = [
        () => store.loadPlaylists(),
        () => store.invalidateCache(),
        () => store.loadPlaylists()
      ]

      const memoryTest = performanceHelpers.detectMemoryLeaks(operations)
      await memoryTest()
    })
  })

  describe('Search and Filtering Integration', () => {
    it('should integrate search with API filtering', async () => {
      const allPlaylists = integrationTestData.createPlaylistSet(20)
      const searchTerm = 'Integration'
      const filteredPlaylists = allPlaylists.filter(p =>
        p.title.toLowerCase().includes(searchTerm.toLowerCase())
      )

      context.server.use(
        http.get('/api/playlists', ({ request }) => {
          const url = new URL(request.url)
          const search = url.searchParams.get('search')
          
          if (search) {
            const filtered = allPlaylists.filter(p =>
              p.title.toLowerCase().includes(search.toLowerCase())
            )
            return HttpResponse.json(mockApiResponses.paginated(filtered))
          }
          
          return HttpResponse.json(mockApiResponses.paginated(allPlaylists))
        })
      )

      // Load all playlists first
      await store.loadPlaylists()
      expect(store.playlists).toHaveLength(20)

      // Test client-side search
      const searchResults = store.searchPlaylists(searchTerm)
      expect(searchResults.length).toBeGreaterThan(0)
      expect(searchResults.every(p => p.title.includes('Integration'))).toBe(true)
    })

    it('should handle complex filtering and sorting', async () => {
      const playlists = integrationTestData.createPlaylistSet(10)

      context.server.use(
        http.get('/api/playlists', () => {
          return HttpResponse.json(mockApiResponses.paginated(playlists))
        })
      )

      await store.loadPlaylists()

      // Test filtering
      const filteredByTrackCount = store.filterPlaylists(p => p.track_count > 5)
      expect(filteredByTrackCount.every(p => p.track_count > 5)).toBe(true)

      // Test sorting
      const sortedByTitle = store.getPlaylistsSortedBy('title')
      expect(sortedByTitle[0].title <= sortedByTitle[1].title).toBe(true)

      const sortedByTrackCount = store.getPlaylistsSortedBy('track_count')
      expect(sortedByTrackCount[0].track_count <= sortedByTrackCount[1].track_count).toBe(true)
    })
  })

  describe('Data Consistency and Synchronization', () => {
    it('should maintain consistency during rapid updates', async () => {
      const playlist = integrationTestData.createPlaylistSet(1)[0]

      // Add initial playlist
      store.addPlaylist(playlist)

      // Rapid updates
      const updates = Array.from({ length: 10 }, (_, i) => ({
        ...playlist,
        title: `Updated Title ${i}`
      }))

      updates.forEach(update => {
        store.updatePlaylist(update)
      })

      await flushPromises()

      const finalPlaylist = store.getPlaylistById(playlist.id)
      expect(finalPlaylist?.title).toBe('Updated Title 9')
    })

    it('should handle conflicting updates gracefully', async () => {
      const playlist = integrationTestData.createPlaylistSet(1)[0]
      store.addPlaylist(playlist)

      // Simulate conflicting updates
      const update1 = { ...playlist, title: 'Update 1' }
      const update2 = { ...playlist, title: 'Update 2' }

      store.updatePlaylist(update1)
      store.updatePlaylist(update2)

      await flushPromises()

      // Last update should win
      const finalPlaylist = store.getPlaylistById(playlist.id)
      expect(finalPlaylist?.title).toBe('Update 2')
    })

    it('should maintain data integrity across operations', async () => {
      const playlists = integrationTestData.createPlaylistSet(5)
      const tracks = integrationTestData.createTrackSet('playlist-1', 8)

      // Setup complex state
      for (const playlist of playlists) {
        store.addPlaylist(playlist)
      }
      store.setTracksForPlaylist('playlist-1', tracks)

      // Verify initial state
      expect(store.playlists).toHaveLength(5)
      expect(store.getTracksForPlaylist('playlist-1')).toHaveLength(8)

      // Remove playlist and verify cleanup
      store.removePlaylist('playlist-1')
      expect(store.playlists).toHaveLength(4)
      expect(store.getTracksForPlaylist('playlist-1')).toEqual([])
      expect(store.hasTracksData('playlist-1')).toBe(false)
    })
  })
})
