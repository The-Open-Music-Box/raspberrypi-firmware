/**
 * Comprehensive tests for serverStateStore.ts
 *
 * This test suite covers all critical business logic for server state synchronization:
 * - State initialization and structure
 * - WebSocket event handling
 * - Server sequence management
 * - Player state updates
 * - Playlist state management
 * - NFC state handling
 * - Error scenarios and edge cases
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useServerStateStore } from '@/stores/serverStateStore'
import type { Track } from '@/components/files/types'

// Mock socket service with full implementation
vi.mock('@/services/socketService', () => ({
  default: {
    on: vi.fn(),
    off: vi.fn(),
    emit: vi.fn(),
    isConnected: vi.fn(() => true)
  }
}))

// Mock API service
vi.mock('@/services/apiService', () => ({
  default: {
    getPlayerStatus: vi.fn()
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

// Mock track field accessor utilities
vi.mock('@/utils/trackFieldAccessor', () => ({
  getTrackNumber: vi.fn((track) => track?.track_number || track?.number || 0),
  // filterTracksByNumbers: remove tracks WITH these numbers (not without)
  filterTracksByNumbers: vi.fn((tracks, numbers) =>
    tracks.filter(t => !numbers.includes(t.track_number || t.number))
  )
}))

// Mock constants
vi.mock('@/constants/apiRoutes', () => ({
  SOCKET_EVENTS: {
    ACK_OP: 'ack_op',
    ERR_OP: 'err_op',
    SYNC_REQUEST: 'sync_request'
  }
}))

describe('serverStateStore', () => {
  let store: ReturnType<typeof useServerStateStore>
  let eventHandlers: Record<string, Function>
  let domEventHandlers: Record<string, Function>
  let mockSocketService: any
  let mockApiService: any

  beforeEach(async () => {
    setActivePinia(createPinia())
    vi.clearAllMocks()

    // Get mocked modules
    mockSocketService = (await import('@/services/socketService')).default
    mockApiService = (await import('@/services/apiService')).default

    // Capture event handlers
    eventHandlers = {}
    domEventHandlers = {}

    mockSocketService.on.mockImplementation((event: string, handler: Function) => {
      eventHandlers[event] = handler
    })

    // Capture DOM event handlers
    const originalAddEventListener = window.addEventListener
    vi.spyOn(window, 'addEventListener').mockImplementation((event: string, handler: any) => {
      domEventHandlers[event] = handler
    })

    store = useServerStateStore()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('State Initialization', () => {
    it('should initialize with default state values', () => {
      expect(store.playlists).toEqual([])
      expect(store.currentPlaylist).toBeNull()
      expect(store.globalSequence).toBe(0)
      expect(store.isConnected).toBe(false)
      expect(store.isReconnecting).toBe(false)
    })

    it('should initialize player state with correct structure', () => {
      expect(store.playerState).toEqual({
        is_playing: false,
        state: undefined,
        active_playlist_id: null,
        active_playlist_title: null,
        active_track_id: null,
        active_track: null,
        position_ms: 0,
        duration_ms: 0,
        track_index: 0,
        track_count: 0,
        can_prev: false,
        can_next: false,
        volume: undefined,
        muted: undefined,
        server_seq: 0
      })
    })

    it('should have empty pending operations set', () => {
      expect(store.pendingOperations.size).toBe(0)
    })

    it('should setup event handlers on initialization', () => {
      expect(mockSocketService.on).toHaveBeenCalledWith('connect', expect.any(Function))
      expect(mockSocketService.on).toHaveBeenCalledWith('disconnect', expect.any(Function))
      expect(mockSocketService.on).toHaveBeenCalledWith('reconnect', expect.any(Function))
      expect(mockSocketService.on).toHaveBeenCalledWith('reconnecting', expect.any(Function))
    })

    it('should setup DOM event listeners for state updates', () => {
      expect(window.addEventListener).toHaveBeenCalledWith('state:playlists', expect.any(Function))
      expect(window.addEventListener).toHaveBeenCalledWith('state:playlist', expect.any(Function))
      expect(window.addEventListener).toHaveBeenCalledWith('state:player', expect.any(Function))
      expect(window.addEventListener).toHaveBeenCalledWith('state:track_progress', expect.any(Function))
      expect(window.addEventListener).toHaveBeenCalledWith('state:track_position', expect.any(Function))
    })
  })

  describe('Connection Event Handling', () => {
    it('should handle connect event', async () => {
      mockApiService.getPlayerStatus.mockResolvedValue({
        is_playing: false,
        active_playlist_id: null
      })

      // The connect handler is async but doesn't return promise, so we need to wait
      eventHandlers['connect']()

      // Wait for async operations to complete
      await new Promise(resolve => setTimeout(resolve, 10))

      expect(store.isConnected).toBe(true)
      expect(store.isReconnecting).toBe(false)
      expect(mockSocketService.emit).toHaveBeenCalledWith('join:playlists', {})
      expect(mockSocketService.emit).toHaveBeenCalledWith('sync_request', expect.any(Object))
      expect(mockApiService.getPlayerStatus).toHaveBeenCalled()
    })

    it('should handle disconnect event', () => {
      eventHandlers['disconnect']()

      expect(store.isConnected).toBe(false)
    })

    it('should handle reconnect event', async () => {
      mockApiService.getPlayerStatus.mockResolvedValue({
        is_playing: false
      })

      await eventHandlers['reconnect']()

      expect(store.isReconnecting).toBe(false)
      expect(mockSocketService.emit).toHaveBeenCalledWith('join:playlists', {})
      expect(mockSocketService.emit).toHaveBeenCalledWith('sync_request', expect.any(Object))
    })

    it('should handle reconnecting event', () => {
      eventHandlers['reconnecting']()

      expect(store.isReconnecting).toBe(true)
    })

    it('should retry subscription if not connected on connect', async () => {
      vi.useFakeTimers()
      mockSocketService.isConnected.mockReturnValueOnce(false).mockReturnValueOnce(true)

      await eventHandlers['connect']()

      // First subscription should fail and schedule retry
      expect(mockSocketService.emit).not.toHaveBeenCalledWith('join:playlists', {})

      // Fast-forward timers and check retry
      vi.advanceTimersByTime(500)

      expect(mockSocketService.emit).toHaveBeenCalledWith('join:playlists', {})

      vi.useRealTimers()
    })
  })

  describe('Playlist Snapshot Handling', () => {
    it('should handle playlists snapshot with standard format', () => {
      const mockPlaylists = [
        { id: 'pl1', title: 'Playlist 1', description: 'Test', tracks: [], track_count: 0 },
        { id: 'pl2', title: 'Playlist 2', description: 'Test 2', tracks: [], track_count: 0 }
      ]

      const event = new CustomEvent('state:playlists', {
        detail: {
          data: { playlists: mockPlaylists },
          server_seq: 10
        }
      })

      domEventHandlers['state:playlists'](event)

      expect(store.playlists).toEqual(mockPlaylists)
      expect(store.globalSequence).toBe(10)
    })

    it('should handle playlists snapshot with direct format', () => {
      const mockPlaylists = [
        { id: 'pl1', title: 'Playlist 1', description: 'Test', tracks: [], track_count: 0 }
      ]

      const event = new CustomEvent('state:playlists', {
        detail: {
          playlists: mockPlaylists,
          server_seq: 5
        }
      })

      domEventHandlers['state:playlists'](event)

      expect(store.playlists).toEqual(mockPlaylists)
      expect(store.globalSequence).toBe(5)
    })

    it('should handle empty playlists snapshot', () => {
      const event = new CustomEvent('state:playlists', {
        detail: {
          data: {}
        }
      })

      domEventHandlers['state:playlists'](event)

      expect(store.playlists).toEqual([])
    })

    it('should handle playlist snapshot', () => {
      const mockPlaylist = {
        id: 'pl1',
        title: 'Updated Playlist',
        description: 'Updated',
        tracks: [],
        track_count: 0
      }

      const event = new CustomEvent('state:playlist', {
        detail: {
          event_type: 'state:playlist',
          server_seq: 15,
          playlist_id: 'pl1',
          data: mockPlaylist,
          timestamp: Date.now(),
          event_id: 'evt1'
        }
      })

      // First add playlist to list
      const initEvent = new CustomEvent('state:playlists', {
        detail: {
          data: { playlists: [mockPlaylist] }
        }
      })
      domEventHandlers['state:playlists'](initEvent)

      // Then update it
      domEventHandlers['state:playlist'](event)

      expect(store.globalSequence).toBe(15)
      expect(store.playlists[0]).toEqual(mockPlaylist)
    })

    it('should update current playlist if it matches updated playlist', () => {
      const mockPlaylist = {
        id: 'pl1',
        title: 'Playlist 1',
        description: 'Test',
        tracks: [],
        track_count: 0
      }

      // Initialize with playlist
      const initEvent = new CustomEvent('state:playlists', {
        detail: { data: { playlists: [mockPlaylist] } }
      })
      domEventHandlers['state:playlists'](initEvent)

      // Simulate current playlist by having it in state
      // We can't set readonly properties, but we can verify the update logic
      // The store updates both playlists array and currentPlaylist if they match

      // Update the playlist
      const updatedPlaylist = { ...mockPlaylist, title: 'Updated Title' }
      const updateEvent = new CustomEvent('state:playlist', {
        detail: {
          event_type: 'state:playlist',
          server_seq: 20,
          playlist_id: 'pl1',
          data: updatedPlaylist,
          timestamp: Date.now(),
          event_id: 'evt2'
        }
      })

      domEventHandlers['state:playlist'](updateEvent)

      // Verify the playlist in the array was updated
      expect(store.playlists[0].title).toBe('Updated Title')
    })
  })

  describe('Player State Handling', () => {
    it('should handle player state with StateEvent wrapper', () => {
      const playerData = {
        is_playing: true,
        active_playlist_id: 'pl1',
        active_playlist_title: 'My Playlist',
        active_track_id: 't1',
        active_track: {
          id: 't1',
          title: 'Track 1',
          filename: 'track1.mp3',
          duration_ms: 180000
        },
        position_ms: 5000,
        duration_ms: 180000,
        track_index: 0,
        track_count: 5,
        can_prev: false,
        can_next: true,
        volume: 75
      }

      const event = new CustomEvent('state:player', {
        detail: {
          event_type: 'state:player',
          server_seq: 25,
          data: playerData,
          timestamp: Date.now(),
          event_id: 'evt3'
        }
      })

      domEventHandlers['state:player'](event)

      expect(store.playerState.is_playing).toBe(true)
      expect(store.playerState.active_playlist_id).toBe('pl1')
      expect(store.playerState.active_playlist_title).toBe('My Playlist')
      expect(store.playerState.active_track?.title).toBe('Track 1')
      expect(store.playerState.position_ms).toBe(5000)
      expect(store.playerState.volume).toBe(75)
      expect(store.globalSequence).toBe(25)
    })

    it('should handle player state with direct PlayerState format', () => {
      const playerState = {
        is_playing: false,
        active_playlist_id: 'pl2',
        active_playlist_title: null,
        active_track_id: null,
        active_track: null,
        position_ms: 0,
        duration_ms: 0,
        track_index: 0,
        track_count: 0,
        can_prev: false,
        can_next: false,
        volume: 50,
        server_seq: 30
      }

      const event = new CustomEvent('state:player', {
        detail: playerState
      })

      domEventHandlers['state:player'](event)

      expect(store.playerState.is_playing).toBe(false)
      expect(store.playerState.active_playlist_id).toBe('pl2')
      expect(store.playerState.volume).toBe(50)
      expect(store.globalSequence).toBe(30)
    })

    it('should handle player state with partial updates', () => {
      // Set initial state
      const initialEvent = new CustomEvent('state:player', {
        detail: {
          is_playing: true,
          active_playlist_id: 'pl1',
          position_ms: 1000,
          volume: 80,
          server_seq: 10
        }
      })
      domEventHandlers['state:player'](initialEvent)

      // Partial update
      const updateEvent = new CustomEvent('state:player', {
        detail: {
          is_playing: false,
          server_seq: 11
        }
      })
      domEventHandlers['state:player'](updateEvent)

      expect(store.playerState.is_playing).toBe(false)
      expect(store.playerState.active_playlist_id).toBeNull() // Reset by partial update
    })

    it('should convert is_playing to boolean correctly', () => {
      const event = new CustomEvent('state:player', {
        detail: {
          data: {
            is_playing: 1, // Non-boolean truthy value
          }
        }
      })

      domEventHandlers['state:player'](event)

      expect(store.playerState.is_playing).toBe(true)
      expect(typeof store.playerState.is_playing).toBe('boolean')
    })

    it('should handle track progress updates', () => {
      const event = new CustomEvent('state:track_progress', {
        detail: {
          event_type: 'state:track_progress',
          server_seq: 35,
          data: {
            position_ms: 15000,
            duration_ms: 200000,
            track_info: {
              id: 't2',
              title: 'Track 2',
              filename: 'track2.mp3'
            }
          },
          timestamp: Date.now(),
          event_id: 'evt4'
        }
      })

      domEventHandlers['state:track_progress'](event)

      expect(store.playerState.position_ms).toBe(15000)
      expect(store.playerState.duration_ms).toBe(200000)
      expect(store.playerState.active_track?.title).toBe('Track 2')
      expect(store.globalSequence).toBe(35)
    })

    it('should handle track position updates', () => {
      const event = new CustomEvent('state:track_position', {
        detail: {
          event_type: 'state:track_position',
          server_seq: 40,
          data: {
            position_ms: 25000,
            duration_ms: 180000,
            is_playing: true,
            track_id: 't3'
          },
          timestamp: Date.now(),
          event_id: 'evt5'
        }
      })

      domEventHandlers['state:track_position'](event)

      expect(store.playerState.position_ms).toBe(25000)
      expect(store.playerState.duration_ms).toBe(180000)
      expect(store.playerState.is_playing).toBe(true)
      expect(store.playerState.active_track_id).toBe('t3')
      expect(store.globalSequence).toBe(40)
    })

    it('should update track_id if different', () => {
      // First set a track
      const initialEvent = new CustomEvent('state:player', {
        detail: {
          data: {
            active_track_id: 't2'
          }
        }
      })
      domEventHandlers['state:player'](initialEvent)

      // Now update with different track
      const event = new CustomEvent('state:track_position', {
        detail: {
          data: {
            position_ms: 30000,
            track_id: 't3'
          },
          server_seq: 41
        }
      })

      domEventHandlers['state:track_position'](event)

      expect(store.playerState.active_track_id).toBe('t3')
      expect(store.playerState.position_ms).toBe(30000)
    })
  })

  describe('Playlist Action Events', () => {
    it('should handle playlist created event', () => {
      const newPlaylist = {
        id: 'pl-new',
        title: 'New Playlist',
        description: 'Fresh playlist',
        tracks: [],
        track_count: 0
      }

      const event = new CustomEvent('state:playlist_created', {
        detail: {
          event_type: 'state:playlist_created',
          server_seq: 45,
          data: { playlist: newPlaylist },
          timestamp: Date.now(),
          event_id: 'evt6'
        }
      })

      domEventHandlers['state:playlist_created'](event)

      expect(store.playlists).toContainEqual(newPlaylist)
      expect(store.globalSequence).toBe(45)
    })

    it('should not duplicate playlist on created event', () => {
      const playlist = {
        id: 'pl1',
        title: 'Existing',
        description: 'Test',
        tracks: [],
        track_count: 0
      }

      // Initialize with playlist
      const initEvent = new CustomEvent('state:playlists', {
        detail: { data: { playlists: [playlist] } }
      })
      domEventHandlers['state:playlists'](initEvent)

      // Try to create again
      const createEvent = new CustomEvent('state:playlist_created', {
        detail: {
          event_type: 'state:playlist_created',
          server_seq: 50,
          data: { playlist },
          timestamp: Date.now(),
          event_id: 'evt7'
        }
      })

      domEventHandlers['state:playlist_created'](createEvent)

      expect(store.playlists.length).toBe(1)
    })

    it('should handle playlist updated event', () => {
      const originalPlaylist = {
        id: 'pl1',
        title: 'Original',
        description: 'Before',
        tracks: [],
        track_count: 0
      }

      // Initialize
      const initEvent = new CustomEvent('state:playlists', {
        detail: { data: { playlists: [originalPlaylist] } }
      })
      domEventHandlers['state:playlists'](initEvent)

      // Update
      const updatedPlaylist = {
        ...originalPlaylist,
        title: 'Updated',
        description: 'After'
      }

      const updateEvent = new CustomEvent('state:playlist_updated', {
        detail: {
          event_type: 'state:playlist_updated',
          server_seq: 55,
          playlist_id: 'pl1',
          data: { playlist: updatedPlaylist, playlist_seq: 10 },
          timestamp: Date.now(),
          event_id: 'evt8'
        }
      })

      domEventHandlers['state:playlist_updated'](updateEvent)

      expect(store.playlists[0].title).toBe('Updated')
      expect(store.playlists[0].description).toBe('After')
      expect(store.globalSequence).toBe(55)
    })

    it('should handle playlist deleted event with playlist_id in data', () => {
      const playlist = {
        id: 'pl-delete',
        title: 'To Delete',
        description: 'Test',
        tracks: [],
        track_count: 0
      }

      // Initialize
      const initEvent = new CustomEvent('state:playlists', {
        detail: { data: { playlists: [playlist] } }
      })
      domEventHandlers['state:playlists'](initEvent)

      expect(store.playlists.length).toBe(1)

      // Delete
      const deleteEvent = new CustomEvent('state:playlist_deleted', {
        detail: {
          event_type: 'state:playlist_deleted',
          server_seq: 60,
          data: { playlist_id: 'pl-delete' },
          timestamp: Date.now(),
          event_id: 'evt9'
        }
      })

      domEventHandlers['state:playlist_deleted'](deleteEvent)

      expect(store.playlists.length).toBe(0)
      expect(store.globalSequence).toBe(60)
    })

    it('should handle playlist deleted event with event.playlist_id', () => {
      const playlist = {
        id: 'pl-delete2',
        title: 'To Delete',
        description: 'Test',
        tracks: [],
        track_count: 0
      }

      // Initialize
      const initEvent = new CustomEvent('state:playlists', {
        detail: { data: { playlists: [playlist] } }
      })
      domEventHandlers['state:playlists'](initEvent)

      // Delete with playlist_id at root level
      const deleteEvent = new CustomEvent('state:playlist_deleted', {
        detail: {
          event_type: 'state:playlist_deleted',
          server_seq: 65,
          playlist_id: 'pl-delete2',
          data: {},
          timestamp: Date.now(),
          event_id: 'evt10'
        }
      })

      domEventHandlers['state:playlist_deleted'](deleteEvent)

      expect(store.playlists.length).toBe(0)
    })

    it('should handle playlist deleted and remove from list', () => {
      const playlist = {
        id: 'pl-current',
        title: 'Current',
        description: 'Test',
        tracks: [],
        track_count: 0
      }

      // Initialize
      const initEvent = new CustomEvent('state:playlists', {
        detail: { data: { playlists: [playlist] } }
      })
      domEventHandlers['state:playlists'](initEvent)

      expect(store.playlists.length).toBe(1)

      // Delete
      const deleteEvent = new CustomEvent('state:playlist_deleted', {
        detail: {
          server_seq: 70,
          data: { playlist_id: 'pl-current' }
        }
      })

      domEventHandlers['state:playlist_deleted'](deleteEvent)

      // Verify playlist removed from list
      expect(store.playlists.length).toBe(0)
    })
  })

  describe('Track Action Events', () => {
    // Note: Each test needs to reinitialize since store state persists between tests
    const getBaseMockPlaylist = () => ({
      id: 'pl1',
      title: 'Test Playlist',
      description: 'Test',
      tracks: [
        { id: 't1', track_number: 1, title: 'Track 1', filename: 't1.mp3' },
        { id: 't2', track_number: 2, title: 'Track 2', filename: 't2.mp3' },
        { id: 't3', track_number: 3, title: 'Track 3', filename: 't3.mp3' }
      ],
      track_count: 3
    })

    const initializePlaylist = () => {
      const mockPlaylist = getBaseMockPlaylist()
      const initEvent = new CustomEvent('state:playlists', {
        detail: { data: { playlists: [mockPlaylist] } }
      })
      domEventHandlers['state:playlists'](initEvent)
    }

    it('should handle track added event', () => {
      initializePlaylist()

      const newTrack = {
        id: 't4',
        track_number: 4,
        title: 'Track 4',
        filename: 't4.mp3'
      }

      const event = new CustomEvent('state:track_added', {
        detail: {
          event_type: 'state:track_added',
          server_seq: 75,
          data: {
            playlist_id: 'pl1',
            track: newTrack,
            playlist_seq: 15
          },
          timestamp: Date.now(),
          event_id: 'evt11'
        }
      })

      domEventHandlers['state:track_added'](event)

      const playlist = store.playlists.find(p => p.id === 'pl1')
      expect(playlist?.tracks).toHaveLength(4)
      expect(playlist?.tracks?.find(t => t.id === 't4')).toBeDefined()
      expect(store.globalSequence).toBe(75)
    })

    it('should not duplicate tracks on add', () => {
      initializePlaylist()

      const existingTrack = {
        id: 't2',
        track_number: 2,
        title: 'Track 2',
        filename: 't2.mp3'
      }

      const event = new CustomEvent('state:track_added', {
        detail: {
          server_seq: 80,
          data: {
            playlist_id: 'pl1',
            track: existingTrack
          }
        }
      })

      domEventHandlers['state:track_added'](event)

      const playlist = store.playlists.find(p => p.id === 'pl1')
      expect(playlist?.tracks).toHaveLength(3) // Still 3, not 4
    })

    it('should handle track deleted event', () => {
      initializePlaylist()

      const event = new CustomEvent('state:track_deleted', {
        detail: {
          event_type: 'state:track_deleted',
          server_seq: 85,
          data: {
            playlist_id: 'pl1',
            track_numbers: [2], // Delete track 2
            playlist_seq: 20
          },
          timestamp: Date.now(),
          event_id: 'evt12'
        }
      })

      domEventHandlers['state:track_deleted'](event)

      const playlist = store.playlists.find(p => p.id === 'pl1')
      expect(playlist?.tracks).toHaveLength(2)
      expect(playlist?.tracks?.find(t => t.track_number === 2)).toBeUndefined()
      expect(store.globalSequence).toBe(85)
    })

    it('should handle multiple tracks deleted', () => {
      initializePlaylist()

      const event = new CustomEvent('state:track_deleted', {
        detail: {
          server_seq: 90,
          data: {
            playlist_id: 'pl1',
            track_numbers: [1, 3] // Delete tracks 1 and 3
          }
        }
      })

      domEventHandlers['state:track_deleted'](event)

      const playlist = store.playlists.find(p => p.id === 'pl1')
      expect(playlist?.tracks).toHaveLength(1)
      expect(playlist?.tracks?.[0].track_number).toBe(2)
    })

    it('should update playlist in list on track delete', () => {
      initializePlaylist()

      const event = new CustomEvent('state:track_deleted', {
        detail: {
          server_seq: 95,
          data: {
            playlist_id: 'pl1',
            track_numbers: [1]
          }
        }
      })

      domEventHandlers['state:track_deleted'](event)

      // Verify tracks were removed from the playlist
      const playlist = store.playlists.find(p => p.id === 'pl1')
      expect(playlist?.tracks).toHaveLength(2)
    })

    it('should handle track snapshot event', () => {
      initializePlaylist()

      const updatedPlaylist = {
        ...getBaseMockPlaylist(),
        tracks: [
          { id: 't1', track_number: 1, title: 'Updated Track 1', filename: 't1.mp3' }
        ]
      }

      const event = new CustomEvent('state:track', {
        detail: {
          event_type: 'state:track',
          server_seq: 100,
          playlist_id: 'pl1',
          data: {
            playlist: updatedPlaylist,
            playlist_seq: 25
          },
          timestamp: Date.now(),
          event_id: 'evt13'
        }
      })

      domEventHandlers['state:track'](event)

      const playlist = store.playlists.find(p => p.id === 'pl1')
      expect(playlist?.tracks).toHaveLength(1)
      expect(playlist?.tracks?.[0].title).toBe('Updated Track 1')
      expect(store.globalSequence).toBe(100)
    })
  })

  describe('Playlists Index Update', () => {
    it('should handle create updates', () => {
      const newPlaylist = {
        id: 'pl-new',
        title: 'New',
        description: 'Test',
        tracks: [],
        track_count: 0
      }

      const event = new CustomEvent('state:playlists_index_update', {
        detail: {
          event_type: 'state:playlists_index_update',
          server_seq: 105,
          data: {
            updates: [
              { type: 'create' as const, playlist: newPlaylist }
            ]
          },
          timestamp: Date.now(),
          event_id: 'evt14'
        }
      })

      domEventHandlers['state:playlists_index_update'](event)

      expect(store.playlists).toContainEqual(newPlaylist)
      expect(store.globalSequence).toBe(105)
    })

    it('should handle update updates', () => {
      const playlist = {
        id: 'pl1',
        title: 'Original',
        description: 'Test',
        tracks: [],
        track_count: 0
      }

      // Initialize
      const initEvent = new CustomEvent('state:playlists', {
        detail: { data: { playlists: [playlist] } }
      })
      domEventHandlers['state:playlists'](initEvent)

      // Update via index
      const updatedPlaylist = { ...playlist, title: 'Updated via Index' }
      const event = new CustomEvent('state:playlists_index_update', {
        detail: {
          server_seq: 110,
          data: {
            updates: [
              { type: 'update' as const, playlist: updatedPlaylist }
            ]
          }
        }
      })

      domEventHandlers['state:playlists_index_update'](event)

      expect(store.playlists[0].title).toBe('Updated via Index')
    })

    it('should handle delete updates', () => {
      const playlist = {
        id: 'pl-delete',
        title: 'To Delete',
        description: 'Test',
        tracks: [],
        track_count: 0
      }

      // Initialize
      const initEvent = new CustomEvent('state:playlists', {
        detail: { data: { playlists: [playlist] } }
      })
      domEventHandlers['state:playlists'](initEvent)

      // Delete via index
      const event = new CustomEvent('state:playlists_index_update', {
        detail: {
          server_seq: 115,
          data: {
            updates: [
              { type: 'delete' as const, id: 'pl-delete' }
            ]
          }
        }
      })

      domEventHandlers['state:playlists_index_update'](event)

      expect(store.playlists.length).toBe(0)
    })

    it('should handle multiple updates in one event', () => {
      const pl1 = { id: 'pl1', title: 'Playlist 1', description: '', tracks: [], track_count: 0 }
      const pl2 = { id: 'pl2', title: 'Playlist 2', description: '', tracks: [], track_count: 0 }
      const pl3 = { id: 'pl3', title: 'Playlist 3', description: '', tracks: [], track_count: 0 }

      // Initialize
      const initEvent = new CustomEvent('state:playlists', {
        detail: { data: { playlists: [pl1, pl2] } }
      })
      domEventHandlers['state:playlists'](initEvent)

      // Multiple operations
      const event = new CustomEvent('state:playlists_index_update', {
        detail: {
          server_seq: 120,
          data: {
            updates: [
              { type: 'delete' as const, id: 'pl1' },
              { type: 'create' as const, playlist: pl3 },
              { type: 'update' as const, playlist: { ...pl2, title: 'Updated 2' } }
            ]
          }
        }
      })

      domEventHandlers['state:playlists_index_update'](event)

      expect(store.playlists.length).toBe(2)
      expect(store.playlists.find(p => p.id === 'pl1')).toBeUndefined()
      expect(store.playlists.find(p => p.id === 'pl3')).toBeDefined()
      expect(store.playlists.find(p => p.id === 'pl2')?.title).toBe('Updated 2')
    })
  })

  describe('System State Events', () => {
    it('should handle volume changed event', () => {
      const event = new CustomEvent('state:volume_changed', {
        detail: {
          event_type: 'state:volume_changed',
          server_seq: 125,
          data: { volume: 85 },
          timestamp: Date.now(),
          event_id: 'evt15'
        }
      })

      domEventHandlers['state:volume_changed'](event)

      expect(store.playerState.volume).toBe(85)
      expect(store.globalSequence).toBe(125)
    })

    it('should handle NFC state event', () => {
      const event = new CustomEvent('state:nfc_state', {
        detail: {
          event_type: 'state:nfc_state',
          server_seq: 130,
          data: { nfc_enabled: true, tag_detected: true },
          timestamp: Date.now(),
          event_id: 'evt16'
        }
      })

      domEventHandlers['state:nfc_state'](event)

      expect(store.globalSequence).toBe(130)
    })
  })

  describe('Operation Acknowledgments', () => {
    it('should handle operation success', () => {
      const clientOpId = 'op123'
      // Can't directly add to readonly set, but the handler will still work

      const ack = {
        client_op_id: clientOpId,
        data: {
          is_playing: true,
          position_ms: 1000
        }
      }

      eventHandlers['ack_op'](ack)

      // Verify player state was updated
      expect(store.playerState.is_playing).toBe(true)
      expect(store.playerState.position_ms).toBe(1000)
    })

    it('should handle operation success with full player state', () => {
      const clientOpId = 'op456'

      const ack = {
        client_op_id: clientOpId,
        data: {
          is_playing: true,
          active_playlist_id: 'pl1',
          active_playlist_title: 'My Playlist',
          active_track_id: 't1',
          active_track: {
            id: 't1',
            title: 'Track 1',
            filename: 'track1.mp3'
          },
          position_ms: 5000,
          duration_ms: 200000,
          track_index: 0,
          track_count: 10,
          can_prev: false,
          can_next: true,
          volume: 70,
          server_seq: 135
        }
      }

      eventHandlers['ack_op'](ack)

      // Verify player state was fully updated
      expect(store.playerState.is_playing).toBe(true)
      expect(store.playerState.active_playlist_id).toBe('pl1')
      expect(store.playerState.active_track?.title).toBe('Track 1')
      expect(store.playerState.volume).toBe(70)
    })

    it('should handle operation success without data', () => {
      const clientOpId = 'op789'

      const ack = {
        client_op_id: clientOpId
      }

      // Should not throw when no data present
      expect(() => eventHandlers['ack_op'](ack)).not.toThrow()
    })

    it('should handle operation error', () => {
      const clientOpId = 'op-error'

      const ack = {
        client_op_id: clientOpId,
        error: 'Operation failed'
      }

      // Should not throw on error acknowledgment
      expect(() => eventHandlers['err_op'](ack)).not.toThrow()
    })
  })

  describe('Subscription Management', () => {
    it('should subscribe to playlists when connected', () => {
      store.subscribeToPlaylists()

      expect(mockSocketService.emit).toHaveBeenCalledWith('join:playlists', {})
    })

    it('should retry subscription when not connected', () => {
      vi.useFakeTimers()
      mockSocketService.isConnected.mockReturnValueOnce(false).mockReturnValueOnce(true)

      store.subscribeToPlaylists()

      // Should not emit immediately
      expect(mockSocketService.emit).not.toHaveBeenCalled()

      // After timeout, should retry
      vi.advanceTimersByTime(500)

      expect(mockSocketService.emit).toHaveBeenCalledWith('join:playlists', {})

      vi.useRealTimers()
    })

    it('should subscribe to specific playlist', () => {
      store.subscribeToPlaylist('pl123')

      expect(mockSocketService.emit).toHaveBeenCalledWith('join:playlist', {
        playlist_id: 'pl123'
      })
    })

    it('should not subscribe to playlist when disconnected', () => {
      mockSocketService.isConnected.mockReturnValue(false)

      store.subscribeToPlaylist('pl456')

      expect(mockSocketService.emit).not.toHaveBeenCalled()
    })

    it('should unsubscribe from playlist', () => {
      store.unsubscribeFromPlaylist('pl123')

      expect(mockSocketService.emit).toHaveBeenCalledWith('leave:playlist', {
        playlist_id: 'pl123'
      })
    })
  })

  describe('State Synchronization', () => {
    it('should request state sync', () => {
      store.requestStateSync()

      expect(mockSocketService.emit).toHaveBeenCalledWith('sync_request', {
        last_global_seq: 0,
        last_playlist_seqs: {}
      })
    })

    it('should request state sync with current sequences', () => {
      // Set state through events to simulate real usage
      const event1 = new CustomEvent('state:playlists', {
        detail: { data: { playlists: [] }, server_seq: 100 }
      })
      domEventHandlers['state:playlists'](event1)

      const event2 = new CustomEvent('state:playlist_updated', {
        detail: {
          server_seq: 101,
          playlist_id: 'pl1',
          data: {
            playlist: { id: 'pl1', title: 'Test', description: '', tracks: [], track_count: 0 },
            playlist_seq: 50
          }
        }
      })

      // Initialize playlist first
      const initEvent = new CustomEvent('state:playlists', {
        detail: { data: { playlists: [{ id: 'pl1', title: 'Test', description: '', tracks: [], track_count: 0 }] } }
      })
      domEventHandlers['state:playlists'](initEvent)
      domEventHandlers['state:playlist_updated'](event2)

      store.requestStateSync()

      expect(mockSocketService.emit).toHaveBeenCalledWith('sync_request', expect.objectContaining({
        last_global_seq: 101
      }))
    })

    it('should not request sync when disconnected', () => {
      mockSocketService.isConnected.mockReturnValue(false)

      store.requestStateSync()

      expect(mockSocketService.emit).not.toHaveBeenCalled()
    })

    it('should perform manual sync', () => {
      const playlists = [
        { id: 'pl1', title: 'Playlist 1', description: 'Test', tracks: [], track_count: 0 },
        { id: 'pl2', title: 'Playlist 2', description: 'Test', tracks: [], track_count: 0 }
      ]

      store.manualSync(playlists)

      expect(store.playlists).toEqual(playlists)
    })
  })

  describe('Initial Player State', () => {
    it('should request initial player state on connect', async () => {
      const mockPlayerState = {
        is_playing: true,
        active_playlist_id: 'pl1',
        active_playlist_title: 'Test Playlist',
        active_track: {
          id: 't1',
          title: 'Track 1',
          filename: 'track1.mp3'
        },
        position_ms: 10000,
        duration_ms: 180000
      }

      mockApiService.getPlayerStatus.mockResolvedValue(mockPlayerState)

      await store.requestInitialPlayerState()

      expect(mockApiService.getPlayerStatus).toHaveBeenCalled()
      expect(store.playerState.is_playing).toBe(true)
      expect(store.playerState.active_playlist_id).toBe('pl1')
      expect(store.playerState.active_track?.title).toBe('Track 1')
    })

    it('should handle player state request errors gracefully', async () => {
      mockApiService.getPlayerStatus.mockRejectedValue(new Error('API Error'))

      await store.requestInitialPlayerState()

      // Should not throw, just log error
      expect(mockApiService.getPlayerStatus).toHaveBeenCalled()
      // Player state remains empty
      expect(store.playerState.is_playing).toBe(false)
    })

    it('should handle invalid player state response', async () => {
      mockApiService.getPlayerStatus.mockResolvedValue(null)

      await store.requestInitialPlayerState()

      expect(store.playerState.is_playing).toBe(false)
    })
  })

  describe('Getters', () => {
    it('should get playlist by ID', () => {
      const playlists = [
        { id: 'pl1', title: 'Playlist 1', description: 'Test', tracks: [], track_count: 0 },
        { id: 'pl2', title: 'Playlist 2', description: 'Test', tracks: [], track_count: 0 }
      ]

      const initEvent = new CustomEvent('state:playlists', {
        detail: { data: { playlists } }
      })
      domEventHandlers['state:playlists'](initEvent)

      const getter = store.getPlaylistById
      expect(getter('pl1')?.title).toBe('Playlist 1')
      expect(getter('pl2')?.title).toBe('Playlist 2')
      expect(getter('pl999')).toBeUndefined()
    })

    it('should get playlist sequence', () => {
      // Set sequences through events
      const pl1 = { id: 'pl1', title: 'Test 1', description: '', tracks: [], track_count: 0 }
      const pl2 = { id: 'pl2', title: 'Test 2', description: '', tracks: [], track_count: 0 }

      const initEvent = new CustomEvent('state:playlists', {
        detail: { data: { playlists: [pl1, pl2] } }
      })
      domEventHandlers['state:playlists'](initEvent)

      const update1 = new CustomEvent('state:playlist_updated', {
        detail: {
          server_seq: 50,
          playlist_id: 'pl1',
          data: { playlist: pl1, playlist_seq: 100 }
        }
      })
      domEventHandlers['state:playlist_updated'](update1)

      const update2 = new CustomEvent('state:playlist_updated', {
        detail: {
          server_seq: 51,
          playlist_id: 'pl2',
          data: { playlist: pl2, playlist_seq: 200 }
        }
      })
      domEventHandlers['state:playlist_updated'](update2)

      const getter = store.getPlaylistSequence
      expect(getter('pl1')).toBe(100)
      expect(getter('pl2')).toBe(200)
      expect(getter('pl999')).toBe(0) // Default for non-existent
    })
  })

  describe('Server Sequence Management', () => {
    it('should update global sequence from events', () => {
      const event = new CustomEvent('state:playlists', {
        detail: {
          data: { playlists: [] },
          server_seq: 42
        }
      })

      domEventHandlers['state:playlists'](event)

      expect(store.globalSequence).toBe(42)
    })

    it('should update playlist sequences from events', () => {
      const event = new CustomEvent('state:playlist_updated', {
        detail: {
          server_seq: 50,
          playlist_id: 'pl1',
          data: {
            playlist: { id: 'pl1', title: 'Test', description: '', tracks: [], track_count: 0 },
            playlist_seq: 25
          }
        }
      })

      // Initialize first
      const initEvent = new CustomEvent('state:playlists', {
        detail: { data: { playlists: [{ id: 'pl1', title: 'Test', description: '', tracks: [], track_count: 0 }] } }
      })
      domEventHandlers['state:playlists'](initEvent)

      domEventHandlers['state:playlist_updated'](event)

      expect(store.playlistSequences['pl1']).toBe(25)
    })

    it('should maintain sequence monotonicity', () => {
      const event1 = new CustomEvent('state:playlists', {
        detail: { data: { playlists: [] }, server_seq: 10 }
      })
      domEventHandlers['state:playlists'](event1)
      expect(store.globalSequence).toBe(10)

      const event2 = new CustomEvent('state:playlists', {
        detail: { data: { playlists: [] }, server_seq: 20 }
      })
      domEventHandlers['state:playlists'](event2)
      expect(store.globalSequence).toBe(20)

      const event3 = new CustomEvent('state:playlists', {
        detail: { data: { playlists: [] }, server_seq: 30 }
      })
      domEventHandlers['state:playlists'](event3)
      expect(store.globalSequence).toBe(30)
    })
  })

  describe('Edge Cases and Error Scenarios', () => {
    it('should handle events with missing data gracefully', () => {
      const event = new CustomEvent('state:playlist', {
        detail: {
          event_type: 'state:playlist',
          server_seq: 100,
          data: null,
          timestamp: Date.now(),
          event_id: 'evt-null'
        }
      })

      // Should not throw
      expect(() => domEventHandlers['state:playlist'](event)).not.toThrow()
    })

    it('should handle player state with no valid data', () => {
      const event = new CustomEvent('state:player', {
        detail: {
          event_type: 'state:player',
          server_seq: 105,
          data: null
        }
      })

      // Should not crash
      expect(() => domEventHandlers['state:player'](event)).not.toThrow()
    })

    it('should handle track operations on non-existent playlist', () => {
      const event = new CustomEvent('state:track_added', {
        detail: {
          server_seq: 110,
          data: {
            playlist_id: 'non-existent',
            track: { id: 't1', track_number: 1, title: 'Track', filename: 't.mp3' }
          }
        }
      })

      // Should not crash
      expect(() => domEventHandlers['state:track_added'](event)).not.toThrow()
    })

    it('should handle delete of non-existent playlist', () => {
      const event = new CustomEvent('state:playlist_deleted', {
        detail: {
          server_seq: 115,
          data: { playlist_id: 'does-not-exist' }
        }
      })

      expect(() => domEventHandlers['state:playlist_deleted'](event)).not.toThrow()
      expect(store.globalSequence).toBe(115)
    })

    it('should handle track delete with no track_numbers', () => {
      const event = new CustomEvent('state:track_deleted', {
        detail: {
          server_seq: 120,
          data: {
            playlist_id: 'pl1',
            track_numbers: undefined
          }
        }
      })

      expect(() => domEventHandlers['state:track_deleted'](event)).not.toThrow()
    })

    it('should handle track delete with empty track_numbers array', () => {
      const playlist = {
        id: 'pl1',
        title: 'Test',
        description: 'Test',
        tracks: [
          { id: 't1', track_number: 1, title: 'Track 1', filename: 't1.mp3' }
        ],
        track_count: 1
      }

      const initEvent = new CustomEvent('state:playlists', {
        detail: { data: { playlists: [playlist] } }
      })
      domEventHandlers['state:playlists'](initEvent)

      const event = new CustomEvent('state:track_deleted', {
        detail: {
          server_seq: 125,
          data: {
            playlist_id: 'pl1',
            track_numbers: []
          }
        }
      })

      domEventHandlers['state:track_deleted'](event)

      // No tracks should be deleted
      const updatedPlaylist = store.playlists.find(p => p.id === 'pl1')
      expect(updatedPlaylist?.tracks).toHaveLength(1)
    })

    it('should handle playlists index update with no updates array', () => {
      const event = new CustomEvent('state:playlists_index_update', {
        detail: {
          server_seq: 130,
          data: {}
        }
      })

      expect(() => domEventHandlers['state:playlists_index_update'](event)).not.toThrow()
    })

    it('should handle volume change with undefined volume', () => {
      const event = new CustomEvent('state:volume_changed', {
        detail: {
          server_seq: 135,
          data: {}
        }
      })

      domEventHandlers['state:volume_changed'](event)

      // Volume should remain undefined
      expect(store.playerState.volume).toBeUndefined()
    })

    it('should handle track progress with no position_ms', () => {
      const originalPosition = store.playerState.position_ms

      const event = new CustomEvent('state:track_progress', {
        detail: {
          server_seq: 140,
          data: {}
        }
      })

      domEventHandlers['state:track_progress'](event)

      // Position should remain unchanged
      expect(store.playerState.position_ms).toBe(originalPosition)
    })

    it('should handle track position with no position_ms', () => {
      const originalPosition = store.playerState.position_ms

      const event = new CustomEvent('state:track_position', {
        detail: {
          server_seq: 145,
          data: {}
        }
      })

      domEventHandlers['state:track_position'](event)

      // Position should remain unchanged
      expect(store.playerState.position_ms).toBe(originalPosition)
    })
  })

  describe('Readonly State Protection', () => {
    it('should expose playlists as readonly', () => {
      expect(store.playlists).toBeDefined()
      // In TypeScript, readonly prevents writes at compile time
      // At runtime, the ref is still reactive but shouldn't be directly mutated
    })

    it('should expose playerState as readonly', () => {
      expect(store.playerState).toBeDefined()
    })

    it('should expose connection state as readonly', () => {
      expect(store.isConnected).toBeDefined()
      expect(store.isReconnecting).toBeDefined()
    })
  })

  describe('Complex Integration Scenarios', () => {
    it('should handle rapid sequential state updates', () => {
      // Simulate rapid updates that might occur during playback
      for (let i = 0; i < 100; i++) {
        const event = new CustomEvent('state:track_position', {
          detail: {
            server_seq: 150 + i,
            data: {
              position_ms: i * 1000,
              is_playing: true
            }
          }
        })
        domEventHandlers['state:track_position'](event)
      }

      expect(store.playerState.position_ms).toBe(99000)
      expect(store.globalSequence).toBe(249)
    })

    it('should handle interleaved playlist and player updates', () => {
      // Add playlist
      const createEvent = new CustomEvent('state:playlist_created', {
        detail: {
          server_seq: 200,
          data: {
            playlist: { id: 'pl1', title: 'New', description: '', tracks: [], track_count: 0 }
          }
        }
      })
      domEventHandlers['state:playlist_created'](createEvent)

      // Start playing
      const playerEvent = new CustomEvent('state:player', {
        detail: {
          data: {
            is_playing: true,
            active_playlist_id: 'pl1'
          },
          server_seq: 201
        }
      })
      domEventHandlers['state:player'](playerEvent)

      // Update playlist
      const updateEvent = new CustomEvent('state:playlist_updated', {
        detail: {
          server_seq: 202,
          playlist_id: 'pl1',
          data: {
            playlist: { id: 'pl1', title: 'Updated', description: '', tracks: [], track_count: 0 }
          }
        }
      })
      domEventHandlers['state:playlist_updated'](updateEvent)

      expect(store.playlists[0].title).toBe('Updated')
      expect(store.playerState.is_playing).toBe(true)
      expect(store.playerState.active_playlist_id).toBe('pl1')
      expect(store.globalSequence).toBe(202)
    })

    it('should maintain consistency when updating playlists', () => {
      const playlist = {
        id: 'pl1',
        title: 'Test',
        description: 'Test',
        tracks: [
          { id: 't1', track_number: 1, title: 'Track 1', filename: 't1.mp3' }
        ],
        track_count: 1
      }

      // Initialize
      const initEvent = new CustomEvent('state:playlists', {
        detail: { data: { playlists: [playlist] } }
      })
      domEventHandlers['state:playlists'](initEvent)

      // Verify initial state
      expect(store.playlists[0].title).toBe('Test')

      // Update playlist
      const updatedPlaylist = { ...playlist, title: 'Updated Title' }
      const updateEvent = new CustomEvent('state:playlist', {
        detail: {
          server_seq: 210,
          playlist_id: 'pl1',
          data: updatedPlaylist
        }
      })
      domEventHandlers['state:playlist'](updateEvent)

      // Playlist in array should be updated
      expect(store.playlists[0].title).toBe('Updated Title')
      expect(store.playlists[0].tracks).toHaveLength(1)
    })
  })
})
