/**
 * Test Helper Utilities for TheOpenMusicBox Frontend Tests
 *
 * Provides reusable mocks, factories, and test utilities to standardize
 * testing patterns across the application.
 */

import { vi, type MockedFunction } from 'vitest'
import type { VueWrapper } from '@vue/test-utils'

// Types for stores and services
export interface MockPlayerState {
  is_playing: boolean
  active_playlist_id: string | null
  active_playlist_title: string | null
  active_track: any | null
  position_ms: number
  duration_ms: number
  can_prev: boolean
  can_next: boolean
  server_seq: number
  track_index?: number
  track_count?: number
  volume?: number
  muted?: boolean
  state?: string
}

export interface MockTrack {
  id?: string
  track_number: number
  title: string
  artist?: string
  album?: string
  filename: string
  duration_ms: number
  file_size?: number
  created_at?: string
  file_path?: string
}

export interface MockPlaylist {
  id: string
  title: string
  description?: string
  tracks: MockTrack[]
  track_count?: number
  nfc_tag_id?: string
  created_at?: string
  updated_at?: string
}

/**
 * Factory for creating mock tracks
 */
export const createMockTrack = (overrides: Partial<MockTrack> = {}): MockTrack => ({
  id: 'test-track-1',
  track_number: 1,
  title: 'Test Track',
  artist: 'Test Artist',
  album: 'Test Album',
  filename: 'test.mp3',
  duration_ms: 180000,
  file_path: '/tracks/test.mp3',
  ...overrides
})

/**
 * Factory for creating mock playlists
 */
export const createMockPlaylist = (overrides: Partial<MockPlaylist> = {}): MockPlaylist => ({
  id: 'test-playlist-1',
  title: 'Test Playlist',
  description: 'A test playlist',
  tracks: [createMockTrack()],
  track_count: 1,
  ...overrides
})

/**
 * Factory for creating mock player state
 */
export const createMockPlayerState = (overrides: Partial<MockPlayerState> = {}): MockPlayerState => ({
  is_playing: false,
  active_playlist_id: null,
  active_playlist_title: null,
  active_track: null,
  position_ms: 0,
  duration_ms: 0,
  can_prev: false,
  can_next: false,
  server_seq: 0,
  ...overrides
})

/**
 * Creates a mock server state store
 */
export const createMockServerStateStore = (playerState: Partial<MockPlayerState> = {}) => ({
  playerState: createMockPlayerState(playerState),
  playlists: [],
  currentPlaylist: null,
  globalSequence: 0,
  isConnected: true,
  isReconnecting: false,
  // Methods
  connect: vi.fn(),
  disconnect: vi.fn(),
  updatePlayerState: vi.fn(),
  updatePlaylists: vi.fn(),
  // Pinia store methods
  $subscribe: vi.fn(),
  $patch: vi.fn(),
  $reset: vi.fn(),
  $dispose: vi.fn(),
  $state: {},
  $id: 'serverState'
})

/**
 * Creates a mock unified playlist store
 */
export const createMockUnifiedPlaylistStore = () => {
  const mockPlaylists: MockPlaylist[] = []

  return {
    // State
    playlists: new Map(),
    tracks: new Map(),
    isLoading: false,
    error: null,
    isInitialized: true,

    // Computed getters that return functions
    getAllPlaylists: mockPlaylists,
    getPlaylistById: vi.fn((id: string) => mockPlaylists.find(p => p.id === id)),
    getPlaylistWithTracks: vi.fn((id: string) => {
      const playlist = mockPlaylists.find(p => p.id === id)
      return playlist ? { ...playlist, tracks: playlist.tracks || [] } : undefined
    }),
    getTracksForPlaylist: vi.fn((id: string) => {
      const playlist = mockPlaylists.find(p => p.id === id)
      return playlist?.tracks || []
    }),
    getTrackByNumber: vi.fn((playlistId: string, trackNumber: number) => {
      const playlist = mockPlaylists.find(p => p.id === playlistId)
      return playlist?.tracks?.find(t => t.track_number === trackNumber)
    }),
    hasPlaylistData: vi.fn((id: string) => mockPlaylists.some(p => p.id === id)),
    hasTracksData: vi.fn((id: string) => {
      const playlist = mockPlaylists.find(p => p.id === id)
      return playlist?.tracks && playlist.tracks.length > 0
    }),

    // Actions
    initialize: vi.fn().mockResolvedValue(undefined),
    loadPlaylists: vi.fn().mockResolvedValue(undefined),
    addPlaylist: vi.fn().mockResolvedValue(undefined),
    updatePlaylist: vi.fn().mockResolvedValue(undefined),
    deletePlaylist: vi.fn().mockResolvedValue(undefined),
    addTrackToPlaylist: vi.fn().mockResolvedValue(undefined),
    removeTrackFromPlaylist: vi.fn().mockResolvedValue(undefined),

    // Helper to set playlists in tests
    _setPlaylists: (newPlaylists: MockPlaylist[]) => {
      mockPlaylists.splice(0, mockPlaylists.length, ...newPlaylists)
    },
    // Pinia store methods
    $subscribe: vi.fn(),
    $patch: vi.fn(),
    $reset: vi.fn(),
    $dispose: vi.fn(),
    $state: {},
    $id: 'unifiedPlaylist'
  }
}

/**
 * Creates a mock API service
 */
export const createMockApiService = () => ({
  player: {
    play: vi.fn().mockResolvedValue({ status: 'success' }),
    pause: vi.fn().mockResolvedValue({ status: 'success' }),
    stop: vi.fn().mockResolvedValue({ status: 'success' }),
    next: vi.fn().mockResolvedValue({ status: 'success' }),
    previous: vi.fn().mockResolvedValue({ status: 'success' }),
    seek: vi.fn().mockResolvedValue({ status: 'success' }),
    getStatus: vi.fn().mockResolvedValue({ status: 'success', data: {} })
  },
  playlists: {
    getAll: vi.fn().mockResolvedValue({ status: 'success', data: { playlists: [] } }),
    getById: vi.fn().mockResolvedValue({ status: 'success', data: {} }),
    create: vi.fn().mockResolvedValue({ status: 'success', data: {} }),
    update: vi.fn().mockResolvedValue({ status: 'success', data: {} }),
    delete: vi.fn().mockResolvedValue({ status: 'success' }),
    playPlaylist: vi.fn().mockResolvedValue({ status: 'success' })
  },
  nfc: {
    getStatus: vi.fn().mockResolvedValue({ status: 'success', data: { reader_available: true } }),
    associate: vi.fn().mockResolvedValue({ status: 'success' }),
    dissociate: vi.fn().mockResolvedValue({ status: 'success' })
  },
  upload: {
    uploadFile: vi.fn().mockResolvedValue({ status: 'success', data: {} }),
    getUploadStatus: vi.fn().mockResolvedValue({ status: 'success', data: {} })
  }
})

/**
 * Standard Vue component stubs for testing
 */
export const createComponentStubs = () => ({
  // Audio components
  TrackInfo: {
    name: 'TrackInfo',
    template: '<div data-testid="track-info">{{ track?.title || "No Track" }}</div>',
    props: ['track', 'playlistTitle', 'duration']
  },
  ProgressBar: {
    name: 'ProgressBar',
    template: '<div data-testid="progress-bar" @click="$emit(\'seek\', 30000)">{{ currentTime }}/{{ duration }}</div>',
    props: ['currentTime', 'duration'],
    emits: ['seek']
  },
  PlaybackControls: {
    name: 'PlaybackControls',
    template: `
      <div data-testid="playback-controls">
        <button data-testid="play-pause" @click="$emit('toggle-play-pause')">
          {{ isPlaying ? 'Pause' : 'Play' }}
        </button>
        <button data-testid="previous" @click="$emit('previous')" :disabled="!canPrevious">Previous</button>
        <button data-testid="next" @click="$emit('next')" :disabled="!canNext">Next</button>
      </div>
    `,
    props: ['isPlaying', 'canPrevious', 'canNext'],
    emits: ['toggle-play-pause', 'previous', 'next']
  },
  // File components
  FilesList: {
    name: 'FilesList',
    template: '<div data-testid="files-list">Files List</div>',
    props: ['playlists', 'selectedTrack', 'playingPlaylistId', 'playingTrackNumber'],
    emits: ['deleteTrack', 'select-track', 'play-playlist', 'feedback', 'playlist-added', 'playlist-deleted', 'playlist-updated']
  },
  DeleteDialog: {
    name: 'DeleteDialog',
    template: '<div data-testid="delete-dialog" v-if="open">Delete Dialog</div>',
    props: ['open', 'track', 'playlist'],
    emits: ['close', 'confirm']
  },
  // Upload components
  UploadModal: {
    name: 'UploadModal',
    template: '<div data-testid="upload-modal" v-if="visible">Upload Modal</div>',
    props: ['visible'],
    emits: ['close', 'upload-complete']
  }
})

/**
 * Creates global mocks for common dependencies
 */
export const setupGlobalMocks = () => {
  // Mock i18n
  const mockT = vi.fn((key: string, params?: any) => {
    if (params) {
      return `${key} ${JSON.stringify(params)}`
    }
    return key
  })

  // Mock logger
  const mockLogger = {
    info: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
    warn: vi.fn()
  }

  // Mock track field accessors
  const mockTrackAccessors = {
    getTrackNumber: vi.fn((track: any) => track?.track_number || 1),
    getTrackDurationMs: vi.fn((track: any) => track?.duration_ms || 180000),
    findTrackByNumber: vi.fn((tracks: any[], number: number) =>
      tracks.find(t => t.track_number === number)
    )
  }

  return {
    t: mockT,
    logger: mockLogger,
    trackAccessors: mockTrackAccessors
  }
}

/**
 * Helper to wait for Vue reactivity updates
 */
export const flushPromises = () => new Promise(resolve => setTimeout(resolve, 0))

/**
 * Helper to trigger events and wait for updates
 */
export const triggerAndWait = async (wrapper: VueWrapper<any>, selector: string, event: string = 'click') => {
  await wrapper.find(selector).trigger(event)
  await flushPromises()
  return wrapper
}

/**
 * Helper to check if component has emitted specific event
 */
export const expectEmitted = (wrapper: VueWrapper<any>, eventName: string, expectedArgs?: any) => {
  const emitted = wrapper.emitted(eventName)
  expect(emitted).toBeTruthy()
  if (expectedArgs !== undefined) {
    expect(emitted![emitted!.length - 1]).toEqual(expectedArgs)
  }
}

/**
 * Helper to mock next tick for async operations
 */
export const nextTick = () => new Promise(resolve => setTimeout(resolve, 0))

/**
 * Mock setup for common stores - can be used in beforeEach
 */
export const setupMockStores = (options: {
  playerState?: Partial<MockPlayerState>
  playlists?: MockPlaylist[]
} = {}) => {
  const mockServerStateStore = createMockServerStateStore(options.playerState)
  const mockUnifiedPlaylistStore = createMockUnifiedPlaylistStore()

  if (options.playlists) {
    mockUnifiedPlaylistStore.playlists = options.playlists
  }

  return {
    mockServerStateStore,
    mockUnifiedPlaylistStore
  }
}

/**
 * Default test configuration for mount options
 */
export const createMountOptions = (overrides: any = {}) => ({
  global: {
    stubs: createComponentStubs(),
    mocks: {
      $t: (key: string) => key,
      $route: { path: '/', params: {}, query: {} },
      $router: { push: vi.fn(), replace: vi.fn() }
    },
    ...overrides.global
  },
  ...overrides
})