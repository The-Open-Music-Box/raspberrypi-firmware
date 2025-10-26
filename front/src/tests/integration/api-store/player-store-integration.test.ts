/**
 * Player Store Integration Tests
 *
 * Tests the complete integration between Player API endpoints and ServerStateStore
 * including player commands, state synchronization, and real-time updates.
 *
 * Focus areas:
 * - Player command execution (play, pause, next, previous)
 * - State synchronization between API and store
 * - Real-time WebSocket event handling
 * - Error propagation and recovery
 * - Performance under rapid state changes
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { http, HttpResponse } from 'msw'
import { useServerStateStore } from '@/stores/serverStateStore'
import { apiService } from '@/services/apiService'
import { socketService } from '@/services/socketService'
import {
  setupIntegrationTest,
  mockApiResponses,
  integrationTestData,
  integrationAssertions,
  performanceHelpers,
  websocketMocks,
  cleanupHelpers,
  type IntegrationTestContext
} from '../helpers/integration-helpers'
import { createMockPlayerState, createMockTrack, createMockPlaylist } from '@/tests/utils/testHelpers'

describe('Player Store Integration Tests', () => {
  let context: IntegrationTestContext
  let store: ReturnType<typeof useServerStateStore>
  let mockSocket: ReturnType<typeof websocketMocks.createMockSocket>

  beforeEach(() => {
    context = setupIntegrationTest()
    store = useServerStateStore()
    mockSocket = websocketMocks.createMockSocket()

    // Mock socketService to use our test socket
    vi.mocked(socketService.getSocket)
      .mockReturnValue(mockSocket as any)
    vi.mocked(socketService.isConnected)
      .mockReturnValue(true)
  })

  afterEach(() => {
    cleanupHelpers.fullCleanup(context)
  })

  describe('Player Command Integration', () => {
    it('should execute play command and sync state', async () => {
      // Setup initial paused state
      const initialState = createMockPlayerState({
        is_playing: false,
        position_ms: 0,
        current_track: createMockTrack({ title: 'Test Track' })
      })

      const playingState = createMockPlayerState({
        is_playing: true,
        position_ms: 100,
        current_track: createMockTrack({ title: 'Test Track' })
      })

      // Mock API responses
      context.server.use(
        http.get('/api/player/status', () => {
          return HttpResponse.json(mockApiResponses.success(initialState))
        }),
        http.post('/api/player/play', () => {
          return HttpResponse.json(mockApiResponses.success({ status: 'success' }))
        })
      )

      // Initial state load
      await store.loadPlayerState()
      expect(store.isLoading).toBe(false)
      expect(store.playerState.position_ms).toBe(0)

      // Execute play command
      await apiService.player.play()

      // Simulate WebSocket event for state change
      mockSocket.simulate('player_state_changed', playingState)

      // Verify state synchronization
      expect(store.playerState.is_playing).toBe(true)
      expect(store.playerState.position_ms).toBe(100)
      expect(store.currentTrack?.title).toBe('Test Track')
    })

    it('should handle pause command with position update', async () => {
      const playingState = createMockPlayerState({
        is_playing: true,
        position_ms: 100,
        current_track: createMockTrack({ title: 'Test Track' })
      })

      const pausedState = createMockPlayerState({
        is_playing: false,
        position_ms: 45000,
        current_track: createMockTrack({ title: 'Test Track' })
      })

      context.server.use(
        http.post('/api/player/pause', () => {
          return HttpResponse.json(mockApiResponses.success({ status: 'success' }))
        })
      )

      // Set initial playing state
      store.updatePlayerState(playingState)
      expect(store.playerState.is_playing).toBe(true)

      // Execute pause command
      await apiService.player.pause()

      // Simulate WebSocket state update
      mockSocket.simulate('player_state_changed', pausedState)

      // Verify pause and position retention
      expect(store.playerState.is_playing).toBe(false)
      expect(store.playerState.position_ms).toBe(45000)
    })

    it('should handle track navigation commands', async () => {
      const playlist = createMockPlaylist({ id: 'test-playlist', title: 'Test' })
      const tracks = [
        createMockTrack({ number: 1, title: 'Track 1' }),
        createMockTrack({ number: 2, title: 'Track 2' }),
        createMockTrack({ number: 3, title: 'Track 3' })
      ]

      const initialState = createMockPlayerState({
        current_track: tracks[0],
        current_playlist_id: playlist.id
      })

      const nextTrackState = createMockPlayerState({
        current_track: tracks[1],
        current_playlist_id: playlist.id
      })

      context.server.use(
        http.post('/api/player/next', () => {
          return HttpResponse.json(mockApiResponses.success({
            track: tracks[1],
            position: 2
          }))
        })
      )

      // Set initial state
      store.updatePlayerState(initialState)
      expect(store.currentTrack?.title).toBe('Track 1')

      // Execute next command
      await apiService.player.next()

      // Simulate WebSocket track change
      mockSocket.simulate('track_changed', nextTrackState)

      // Verify track navigation
      expect(store.currentTrack?.title).toBe('Track 2')
      expect(store.playerState.current_playlist_id).toBe('test-playlist')
    })

    it('should handle volume control integration', async () => {
      const volumeChangeState = createMockPlayerState({ volume: 75 })

      context.server.use(
        http.post('/api/player/volume', async ({ request }) => {
          const body = await request.json() as any
          expect(body.volume).toBe(75)
          return HttpResponse.json(mockApiResponses.success({ volume: 75 }))
        })
      )

      // Set initial volume
      store.updatePlayerState(createMockPlayerState({ volume: 50 }))
      expect(store.playerState.volume).toBe(50)

      // Execute volume change
      await apiService.player.setVolume(75)

      // Simulate WebSocket volume update
      mockSocket.simulate('volume_changed', { volume: 75 })

      // Update store with new state
      store.updatePlayerState(volumeChangeState)

      // Verify volume change
      expect(store.playerState.volume).toBe(75)
    })
  })

  describe('Real-time State Synchronization', () => {
    it('should sync player state changes from WebSocket events', async () => {
      const stateSequence = integrationTestData.createPlayerStateSequence()

      // Apply state changes in sequence
      for (const state of stateSequence) {
        mockSocket.simulate('player_state_changed', state)
        store.updatePlayerState(state)
        expect(store.playerState.is_playing).toBe(state.is_playing)
        expect(store.playerState.position_ms).toBe(state.position_ms)
      })

    it('should handle playlist change events', async () => {
      const newPlaylist = createMockPlaylist({ 
        id: 'new-playlist', 
        title: 'New Playlist' 
      })

      const playlistChangeState = createMockPlayerState({
        current_playlist_id: 'new-playlist',
        current_track: createMockTrack({ title: 'First Track from New Playlist' })
      })

      // Simulate playlist change from server
      mockSocket.simulate('playlist_changed', { 
        playlist: newPlaylist,
        current_track: playlistChangeState.current_track
      })
      
      store.updatePlayerState(playlistChangeState)
      expect(store.playerState.current_playlist_id).toBe('new-playlist')
      expect(store.currentTrack?.title).toBe('First Track from New Playlist')
    })

    it('should handle track progress updates', async () => {
      let currentPosition = 0
      const track = createMockTrack({ duration_ms: 180000 }) // 3 minutes

      store.updatePlayerState(createMockPlayerState({
        is_playing: true,
        current_track: track,
        position_ms: 0
      }))

      // Simulate progress updates every second
      const progressInterval = setInterval(() => {
        currentPosition += 1000
        mockSocket.simulate('progress_update', { position_ms: currentPosition })
        store.updatePlayerState(createMockPlayerState({
          is_playing: true,
          current_track: track,
          position_ms: currentPosition
        }))
      }, 10) // Fast simulation

      // Wait for several updates
      await new Promise(resolve => setTimeout(resolve, 50))
      clearInterval(progressInterval)

      expect(store.playerState.position_ms).toBeGreaterThan(0)
      expect(store.playerState.position_ms).toBeLessThanOrEqual(180000)
    })
  })

  describe('Error Handling and Recovery', () => {
    it('should handle API command failures gracefully', async () => {
      context.server.use(
        http.post('/api/player/play', () => {
          return HttpResponse.json(mockApiResponses.error('Playback device not available', 'device_error'), { status: 500 })
        })
      )

      const initialState = store.playerState.is_playing

      // Attempt to play should fail
      await expect(apiService.player.play()).rejects.toThrow()

      // Store state should remain unchanged
      expect(store.playerState.is_playing).toBe(initialState)
    })

    it('should handle WebSocket disconnection and reconnection', async () => {
      // Simulate initial connected state
      mockSocket.connected = true
      store.updateConnectionState(true)
      expect(store.isConnected).toBe(true)

      // Simulate disconnection
      mockSocket.connected = false
      mockSocket.simulate('disconnect', { reason: 'transport close' })
      store.updateConnectionState(false)
      expect(store.isConnected).toBe(false)

      // Simulate reconnection
      mockSocket.connected = true
      mockSocket.simulate('connect', {})
      store.updateConnectionState(true)
      expect(store.isConnected).toBe(true)

      // Should reload player state on reconnection
      const reconnectState = createMockPlayerState({ is_playing: true })
      context.server.use(
        http.get('/api/player/status', () => {
          return HttpResponse.json(mockApiResponses.success(reconnectState))
        })
      )

      await store.loadPlayerState()
      expect(store.playerState.is_playing).toBe(true)
    })

    it('should handle malformed WebSocket events', async () => {
      const originalState = { ...store.playerState }

      // Send invalid events
      mockSocket.simulate('player_state_changed', null)
      mockSocket.simulate('player_state_changed', { invalid: 'data' })
      mockSocket.simulate('player_state_changed', 'not an object')

      // State should remain unchanged
      expect(store.playerState).toEqual(originalState)
    })

    it('should handle rapid command execution', async () => {
      let commandCount = 0

      context.server.use(
        http.post('/api/player/play', () => {
          commandCount++
          return HttpResponse.json(mockApiResponses.success({ status: 'success' }))
        }),
        http.post('/api/player/pause', () => {
          commandCount++
          return HttpResponse.json(mockApiResponses.success({ status: 'success' }))
        })
      )

      // Execute rapid play/pause commands
      const commands = []
      for (let i = 0; i < 10; i++) {
        if (i % 2 === 0) {
          commands.push(apiService.player.play())
        } else {
          commands.push(apiService.player.pause())
        }

      await Promise.all(commands)
      expect(commandCount).toBe(10)
    })
  })

  describe('Performance and Optimization', () => {
    it('should handle high-frequency state updates efficiently', async () => {
      const { duration } = await performanceHelpers.measureDuration(async () => {
        // Simulate 100 rapid state updates
        for (let i = 0; i < 100; i++) {
          const state = createMockPlayerState({
            position_ms: i * 1000,
            is_playing: true
          })
          mockSocket.simulate('player_state_changed', state)
          store.updatePlayerState(state)
        })

      expect(duration).toBeLessThan(100) // Should complete within 100ms
    })

    it('should optimize API calls with state diffing', async () => {
      let apiCallCount = 0

      context.server.use(
        http.get('/api/player/status', () => {
          apiCallCount++
          return HttpResponse.json(mockApiResponses.success(createMockPlayerState()))
        })
      )

      // Multiple calls with same state shouldn't trigger unnecessary API calls
      await store.loadPlayerState()
      await store.loadPlayerState()
      await store.loadPlayerState()

      expect(apiCallCount).toBe(1) // Should be optimized to single call
    })

    it('should handle large playlist navigation efficiently', async () => {
      const largePlaylist = createMockPlaylist({
        id: 'large-playlist',
        track_count: 10000
      })

      const track5000 = createMockTrack({
        number: 5000,
        title: 'Track 5000'
      })

      const navigationState = createMockPlayerState({
        current_track: track5000,
        current_playlist_id: 'large-playlist'
      })

      context.server.use(
        http.post('/api/player/seek-to-track', async ({ request }) => {
          const body = await request.json() as any
          expect(body.track_number).toBe(5000)
          return HttpResponse.json(mockApiResponses.success({
            track: track5000,
            position: 5000
          }))
        })
      )

      const { duration } = await performanceHelpers.measureDuration(async () => {
        await apiService.player.seekToTrack(5000)
        store.updatePlayerState(navigationState)
      })

      expect(duration).toBeLessThan(50) // Should be fast even with large playlists
      expect(store.currentTrack?.title).toBe('Track 5000')
    })
  })

  describe('Integration Workflows', () => {
    it('should handle complete playback session workflow', async () => {
      const playlist = createMockPlaylist({ id: 'test-playlist', title: 'Test' })
      const tracks = integrationTestData.createTrackSet('session-playlist', 3)

      // Setup API responses for complete workflow
      context.server.use(
        http.post('/api/player/load-playlist', () => {
          return HttpResponse.json(mockApiResponses.success({
            playlist,
            current_track: tracks[0]
          }))
        }),
        http.post('/api/player/play', () => {
          return HttpResponse.json(mockApiResponses.success({ status: 'success' }))
        }),
        http.post('/api/player/next', () => {
          return HttpResponse.json(mockApiResponses.success({ track: tracks[1] }))
        }),
        http.post('/api/player/pause', () => {
          return HttpResponse.json(mockApiResponses.success({ status: 'success' }))
        })
      )

      // 1. Load playlist
      await apiService.player.loadPlaylist('session-playlist')
      mockSocket.simulate('playlist_loaded', {
        playlist,
        current_track: tracks[0]
      })
      store.updatePlayerState(createMockPlayerState({ 
        current_playlist_id: 'session-playlist',
        current_track: tracks[0]
      }))

      expect(store.playerState.current_playlist_id).toBe('session-playlist')
      expect(store.currentTrack?.title).toBe(tracks[0].title)

      // 2. Start playback
      await apiService.player.play()
      mockSocket.simulate('player_state_changed', createMockPlayerState({
        is_playing: true,
        current_track: tracks[0]
      }))
      store.updatePlayerState(createMockPlayerState({ 
        is_playing: true,
        current_track: tracks[0]
      }))

      expect(store.playerState.is_playing).toBe(true)

      // 3. Navigate to next track
      await apiService.player.next()
      mockSocket.simulate('track_changed', { current_track: tracks[1] })
      store.updatePlayerState(createMockPlayerState({
        is_playing: true,
        current_track: tracks[1]
      }))

      expect(store.currentTrack?.title).toBe(tracks[1].title)

      // 4. Pause
      await apiService.player.pause()
      mockSocket.simulate('player_state_changed', createMockPlayerState({ 
        is_playing: false,
        current_track: tracks[1]
      }))
      store.updatePlayerState(createMockPlayerState({
        is_playing: false,
        current_track: tracks[1]
      }))

      expect(store.playerState.is_playing).toBe(false)
    })

    it('should sync state during simultaneous API and WebSocket updates', async () => {
      let apiResponseCount = 0
      let websocketEventCount = 0

      context.server.use(
        http.post('/api/player/play', () => {
          apiResponseCount++
          setTimeout(() => {
            websocketEventCount++
            mockSocket.simulate('player_state_changed', createMockPlayerState({ 
              is_playing: true,
              position_ms: 0
            }))
          }, 10)

          return HttpResponse.json(mockApiResponses.success({ status: 'success' }))
        })
      )

      // Execute command and wait for both API and WebSocket
      await apiService.player.play()
      await new Promise(resolve => setTimeout(resolve, 20))

      expect(apiResponseCount).toBe(1)
      expect(websocketEventCount).toBe(1)
    })
  })

  describe('Edge Cases and Boundary Conditions', () => {
    it('should handle player state during track transitions', async () => {
      const track1 = createMockTrack({ number: 1, duration_ms: 30000 })
      const track2 = createMockTrack({ number: 2, duration_ms: 30000 })

      // Simulate approaching end of track
      store.updatePlayerState(createMockPlayerState({
        current_track: track1,
        position_ms: 29800, // Near end
        is_playing: true
      }))

      // Simulate automatic track transition
      mockSocket.simulate('track_ended', { track: track1 })
      mockSocket.simulate('track_started', { track: track2 })
      store.updatePlayerState(createMockPlayerState({
        current_track: track2,
        position_ms: 0,
        is_playing: true
      }))

      expect(store.currentTrack?.number).toBe(2)
      expect(store.playerState.position_ms).toBe(0)
    })

    it('should handle empty playlist scenarios', async () => {
      const emptyState = createMockPlayerState({
        current_track: null,
        current_playlist_id: null,
        is_playing: false
      })

      context.server.use(
        http.post('/api/player/play', () => {
          return HttpResponse.json(mockApiResponses.error('No playlist loaded', 'no_playlist'), { status: 400 })
        })
      )

      store.updatePlayerState(emptyState)
      await expect(apiService.player.play()).rejects.toThrow()
      expect(store.currentTrack).toBeNull()
      expect(store.playerState.is_playing).toBe(false)
    })

    it('should handle concurrent command execution', async () => {
      let commandOrder: string[] = []

      context.server.use(
        http.post('/api/player/play', async () => {
          await new Promise(resolve => setTimeout(resolve, 10))
          commandOrder.push('play')
          return HttpResponse.json(mockApiResponses.success({ status: 'success' }))
        }),
        http.post('/api/player/pause', async () => {
          await new Promise(resolve => setTimeout(resolve, 5))
          commandOrder.push('pause')
          return HttpResponse.json(mockApiResponses.success({ status: 'success' }))
        })
      )

      // Execute commands concurrently
      const playPromise = apiService.player.play()
      const pausePromise = apiService.player.pause()
      await Promise.all([playPromise, pausePromise])

      // Pause should complete first due to shorter delay
      expect(commandOrder).toEqual(['pause', 'play'])
    })
  })
})
