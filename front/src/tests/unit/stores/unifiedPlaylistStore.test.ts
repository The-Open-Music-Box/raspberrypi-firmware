/**
 * Unit tests for unifiedPlaylistStore.ts
 *
 * Tests the centralized playlist and track data management store including:
 * - Playlist data loading and management
 * - Track data management by playlist
 * - WebSocket integration
 * - API integration
 * - Performance optimizations
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUnifiedPlaylistStore } from '@/stores/unifiedPlaylistStore'

// Mock socketService
vi.mock('@/services/socketService', () => ({
  default: {
    on: vi.fn(),
    off: vi.fn(),
    emit: vi.fn(),
    isConnected: vi.fn(() => true),
    connect: vi.fn(),
    disconnect: vi.fn()
  }
}))

// Mock apiService
vi.mock('@/services/apiService', () => ({
  default: {
    getPlaylists: vi.fn(),
    getPlaylist: vi.fn(),
    getPlaylistTracks: vi.fn(),
    createPlaylist: vi.fn(),
    updatePlaylist: vi.fn(),
    deletePlaylist: vi.fn(),
    deleteTrack: vi.fn(),
    reorderTracks: vi.fn(),
    moveTrack: vi.fn(),
    moveTrackBetweenPlaylists: vi.fn()
  }
}))

// Mock logger
vi.mock('@/utils/logger', () => ({
  logger: {
    info: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
    warn: vi.fn()
  }
}))

// Mock constants
vi.mock('@/constants/apiRoutes', () => ({
  SOCKET_EVENTS: {
    PLAYLIST_UPDATED: 'playlist_updated',
    TRACK_UPDATED: 'track_updated'
  }
}))

// Mock track utils
vi.mock('@/utils/trackFieldAccessor', () => ({
  getTrackNumber: vi.fn((track) => track?.track_number || track?.number || 0),
  filterTrackByNumber: vi.fn((tracks, number) => tracks.find(t => (t.track_number || t.number) === number)),
  filterTracksByNumbers: vi.fn((tracks, numbers) => tracks.filter(t => numbers.includes(t.track_number || t.number))),
  validateTracksForDrag: vi.fn(() => ({ isValid: true })),
  createTrackIndexMap: vi.fn((tracks) => {
    // Create proper index map for O(1) lookups
    const map = new Map()
    tracks.forEach(track => {
      const trackNumber = track.track_number || track.number
      if (trackNumber) {
        map.set(trackNumber, track)
      }
    })
    return map
  }),
  findTrackByNumberSafe: vi.fn((tracks, number) => {
    const track = tracks.find(t => (t.track_number || t.number) === number)
    return { track: track || null, index: track ? tracks.indexOf(track) : -1 }
  })
}))

// Mock drag error handler
vi.mock('@/utils/dragOperationErrorHandler', () => ({
  handleDragError: vi.fn(),
  DragContext: class {}
}))

describe('unifiedPlaylistStore', () => {
  let store: ReturnType<typeof useUnifiedPlaylistStore>
  let pinia: ReturnType<typeof createPinia>
  let mockApiService: any

  beforeEach(async () => {
    pinia = createPinia()
    setActivePinia(pinia)

    // Get the mocked API service
    mockApiService = (await import('@/services/apiService')).default

    store = useUnifiedPlaylistStore()
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Store Initialization', () => {
    it('should initialize with default state', () => {
      expect(store.isLoading).toBe(false)
      expect(store.error).toBe(null)
      expect(store.lastSync).toBe(0)
      expect(store.isInitialized).toBe(false)
      expect(store.getAllPlaylists).toEqual([])
    })

    it('should have proper reactive state', () => {
      expect(typeof store.isLoading).toBe('boolean')
      expect(Array.isArray(store.getAllPlaylists)).toBe(true)
      expect(typeof store.getPlaylistById).toBe('function')
      expect(typeof store.getTracksForPlaylist).toBe('function')
    })
  })

  describe('Playlist Management', () => {
    it('should initialize the store', async () => {
      const mockPlaylists = [
        { id: 'pl1', title: 'Playlist 1', description: 'First playlist', track_count: 0 },
        { id: 'pl2', title: 'Playlist 2', description: 'Second playlist', track_count: 0 }
      ]

      mockApiService.getPlaylists.mockResolvedValue(mockPlaylists)

      await store.initialize()

      expect(mockApiService.getPlaylists).toHaveBeenCalled()
      expect(store.isInitialized).toBe(true)
      expect(store.getAllPlaylists).toHaveLength(2)
    })

    it('should load all playlists', async () => {
      const mockPlaylists = [
        { id: 'pl1', title: 'Playlist 1', description: 'First playlist', track_count: 0 },
        { id: 'pl2', title: 'Playlist 2', description: 'Second playlist', track_count: 0 }
      ]

      mockApiService.getPlaylists.mockResolvedValue(mockPlaylists)

      await store.loadAllPlaylists()

      expect(mockApiService.getPlaylists).toHaveBeenCalled()
      expect(store.getAllPlaylists).toHaveLength(2)
      expect(store.getPlaylistById('pl1')?.title).toBe('Playlist 1')
    })

    it('should handle playlist loading errors', async () => {
      const error = new Error('Failed to load playlists')
      mockApiService.getPlaylists.mockRejectedValue(error)

      // Store throws error after setting error state
      await expect(store.loadAllPlaylists()).rejects.toThrow()

      expect(store.error).toBe('Failed to load playlists')
      expect(store.isLoading).toBe(false)
    })

    it('should get playlist by ID', async () => {
      const mockPlaylists = [
        { id: 'pl1', title: 'Playlist 1', description: 'First playlist', track_count: 0 }
      ]

      mockApiService.getPlaylists.mockResolvedValue(mockPlaylists)
      await store.loadAllPlaylists()

      const playlist = store.getPlaylistById('pl1')
      expect(playlist?.title).toBe('Playlist 1')

      const nonExistent = store.getPlaylistById('nonexistent')
      expect(nonExistent).toBeUndefined()
    })

    it('should create new playlist', async () => {
      const newPlaylist = { id: 'new', title: 'New Playlist', description: 'Test playlist', track_count: 0 }
      mockApiService.createPlaylist.mockResolvedValue(newPlaylist)

      await store.createPlaylist('New Playlist', 'Test playlist')

      expect(mockApiService.createPlaylist).toHaveBeenCalledWith('New Playlist', 'Test playlist')
    })

    it('should update existing playlist', async () => {
      // First add a playlist
      const mockPlaylists = [
        { id: 'pl1', title: 'Playlist 1', description: 'First playlist', track_count: 0 }
      ]
      mockApiService.getPlaylists.mockResolvedValue(mockPlaylists)
      await store.loadAllPlaylists()

      const updatedPlaylist = { id: 'pl1', title: 'Updated Title', description: 'Updated description', track_count: 0 }
      mockApiService.updatePlaylist.mockResolvedValue(updatedPlaylist)

      await store.updatePlaylist('pl1', { title: 'Updated Title', description: 'Updated description' })

      expect(mockApiService.updatePlaylist).toHaveBeenCalledWith('pl1', expect.any(Object))
    })

    it('should delete playlist', async () => {
      // First add a playlist
      const mockPlaylists = [
        { id: 'pl1', title: 'Playlist 1', description: 'First playlist', track_count: 0 }
      ]
      mockApiService.getPlaylists.mockResolvedValue(mockPlaylists)
      await store.loadAllPlaylists()

      mockApiService.deletePlaylist.mockResolvedValue({ success: true })

      await store.deletePlaylist('pl1')

      expect(mockApiService.deletePlaylist).toHaveBeenCalledWith('pl1')
    })
  })

  describe('Track Management', () => {
    beforeEach(async () => {
      // Setup a playlist first
      const mockPlaylists = [
        { id: 'pl1', title: 'Playlist 1', description: 'First playlist', track_count: 2 }
      ]
      mockApiService.getPlaylists.mockResolvedValue(mockPlaylists)
      await store.loadAllPlaylists()
    })

    it('should load tracks for playlist', async () => {
      const mockPlaylistWithTracks = {
        id: 'pl1',
        title: 'Playlist 1',
        description: 'First playlist',
        track_count: 2,
        tracks: [
          { id: 't1', track_number: 1, title: 'Track 1', filename: 'track1.mp3' },
          { id: 't2', track_number: 2, title: 'Track 2', filename: 'track2.mp3' }
        ]
      }

      mockApiService.getPlaylist.mockResolvedValue(mockPlaylistWithTracks)

      await store.loadPlaylistTracks('pl1')

      expect(mockApiService.getPlaylist).toHaveBeenCalledWith('pl1')
      expect(store.getTracksForPlaylist('pl1')).toHaveLength(2)
    })

    it('should handle track loading errors', async () => {
      const error = new Error('Failed to load tracks')
      mockApiService.getPlaylist.mockRejectedValue(error)

      // Store throws error without setting error state for track loading
      await expect(store.loadPlaylistTracks('pl1')).rejects.toThrow()
    })

    it('should get tracks for playlist', async () => {
      const mockPlaylist = {
        id: 'pl1',
        title: 'Playlist 1',
        tracks: [
          { id: 't1', track_number: 1, title: 'Track 1', filename: 'track1.mp3' }
        ]
      }

      mockApiService.getPlaylist.mockResolvedValue(mockPlaylist)
      await store.loadPlaylistTracks('pl1')

      const tracks = store.getTracksForPlaylist('pl1')
      expect(tracks).toHaveLength(1)
      expect(tracks[0].title).toBe('Track 1')
    })

    it('should get track by number', async () => {
      const mockPlaylist = {
        id: 'pl1',
        title: 'Playlist 1',
        tracks: [
          { id: 't1', track_number: 1, title: 'Track 1', filename: 'track1.mp3' },
          { id: 't2', track_number: 2, title: 'Track 2', filename: 'track2.mp3' }
        ]
      }

      mockApiService.getPlaylist.mockResolvedValue(mockPlaylist)
      await store.loadPlaylistTracks('pl1')

      const track = store.getTrackByNumber('pl1', 2)
      expect(track?.title).toBe('Track 2')

      const nonExistent = store.getTrackByNumber('pl1', 99)
      expect(nonExistent).toBeUndefined()
    })

    it('should delete track', async () => {
      mockApiService.deleteTrack.mockResolvedValue({ success: true })

      await store.deleteTrack('pl1', [1, 2])

      expect(mockApiService.deleteTrack).toHaveBeenCalledWith('pl1', [1, 2])
    })

    it('should reorder tracks', async () => {
      // First load some tracks so reorderTracks has data to work with
      const mockPlaylist = {
        id: 'pl1',
        title: 'Playlist 1',
        tracks: [
          { id: 't1', track_number: 1, title: 'Track 1', filename: 'track1.mp3' },
          { id: 't2', track_number: 2, title: 'Track 2', filename: 'track2.mp3' }
        ]
      }
      mockApiService.getPlaylist.mockResolvedValue(mockPlaylist)
      await store.loadPlaylistTracks('pl1')

      mockApiService.reorderTracks.mockResolvedValue({ success: true })

      // Store expects newOrder as an array of track numbers
      await store.reorderTracks('pl1', [2, 1])

      // API is called with track IDs, not numbers
      expect(mockApiService.reorderTracks).toHaveBeenCalledWith('pl1', ['t2', 't1'])
    })

    it('should correctly reorder tracks with proper state updates', async () => {
      // Regression test for off-by-one bug where duplicate optimistic updates
      // caused track mapping to fail
      const mockPlaylist = {
        id: 'pl1',
        title: 'Playlist 1',
        tracks: [
          { id: 't1', track_number: 1, title: 'Track 1', filename: 'track1.mp3' },
          { id: 't2', track_number: 2, title: 'Track 2', filename: 'track2.mp3' },
          { id: 't3', track_number: 3, title: 'Track 3', filename: 'track3.mp3' },
          { id: 't4', track_number: 4, title: 'Track 4', filename: 'track4.mp3' },
          { id: 't5', track_number: 5, title: 'Track 5', filename: 'track5.mp3' }
        ]
      }
      mockApiService.getPlaylist.mockResolvedValue(mockPlaylist)
      await store.loadPlaylistTracks('pl1')

      mockApiService.reorderTracks.mockResolvedValue({ success: true })

      // Simulate dragging track 5 to position 1 (0-indexed position 0)
      // Visual order after drag: [track5, track1, track2, track3, track4]
      // Track numbers from visual order: [5, 1, 2, 3, 4]
      await store.reorderTracks('pl1', [5, 1, 2, 3, 4])

      // Verify API was called with correct track IDs in correct order
      expect(mockApiService.reorderTracks).toHaveBeenCalledWith('pl1', ['t5', 't1', 't2', 't3', 't4'])

      // Verify optimistic update applied correct track_numbers
      const updatedTracks = store.getTracksForPlaylist('pl1')
      expect(updatedTracks).toHaveLength(5)

      // Track 5 should now be first with track_number = 1
      expect(updatedTracks[0].id).toBe('t5')
      expect(updatedTracks[0].track_number).toBe(1)
      expect(updatedTracks[0].title).toBe('Track 5')

      // Track 1 should now be second with track_number = 2
      expect(updatedTracks[1].id).toBe('t1')
      expect(updatedTracks[1].track_number).toBe(2)
      expect(updatedTracks[1].title).toBe('Track 1')

      // Verify all tracks are in correct order
      expect(updatedTracks[2].id).toBe('t2')
      expect(updatedTracks[2].track_number).toBe(3)
      expect(updatedTracks[3].id).toBe('t3')
      expect(updatedTracks[3].track_number).toBe(4)
      expect(updatedTracks[4].id).toBe('t4')
      expect(updatedTracks[4].track_number).toBe(5)
    })

    it('should move track between playlists', async () => {
      mockApiService.moveTrackBetweenPlaylists.mockResolvedValue({ success: true })

      await store.moveTrackBetweenPlaylists('pl1', 'pl2', 1, 2)

      expect(mockApiService.moveTrackBetweenPlaylists).toHaveBeenCalledWith('pl1', 'pl2', 1, 2)
    })

    it('should clear tracks for playlist', () => {
      // Set some tracks first using optimistic updates
      store.setTracksOptimistic('pl1', [
        { id: 't1', track_number: 1, title: 'Track 1', filename: 'track1.mp3' }
      ])

      expect(store.getTracksForPlaylist('pl1')).toHaveLength(1)

      store.clearPlaylistTracks('pl1')

      expect(store.getTracksForPlaylist('pl1')).toHaveLength(0)
    })
  })

  describe('Getters and Computed Properties', () => {
    beforeEach(async () => {
      const mockPlaylists = [
        { id: 'pl1', title: 'Playlist 1', description: 'First playlist', track_count: 1 },
        { id: 'pl2', title: 'Playlist 2', description: 'Second playlist', track_count: 0 }
      ]
      mockApiService.getPlaylists.mockResolvedValue(mockPlaylists)
      await store.loadAllPlaylists()

      const mockPlaylist = {
        id: 'pl1',
        title: 'Playlist 1',
        tracks: [
          { id: 't1', track_number: 1, title: 'Track 1', filename: 'track1.mp3' }
        ]
      }
      mockApiService.getPlaylist.mockResolvedValue(mockPlaylist)
      await store.loadPlaylistTracks('pl1')
    })

    it('should get all playlists', () => {
      const playlists = store.getAllPlaylists
      expect(playlists).toHaveLength(2)
      expect(playlists[0].title).toBe('Playlist 1')
    })

    it('should get playlist with tracks', () => {
      const playlistWithTracks = store.getPlaylistWithTracks('pl1')
      expect(playlistWithTracks?.title).toBe('Playlist 1')
      expect(playlistWithTracks?.tracks).toHaveLength(1)
    })

    it('should check if has playlist data', () => {
      expect(store.hasPlaylistData('pl1')).toBe(true)
      expect(store.hasPlaylistData('nonexistent')).toBe(false)
    })

    it('should check if has tracks data', () => {
      expect(store.hasTracksData('pl1')).toBe(true)
      expect(store.hasTracksData('pl2')).toBe(false)
    })

    it('should use optimized track lookup', async () => {
      const track = store.getTrackByNumberOptimized('pl1', 1)
      expect(track?.title).toBe('Track 1')

      const nonExistent = store.getTrackByNumberOptimized('pl1', 99)
      expect(nonExistent).toBe(null)
    })
  })

  describe('State Management', () => {
    it('should track loading state', async () => {
      expect(store.isLoading).toBe(false)

      const promise = store.loadAllPlaylists()
      expect(store.isLoading).toBe(true)

      await promise
      expect(store.isLoading).toBe(false)
    })

    it('should handle and clear errors', async () => {
      const error = new Error('Test error')
      mockApiService.getPlaylists.mockRejectedValue(error)

      // First call throws error
      await expect(store.loadAllPlaylists()).rejects.toThrow()
      expect(store.error).toBe('Failed to load playlists')

      // Error should be cleared on successful operation
      mockApiService.getPlaylists.mockResolvedValue([])
      await store.loadAllPlaylists()
      expect(store.error).toBe(null)
    })

    it('should track last sync time', async () => {
      const beforeSync = Date.now()
      mockApiService.getPlaylists.mockResolvedValue([])

      await store.loadAllPlaylists()

      expect(store.lastSync).toBeGreaterThanOrEqual(beforeSync)
      expect(store.lastSync).toBeLessThanOrEqual(Date.now())
    })

    it('should force sync when requested', async () => {
      mockApiService.getPlaylists.mockResolvedValue([])
      await store.loadAllPlaylists()

      const firstSync = store.lastSync

      // Add small delay to ensure different timestamp
      await new Promise(resolve => setTimeout(resolve, 10))

      // Force sync should reload even if recently synced
      await store.forceSync()

      expect(store.lastSync).toBeGreaterThanOrEqual(firstSync)
    })
  })

  describe('Performance Optimizations', () => {
    it('should provide optimized track lookups', async () => {
      const mockTracks = Array.from({ length: 100 }, (_, i) => ({
        id: `t${i}`,
        track_number: i + 1,
        title: `Track ${i + 1}`,
        filename: `track${i + 1}.mp3`
      }))

      const mockPlaylist = {
        id: 'pl1',
        title: 'Playlist 1',
        tracks: mockTracks
      }

      mockApiService.getPlaylist.mockResolvedValue(mockPlaylist)
      await store.loadPlaylistTracks('pl1')

      const startTime = performance.now()
      const track = store.getTrackByNumberOptimized('pl1', 50)
      const endTime = performance.now()

      expect(track?.title).toBe('Track 50')
      expect(endTime - startTime).toBeLessThan(1) // Should be very fast O(1) lookup
    })

    it('should handle optimistic updates', () => {
      const tracks = [
        { id: 't1', track_number: 1, title: 'Track 1', filename: 'track1.mp3' }
      ]

      store.setTracksOptimistic('pl1', tracks)

      expect(store.getTracksForPlaylist('pl1')).toHaveLength(1)
      expect(store.getTrackByNumber('pl1', 1)?.title).toBe('Track 1')
    })
  })

  describe('Cleanup', () => {
    it('should cleanup WebSocket listeners', async () => {
      // cleanup() only removes WebSocket listeners, it doesn't clear state
      // This is intentional - state persists for potential reuse

      const socketService = (await import('@/services/socketService')).default

      store.cleanup()

      // Verify WebSocket listeners are removed
      expect(socketService.off).toHaveBeenCalled()
    })
  })
})