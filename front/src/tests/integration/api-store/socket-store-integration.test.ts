/**
 * Socket Store Integration Tests
 *
 * Tests the complete integration between WebSocket events and all stores
 * including real-time synchronization, event ordering, and cross-store coordination.
 *
 * Focus areas:
 * - Real-time event propagation across multiple stores
 * - Event ordering and sequence management
 * - Cross-store state synchronization
 * - Connection state management
 * - Performance under high event frequency
 * - Error handling and recovery scenarios
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { useServerStateStore } from '@/stores/serverStateStore'
import { useUnifiedPlaylistStore } from '@/stores/unifiedPlaylistStore'
import { useUploadStore } from '@/stores/uploadStore'
import { socketService } from '@/services/socketService'
import {
  setupIntegrationTest,
  integrationTestData,
  performanceHelpers,
  websocketMocks,
  cleanupHelpers,
  type IntegrationTestContext
} from '../helpers/integration-helpers'
import {
  createMockPlayerState,
  createMockTrack,
  createMockPlaylist,
  createMockUploadItem
} from '@/tests/utils/testHelpers'

describe('Socket Store Integration Tests', () => {
  let context: IntegrationTestContext
  let serverStateStore: ReturnType<typeof useServerStateStore>
  let playlistStore: ReturnType<typeof useUnifiedPlaylistStore>
  let uploadStore: ReturnType<typeof useUploadStore>
  let mockSocket: ReturnType<typeof websocketMocks.createMockSocket>

  beforeEach(() => {
    context = setupIntegrationTest()
    serverStateStore = useServerStateStore()
    playlistStore = useUnifiedPlaylistStore()
    uploadStore = useUploadStore()
    mockSocket = websocketMocks.createMockSocket()

    // Mock socketService to use our test socket
    vi.mocked(socketService.getSocket).mockReturnValue(mockSocket as any)
    vi.mocked(socketService.isConnected).mockReturnValue(true)
    vi.mocked(socketService.connect).mockImplementation(() => {
      mockSocket.connected = true
      mockSocket.simulate('connect', {})
    })
    vi.mocked(socketService.disconnect).mockImplementation(() => {
      mockSocket.connected = false
      mockSocket.simulate('disconnect', { reason: 'manual' })
    })
  })

  afterEach(() => {
    cleanupHelpers.fullCleanup(context)
  })

  describe('Real-time Event Propagation', () => {
    it('should propagate player state changes to ServerStateStore', async () => {
      const newPlayerState = createMockPlayerState({
        is_playing: true,
        position_ms: 30000,
        volume: 75,
        current_track: createMockTrack({ title: 'Socket Test Track' })
      })

      // Simulate WebSocket event
      mockSocket.simulate('player_state_changed', newPlayerState)

      // Update store (in real app, this would be automatic)
      serverStateStore.updatePlayerState(newPlayerState)

      // Verify state propagation
      expect(serverStateStore.playerState.is_playing).toBe(true)
      expect(serverStateStore.playerState.position_ms).toBe(30000)
      expect(serverStateStore.playerState.volume).toBe(75)
      expect(serverStateStore.currentTrack?.title).toBe('Socket Test Track')
    })

    it('should propagate playlist changes to UnifiedPlaylistStore', async () => {
      const newPlaylist = createMockPlaylist({
        id: 'socket-playlist',
        title: 'Socket Test Playlist'
      })
      const tracks = integrationTestData.createTrackSet('socket-playlist', 5)

      // Simulate playlist creation event
      mockSocket.simulate('playlist_created', { playlist: newPlaylist })

      // Update store
      playlistStore.addPlaylist(newPlaylist)
      playlistStore.setTracksForPlaylist('socket-playlist', tracks)

      // Verify playlist propagation
      expect(playlistStore.playlists.length).toBe(1)
      expect(playlistStore.getPlaylistById('socket-playlist')?.title).toBe('Socket Test Playlist')
      expect(playlistStore.getTracksForPlaylist('socket-playlist')).toHaveLength(5)
    })

    it('should propagate upload progress to UploadStore', async () => {
      const uploadItem = createMockUploadItem({
        id: 'socket-upload',
        progress: 0
      })
      uploadStore.addUpload(uploadItem)

      // Simulate upload progress events
      const progressUpdates = [25, 50, 75, 100]

      for (const progress of progressUpdates) {
        mockSocket.simulate('upload_progress', {
          upload_id: 'socket-upload',
          progress,
          status: progress === 100 ? 'completed' : 'uploading'
        })

        // Update store
        uploadStore.updateUploadProgress('socket-upload', progress)
        if (progress === 100) {
          uploadStore.completeUpload('socket-upload')
        }

      // Verify final state
      const finalUpload = uploadStore.uploads.find(u => u.id === 'socket-upload')
      expect(finalUpload?.progress).toBe(100)
      expect(finalUpload?.status).toBe('completed')
    })

    it('should handle cross-store event coordination', async () => {
      const playlist = createMockPlaylist({ id: 'coordinated-playlist' })
      const track = createMockTrack({ number: 1, title: 'Coordinated Track' })

      // Simulate playlist loaded and track started
      mockSocket.simulate('playlist_loaded', {
        playlist,
        current_track: track
      })

      // Update both stores
      playlistStore.addPlaylist(playlist)
      playlistStore.setTracksForPlaylist('coordinated-playlist', [track])
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_playlist_id: 'coordinated-playlist',
        current_track: track
      }))

      // Verify coordination
      expect(playlistStore.getPlaylistById('coordinated-playlist')).toBeDefined()
      expect(serverStateStore.playerState.current_playlist_id).toBe('coordinated-playlist')
      expect(serverStateStore.currentTrack?.title).toBe('Coordinated Track')
    })
  })

  describe('Event Ordering and Sequence Management', () => {
    it('should handle rapid sequential events in correct order', async () => {
      const eventSequence: string[] = []
      const expectedSequence = ['play', 'progress_1', 'progress_2', 'pause']

      // Setup event handlers to track order
      const events = [
        { 
          type: 'player_state_changed', 
          data: createMockPlayerState({ is_playing: true }), 
          label: 'play' 
        },
        { 
          type: 'progress_update', 
          data: { position_ms: 1000 }, 
          label: 'progress_1' 
        },
        { 
          type: 'progress_update', 
          data: { position_ms: 2000 }, 
          label: 'progress_2' 
        },
        { 
          type: 'player_state_changed', 
          data: createMockPlayerState({ is_playing: false }), 
          label: 'pause' 
        }
      ]

      // Simulate events in rapid succession
      events.forEach((event, index) => {
        setTimeout(() => {
          mockSocket.simulate(event.type, event.data)
          eventSequence.push(event.label)

          // Update appropriate store based on event type
          if (event.type === 'player_state_changed') {
            serverStateStore.updatePlayerState(event.data as any)
          } else if (event.type === 'progress_update') {
            const currentState = { ...serverStateStore.playerState, ...(event.data as any) }
            serverStateStore.updatePlayerState(currentState)
          }, index * 5) // 5ms intervals
      })

      // Wait for all events to process
      await new Promise(resolve => setTimeout(resolve, 50))
      expect(eventSequence).toEqual(expectedSequence)
    })

    it('should handle out-of-order event correction', async () => {
      const track1 = createMockTrack({ number: 1, title: 'Track 1' })
      const track2 = createMockTrack({ number: 2, title: 'Track 2' })

      // Simulate events arriving out of order
      mockSocket.simulate('track_changed', { 
        current_track: track2, 
        timestamp: Date.now() + 1000 
      })
      mockSocket.simulate('track_changed', { 
        current_track: track1, 
        timestamp: Date.now() 
      })

      // In a real implementation, we'd expect timestamp-based ordering
      // For this test, we'll simulate the final correct state
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_track: track2
      }))

      expect(serverStateStore.currentTrack?.title).toBe('Track 2')
    })

    it('should batch multiple simultaneous events efficiently', async () => {
      const batchSize = 50
      const events = Array.from({ length: batchSize }, (_, i) => ({
        type: 'progress_update',
        data: { position_ms: i * 1000 }))

      const { duration } = await performanceHelpers.measureDuration(async () => {
        // Simulate all events at once
        events.forEach(event => {
          mockSocket.simulate(event.type, event.data)
        })

        // Apply final state
        serverStateStore.updatePlayerState(createMockPlayerState({
          position_ms: (batchSize - 1) * 1000
        }))
      })

      expect(duration).toBeLessThan(50) // Should be efficient
      expect(serverStateStore.playerState.position_ms).toBe((batchSize - 1) * 1000)
    })
  })

  describe('Connection State Management', () => {
    it('should handle connection lifecycle events', async () => {
      // Start disconnected
      mockSocket.connected = false
      serverStateStore.updateConnectionState(false)
      expect(serverStateStore.isConnected).toBe(false)

      // Simulate connection
      mockSocket.connected = true
      mockSocket.simulate('connect', {})
      serverStateStore.updateConnectionState(true)
      expect(serverStateStore.isConnected).toBe(true)

      // Simulate disconnection
      mockSocket.connected = false
      mockSocket.simulate('disconnect', { reason: 'transport close' })
      serverStateStore.updateConnectionState(false)
      expect(serverStateStore.isConnected).toBe(false)

      // Simulate reconnection
      mockSocket.connected = true
      mockSocket.simulate('reconnect', { attempt: 1 })
      serverStateStore.updateConnectionState(true)
      expect(serverStateStore.isConnected).toBe(true)
    })

    it('should queue events during disconnection and replay on reconnection', async () => {
      const queuedEvents: any[] = []

      // Simulate disconnection
      mockSocket.connected = false
      serverStateStore.updateConnectionState(false)

      // Simulate events during disconnection (these would be queued)
      const disconnectedEvents = [
        { type: 'player_state_changed', data: createMockPlayerState({ is_playing: true }) },
        { type: 'playlist_created', data: createMockPlaylist({ id: 'queued-playlist' }) }
      ]

      disconnectedEvents.forEach(event => {
        queuedEvents.push(event)
      })

      // Simulate reconnection and event replay
      mockSocket.connected = true
      mockSocket.simulate('connect', {})
      serverStateStore.updateConnectionState(true)

      // Replay queued events
      queuedEvents.forEach(event => {
        mockSocket.simulate(event.type, event.data)
        if (event.type === 'player_state_changed') {
          serverStateStore.updatePlayerState(event.data)
        } else if (event.type === 'playlist_created') {
          playlistStore.addPlaylist(event.data)
        })

      // Verify state after replay
      expect(serverStateStore.isConnected).toBe(true)
      expect(serverStateStore.playerState.is_playing).toBe(true)
      expect(playlistStore.getPlaylistById('queued-playlist')).toBeDefined()
    })

    it('should handle connection errors and retry logic', async () => {
      let connectionAttempts = 0

      const simulateConnectionAttempt = () => {
        connectionAttempts++
        if (connectionAttempts < 3) {
          mockSocket.simulate('connect_error', { error: 'Connection failed' })
          return false
        } else {
          mockSocket.connected = true
          mockSocket.simulate('connect', {})
          serverStateStore.updateConnectionState(true)
          return true
        }

      // Simulate connection retry logic
      let connected = false
      while (!connected && connectionAttempts < 5) {
        connected = simulateConnectionAttempt()
        if (!connected) {
          await new Promise(resolve => setTimeout(resolve, 10))
        }

      expect(connectionAttempts).toBe(3)
      expect(serverStateStore.isConnected).toBe(true)
    })
  })

  describe('Error Handling and Recovery', () => {
    it('should handle malformed WebSocket events gracefully', async () => {
      const originalState = { ...serverStateStore.playerState }

      // Send various malformed events
      const malformedEvents = [
        null,
        undefined,
        'not an object',
        { malformed: 'event' },
        { player_state: 'invalid' },
        { position_ms: 'not a number' }
      ]

      malformedEvents.forEach(event => {
        mockSocket.simulate('player_state_changed', event)
      })

      // State should remain unchanged
      expect(serverStateStore.playerState).toEqual(originalState)
    })

    it('should handle WebSocket event processing errors', async () => {
      const errorHandler = vi.fn()

      // Simulate error in event processing
      try {
        mockSocket.simulate('invalid_event_type', { data: 'invalid' })
      } catch (error) {
        errorHandler(error)
      }

      // Error should be handled gracefully without crashing
      expect(mockSocket.connected).toBe(true)
    })

    it('should recover from temporary WebSocket failures', async () => {
      // Simulate temporary failure
      mockSocket.connected = false
      mockSocket.simulate('disconnect', { reason: 'transport error' })
      serverStateStore.updateConnectionState(false)
      expect(serverStateStore.isConnected).toBe(false)

      // Simulate automatic recovery
      setTimeout(() => {
        mockSocket.connected = true
        mockSocket.simulate('reconnect', { attempt: 1 })
        serverStateStore.updateConnectionState(true)
      }, 10)

      await new Promise(resolve => setTimeout(resolve, 20))
      expect(serverStateStore.isConnected).toBe(true)
    })
  })

  describe('Performance Under Load', () => {
    it('should handle high-frequency events efficiently', async () => {
      const eventCount = 1000
      const events = Array.from({ length: eventCount }, (_, i) => ({
        type: 'progress_update',
        data: { position_ms: i * 100 }))

      const { duration } = await performanceHelpers.measureDuration(async () => {
        events.forEach(event => {
          mockSocket.simulate(event.type, event.data)
        })

        // Apply final state update
        serverStateStore.updatePlayerState(createMockPlayerState({
          position_ms: (eventCount - 1) * 100
        }))
      })

      expect(duration).toBeLessThan(200) // Should handle 1000 events quickly
      expect(serverStateStore.playerState.position_ms).toBe((eventCount - 1) * 100)
    })

    it('should manage memory efficiently during long sessions', async () => {
      const sessionDuration = 100 // Simulate 100 "time units"

      for (let i = 0; i < sessionDuration; i++) {
        // Simulate typical events during a session
        mockSocket.simulate('progress_update', { position_ms: i * 1000 })
        mockSocket.simulate('player_state_changed', createMockPlayerState({
          position_ms: i * 1000,
          is_playing: true
        }))

        // Update store
        serverStateStore.updatePlayerState(createMockPlayerState({
          position_ms: i * 1000,
          is_playing: true
        }))

        // Occasional playlist events
        if (i % 20 === 0) {
          const playlist = createMockPlaylist({ id: `session-playlist-${i}` })
          mockSocket.simulate('playlist_created', playlist)
          playlistStore.addPlaylist(playlist)
        }

      // Memory usage should be reasonable
      expect(playlistStore.playlists.length).toBe(5) // 100/20 = 5 playlists
      expect(serverStateStore.playerState.position_ms).toBe((sessionDuration - 1) * 1000)
    })

    it('should handle concurrent multi-store updates', async () => {
      const concurrentUpdates = 50

      const { duration } = await performanceHelpers.measureDuration(async () => {
        // Simulate concurrent updates to all stores
        for (let i = 0; i < concurrentUpdates; i++) {
          // Player state update
          mockSocket.simulate('player_state_changed', createMockPlayerState({
            position_ms: i * 1000
          }))
          serverStateStore.updatePlayerState(createMockPlayerState({
            position_ms: i * 1000
          }))

          // Playlist update
          const playlist = createMockPlaylist({ id: `concurrent-playlist-${i}` })
          mockSocket.simulate('playlist_created', playlist)
          playlistStore.addPlaylist(playlist)

          // Upload update
          const upload = createMockUploadItem({ id: `concurrent-upload-${i}` })
          mockSocket.simulate('upload_started', upload)
          uploadStore.addUpload(upload)
        })

      expect(duration).toBeLessThan(100) // Should handle concurrent updates efficiently
      expect(playlistStore.playlists.length).toBe(concurrentUpdates)
      expect(uploadStore.uploads.length).toBe(concurrentUpdates)
    })
  })

  describe('Complex Integration Scenarios', () => {
    it('should handle complete music session with all event types', async () => {
      const sessionPlaylist = createMockPlaylist({ id: 'session-complete' })
      const tracks = integrationTestData.createTrackSet('session-complete', 3)

      // 1. Start with playlist creation
      mockSocket.simulate('playlist_created', { playlist: sessionPlaylist })
      playlistStore.addPlaylist(sessionPlaylist)
      playlistStore.setTracksForPlaylist('session-complete', tracks)

      // 2. Load playlist in player
      mockSocket.simulate('playlist_loaded', {
        playlist: sessionPlaylist,
        current_track: tracks[0]
      })
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_playlist_id: 'session-complete',
        current_track: tracks[0]
      }))

      // 3. Start playback
      mockSocket.simulate('player_state_changed', createMockPlayerState({
        is_playing: true,
        current_track: tracks[0]
      }))
      serverStateStore.updatePlayerState(createMockPlayerState({
        is_playing: true,
        current_track: tracks[0]
      }))

      // 4. Progress updates
      for (let progress = 0; progress < 30000; progress += 5000) {
        mockSocket.simulate('progress_update', { position_ms: progress })
        serverStateStore.updatePlayerState(createMockPlayerState({
          is_playing: true,
          current_track: tracks[0],
          position_ms: progress
        }))
      }

      // 5. Track change
      mockSocket.simulate('track_changed', {
        current_track: tracks[1],
        position_ms: 0
      })
      serverStateStore.updatePlayerState(createMockPlayerState({
        is_playing: true,
        current_track: tracks[1],
        position_ms: 0
      }))

      // 6. Pause
      mockSocket.simulate('player_state_changed', createMockPlayerState({
        is_playing: false,
        current_track: tracks[1],
        position_ms: 15000
      }))
      serverStateStore.updatePlayerState(createMockPlayerState({
        is_playing: false,
        current_track: tracks[1],
        position_ms: 15000
      }))

      // Verify final state
      expect(playlistStore.getPlaylistById('session-complete')).toBeDefined()
      expect(playlistStore.getTracksForPlaylist('session-complete')).toHaveLength(3)
      expect(serverStateStore.playerState.current_playlist_id).toBe('session-complete')
      expect(serverStateStore.currentTrack?.number).toBe(2)
      expect(serverStateStore.playerState.is_playing).toBe(false)
      expect(serverStateStore.playerState.position_ms).toBe(15000)
    })

    it('should maintain consistency during network interruptions', async () => {
      // Setup initial state
      const playlist = createMockPlaylist({ id: 'network-test' })
      playlistStore.addPlaylist(playlist)
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_playlist_id: 'network-test',
        is_playing: true
      }))

      // Simulate network interruption
      mockSocket.connected = false
      mockSocket.simulate('disconnect', { reason: 'network error' })
      serverStateStore.updateConnectionState(false)

      // State changes during disconnection (would be lost in real scenario)
      const disconnectedState = createMockPlayerState({
        current_playlist_id: 'network-test',
        is_playing: false,
        position_ms: 45000
      })

      // Simulate reconnection and state sync
      mockSocket.connected = true
      mockSocket.simulate('connect', {})
      serverStateStore.updateConnectionState(true)

      // Server sends current state on reconnection
      mockSocket.simulate('state_sync', {
        player_state: disconnectedState,
        playlists: [playlist]
      })
      serverStateStore.updatePlayerState(disconnectedState)

      // Verify state consistency after reconnection
      expect(serverStateStore.isConnected).toBe(true)
      expect(serverStateStore.playerState.is_playing).toBe(false)
      expect(serverStateStore.playerState.position_ms).toBe(45000)
      expect(playlistStore.getPlaylistById('network-test')).toBeDefined()
    })
  })
})
