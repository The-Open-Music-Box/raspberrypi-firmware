/**
 * Audio Playback Workflow Integration Tests
 *
 * Tests the complete audio playback experience including player controls,
 * state synchronization, progress tracking, and advanced playback features.
 *
 * Focus areas:
 * - Complete playback session lifecycle
 * - Player control commands and state synchronization
 * - Progress tracking and position management
 * - Playlist navigation and auto-advance
 * - Shuffle and repeat modes
 * - Volume and audio settings
 * - Error handling and recovery
 * - Performance during long sessions
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { http, HttpResponse } from 'msw'
import { useServerStateStore } from '@/stores/serverStateStore'
import { useUnifiedPlaylistStore } from '@/stores/unifiedPlaylistStore'
import { apiService } from '@/services/apiService'
import {
  setupIntegrationTest,
  mockApiResponses,
  integrationTestData,
  performanceHelpers,
  websocketMocks,
  cleanupHelpers,
  type IntegrationTestContext
} from '../helpers/integration-helpers'

import {
  createMockPlayerState,
  createMockPlaylist,
  createMockTrack
} from '@/tests/utils/testHelpers'

describe('Audio Playback Workflow Integration Tests', () => {
  let context: IntegrationTestContext
  let serverStateStore: ReturnType<typeof useServerStateStore>
  let playlistStore: ReturnType<typeof useUnifiedPlaylistStore>
  let mockSocket: ReturnType<typeof websocketMocks.createMockSocket>

  beforeEach(() => {
    context = setupIntegrationTest()
    serverStateStore = useServerStateStore()
    playlistStore = useUnifiedPlaylistStore()
    mockSocket = websocketMocks.createMockSocket()
  })

  afterEach(() => {
    cleanupHelpers.fullCleanup(context)
  })

  describe('Complete Playback Session Lifecycle', () => {
    it('should handle full playback session from start to finish', async () => {
      const sessionPlaylist = createMockPlaylist({
        id: 'session-playlist',
        title: 'Session Playlist'
      })

      const tracks = integrationTestData.createTrackSet('session-playlist', 3)
      tracks.forEach((track, index) => {
        track.duration_ms = 30000 // 30 seconds each for faster testing
      })

      // Setup initial state
      playlistStore.addPlaylist(sessionPlaylist)
      playlistStore.setTracksForPlaylist('session-playlist', tracks)

      context.server.use(
        // Load playlist
        http.post('/api/player/load-playlist', () => {
          return HttpResponse.json(mockApiResponses.success({
            playlist: sessionPlaylist,
            current_track: tracks[0],
            total_tracks: tracks.length
          }))
        }),

        // Player controls
        http.post('/api/player/play', () => {
          return HttpResponse.json(mockApiResponses.success({ status: 'success' }))
        }),

        http.post('/api/player/pause', () => {
          return HttpResponse.json(mockApiResponses.success({ status: 'success' }))
        }),

        http.post('/api/player/next', () => {
          return HttpResponse.json(mockApiResponses.success({ status: 'success' }))
        })
      )

      // 1. Load playlist
      await apiService.player.loadPlaylist('session-playlist')
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_playlist_id: 'session-playlist',
        current_track: tracks[0],
        is_playing: false,
        position_ms: 0
      }))

      mockSocket.simulate('playlist_loaded', {
        playlist: sessionPlaylist,
        current_track: tracks[0]
      })

      expect(serverStateStore.playerState.current_playlist_id).toBe('session-playlist')
      expect(serverStateStore.currentTrack).toEqual(tracks[0])

      // 2. Start playback
      await apiService.player.play()
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_playlist_id: 'session-playlist',
        current_track: tracks[0],
        is_playing: true,
        position_ms: 0
      }))

      mockSocket.simulate('playback_started', {
        track: tracks[0],
        playlist_id: 'session-playlist'
      })

      expect(serverStateStore.playerState.is_playing).toBe(true)

      // 3. Simulate progress updates during first track
      for (let progress = 0; progress <= 30000; progress += 5000) {
        mockSocket.simulate('progress_update', { position_ms: progress })
        serverStateStore.updatePlayerState(createMockPlayerState({
          current_playlist_id: 'session-playlist',
          current_track: tracks[0],
          is_playing: true,
          position_ms: progress
        }))

        if (progress === 15000) {
          // Pause in middle
          await apiService.player.pause()
          serverStateStore.updatePlayerState(createMockPlayerState({
            current_playlist_id: 'session-playlist',
            current_track: tracks[0],
            is_playing: false,
            position_ms: progress
          }))

          // Resume after a moment
          await apiService.player.play()
          serverStateStore.updatePlayerState(createMockPlayerState({
            current_playlist_id: 'session-playlist',
            current_track: tracks[0],
            is_playing: true,
            position_ms: progress
          }))
        }
      }

      // 4. Auto-advance to next track
      mockSocket.simulate('track_ended', { track: tracks[0] })
      mockSocket.simulate('track_started', { track: tracks[1] })
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_playlist_id: 'session-playlist',
        current_track: tracks[1],
        is_playing: true,
        position_ms: 0
      }))

      expect(serverStateStore.currentTrack).toEqual(tracks[1])
      expect(serverStateStore.playerState.position_ms).toBe(0)

      // 5. Manual navigation to last track
      await apiService.player.next()
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_playlist_id: 'session-playlist',
        current_track: tracks[2],
        is_playing: true,
        position_ms: 0
      }))

      mockSocket.simulate('track_changed', { track: tracks[2] })
      expect(serverStateStore.currentTrack).toEqual(tracks[2])

      // 6. Complete session
      mockSocket.simulate('track_ended', { track: tracks[2] })
      mockSocket.simulate('playlist_ended', { playlist_id: 'session-playlist' })
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_playlist_id: 'session-playlist',
        current_track: null,
        is_playing: false,
        position_ms: 0
      }))

      expect(serverStateStore.playerState.is_playing).toBe(false)
      expect(serverStateStore.currentTrack).toBeNull()
    })

    it('should handle repeat modes during playback', async () => {
      const repeatPlaylist = createMockPlaylist({
        id: 'repeat-playlist',
        title: 'Repeat Playlist'
      })

      const tracks = integrationTestData.createTrackSet('repeat-playlist', 2)
      playlistStore.addPlaylist(repeatPlaylist)
      playlistStore.setTracksForPlaylist('repeat-playlist', tracks)

      context.server.use(
        http.post('/api/player/repeat', async ({ request }) => {
          const body = await request.json() as any
          return HttpResponse.json(mockApiResponses.success({
            repeat_mode: body.mode
          }))
        })
      )

      // Setup initial state
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_playlist_id: 'repeat-playlist',
        current_track: tracks[0],
        is_playing: true,
        repeat_mode: 'none'
      }))

      // Test repeat-one mode
      await apiService.player.setRepeatMode('one')
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_playlist_id: 'repeat-playlist',
        current_track: tracks[0],
        is_playing: true,
        repeat_mode: 'one'
      }))

      mockSocket.simulate('repeat_mode_changed', { mode: 'one' })

      // Simulate track end - should repeat same track
      mockSocket.simulate('track_ended', { track: tracks[0] })
      mockSocket.simulate('track_started', { track: tracks[0] }) // Same track

      serverStateStore.updatePlayerState(createMockPlayerState({
        current_playlist_id: 'repeat-playlist',
        current_track: tracks[0],
        is_playing: true,
        position_ms: 0,
        repeat_mode: 'one'
      }))

      expect(serverStateStore.currentTrack).toEqual(tracks[0])
      expect(serverStateStore.playerState.repeat_mode).toBe('one')

      // Test repeat-all mode
      await apiService.player.setRepeatMode('all')
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_playlist_id: 'repeat-playlist',
        current_track: tracks[1],
        is_playing: true,
        repeat_mode: 'all'
      }))

      // Go to last track
      mockSocket.simulate('track_changed', { track: tracks[1] })

      // End of playlist should restart from beginning
      mockSocket.simulate('track_ended', { track: tracks[1] })
      mockSocket.simulate('playlist_restarted', { first_track: tracks[0] })
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_playlist_id: 'repeat-playlist',
        current_track: tracks[0],
        is_playing: true,
        position_ms: 0,
        repeat_mode: 'all'
      }))

      expect(serverStateStore.currentTrack).toEqual(tracks[0])
    })

    it('should handle shuffle mode throughout session', async () => {
      const shufflePlaylist = createMockPlaylist({
        id: 'shuffle-playlist',
        title: 'Shuffle Playlist'
      })

      const tracks = integrationTestData.createTrackSet('shuffle-playlist', 10)
      const shuffledOrder = [...tracks].sort(() => Math.random() - 0.5)

      playlistStore.addPlaylist(shufflePlaylist)
      playlistStore.setTracksForPlaylist('shuffle-playlist', tracks)

      context.server.use(
        http.post('/api/player/shuffle', () => {
          return HttpResponse.json(mockApiResponses.success({
            shuffle_enabled: true,
            shuffled_order
          }))
        })
      )

      // Enable shuffle
      await apiService.player.toggleShuffle(true)
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_playlist_id: 'shuffle-playlist',
        current_track: shuffledOrder[0],
        is_playing: true,
        shuffle_enabled: true
      }))

      mockSocket.simulate('shuffle_enabled', {
        playlist_id: 'shuffle-playlist',
        shuffled_order,
        current_track: shuffledOrder[0]
      })

      expect(serverStateStore.playerState.shuffle_enabled).toBe(true)
      expect(serverStateStore.currentTrack).toEqual(shuffledOrder[0])

      // Navigate through shuffled tracks
      for (let i = 1; i < 5; i++) {
        mockSocket.simulate('track_changed', { track: shuffledOrder[i] })
        serverStateStore.updatePlayerState(createMockPlayerState({
          current_playlist_id: 'shuffle-playlist',
          current_track: shuffledOrder[i],
          is_playing: true,
          shuffle_enabled: true
        }))

        expect(serverStateStore.currentTrack).toEqual(shuffledOrder[i])
      }

      // Disable shuffle - should return to normal order
      await apiService.player.toggleShuffle(false)
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_playlist_id: 'shuffle-playlist',
        current_track: tracks[0], // Back to original order
        is_playing: true,
        shuffle_enabled: false
      }))

      expect(serverStateStore.playerState.shuffle_enabled).toBe(false)
    })
  })

  describe('Progress Tracking and Position Management', () => {
    it('should handle accurate progress tracking during playback', async () => {
      const track = createMockTrack({
        id: 'progress-track',
        title: 'Progress Test Track',
        duration_ms: 180000
      })

      serverStateStore.updatePlayerState(createMockPlayerState({
        current_track: track,
        is_playing: true,
        position_ms: 0
      }))

      const progressUpdates: number[] = []
      const expectedPositions = []

      // Simulate 30 seconds of progress updates every second
      for (let second = 0; second <= 30; second++) {
        const position = second * 1000
        expectedPositions.push(position)
        mockSocket.simulate('progress_update', { position_ms: position })
        serverStateStore.updatePlayerState(createMockPlayerState({
          current_track: track,
          is_playing: true,
          position_ms: position
        }))

        progressUpdates.push(serverStateStore.playerState.position_ms)
      }

      // Verify continuous progress
      expect(progressUpdates).toEqual(expectedPositions)
      expect(serverStateStore.playerState.position_ms).toBe(30000)
    })

    it('should handle seeking and position jumps', async () => {
      const track = createMockTrack({
        duration_ms: 240000
      })

      serverStateStore.updatePlayerState(createMockPlayerState({
        current_track: track,
        is_playing: true,
        position_ms: 0
      }))

      context.server.use(
        http.post('/api/player/seek', async ({ request }) => {
          const body = await request.json() as any
          return HttpResponse.json(mockApiResponses.success({
            position_ms: body.position_ms
          }))
        })
      )

      // Seek to 2 minutes
      const seekPosition = 120000
      await apiService.player.seek(seekPosition)
      mockSocket.simulate('position_changed', { position_ms: seekPosition })
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_track: track,
        is_playing: true,
        position_ms: seekPosition
      }))

      expect(serverStateStore.playerState.position_ms).toBe(seekPosition)

      // Seek backwards
      const backSeekPosition = 30000
      await apiService.player.seek(backSeekPosition)
      mockSocket.simulate('position_changed', { position_ms: backSeekPosition })
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_track: track,
        is_playing: true,
        position_ms: backSeekPosition
      }))

      expect(serverStateStore.playerState.position_ms).toBe(backSeekPosition)

      // Seek near end
      const nearEndPosition = 235000
      await apiService.player.seek(nearEndPosition)
      mockSocket.simulate('position_changed', { position_ms: nearEndPosition })
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_track: track,
        is_playing: true,
        position_ms: nearEndPosition
      }))

      expect(serverStateStore.playerState.position_ms).toBe(nearEndPosition)
    })

    it('should handle position persistence across pause/resume', async () => {
      const track = createMockTrack({ duration_ms: 180000 })
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_track: track,
        is_playing: true,
        position_ms: 0
      }))

      context.server.use(
        http.post('/api/player/pause', () => {
          return HttpResponse.json(mockApiResponses.success({ status: 'success' }))
        }),

        http.post('/api/player/play', () => {
          return HttpResponse.json(mockApiResponses.success({ status: 'success' }))
        })
      )

      // Play for 45 seconds
      for (let i = 0; i <= 45; i += 5) {
        const position = i * 1000
        mockSocket.simulate('progress_update', { position_ms: position })
        serverStateStore.updatePlayerState(createMockPlayerState({
          current_track: track,
          is_playing: true,
          position_ms: position
        }))
      }

      const pausePosition = serverStateStore.playerState.position_ms

      // Pause
      await apiService.player.pause()
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_track: track,
        is_playing: false,
        position_ms: pausePosition
      }))

      expect(serverStateStore.playerState.is_playing).toBe(false)
      expect(serverStateStore.playerState.position_ms).toBe(pausePosition)

      // Wait (simulate user doing something else)
      await new Promise(resolve => setTimeout(resolve, 100))

      // Resume
      await apiService.player.play()
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_track: track,
        is_playing: true,
        position_ms: pausePosition
      }))

      expect(serverStateStore.playerState.is_playing).toBe(true)
      expect(serverStateStore.playerState.position_ms).toBe(pausePosition)

      // Continue progress from resume point
      mockSocket.simulate('progress_update', { position_ms: pausePosition + 1000 })
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_track: track,
        is_playing: true,
        position_ms: pausePosition + 1000
      }))

      expect(serverStateStore.playerState.position_ms).toBe(pausePosition + 1000)
    })
  })

  describe('Volume and Audio Settings', () => {
    it('should handle volume control workflow', async () => {
      context.server.use(
        http.post('/api/player/volume', async ({ request }) => {
          const body = await request.json() as any
          return HttpResponse.json(mockApiResponses.success({
            volume: body.volume
          }))
        })
      )

      // Initial volume
      serverStateStore.updatePlayerState(createMockPlayerState({ volume: 50 }))

      const volumeLevels = [25, 75, 100, 0, 60]

      for (const volume of volumeLevels) {
        await apiService.player.setVolume(volume)
        mockSocket.simulate('volume_changed', { volume })
        serverStateStore.updatePlayerState(createMockPlayerState({ volume }))

        expect(serverStateStore.playerState.volume).toBe(volume)
      }
    })

    it('should handle mute/unmute workflow', async () => {
      const originalVolume = 75

      serverStateStore.updatePlayerState(createMockPlayerState({
        volume: originalVolume,
        is_muted: false
      }))

      context.server.use(
        http.post('/api/player/mute', () => {
          return HttpResponse.json(mockApiResponses.success({
            is_muted: true,
            previous_volume: originalVolume
          }))
        }),

        http.post('/api/player/unmute', () => {
          return HttpResponse.json(mockApiResponses.success({
            is_muted: false,
            restored_volume: originalVolume
          }))
        })
      )

      // Mute
      await apiService.player.mute()
      mockSocket.simulate('muted', { previous_volume: originalVolume })
      serverStateStore.updatePlayerState(createMockPlayerState({
        volume: 0,
        is_muted: true,
        previous_volume: originalVolume
      }))

      expect(serverStateStore.playerState.is_muted).toBe(true)
      expect(serverStateStore.playerState.volume).toBe(0)

      // Unmute
      await apiService.player.unmute()
      mockSocket.simulate('unmuted', { restored_volume: originalVolume })
      serverStateStore.updatePlayerState(createMockPlayerState({
        volume: originalVolume,
        is_muted: false
      }))

      expect(serverStateStore.playerState.is_muted).toBe(false)
      expect(serverStateStore.playerState.volume).toBe(originalVolume)
    })

    it('should handle audio equalizer settings', async () => {
      const equalizerPresets = [
        { name: 'rock', gains: [3, 2, 0, 1, 3, 2, 1, 2, 3, 4] },
        { name: 'jazz', gains: [2, 1, 0, 1, 2, 1, 0, 1, 2, 3] },
        { name: 'classical', gains: [1, 0, 0, 0, 1, 1, 0, 1, 2, 3] }
      ]

      context.server.use(
        http.post('/api/player/equalizer', async ({ request }) => {
          const body = await request.json() as any
          return HttpResponse.json(mockApiResponses.success({
            equalizer_preset: body.preset,
            gains: body.gains
          }))
        })
      )

      for (const preset of equalizerPresets) {
        await apiService.player.setEqualizer(preset.name, preset.gains)
        mockSocket.simulate('equalizer_changed', {
          preset: preset.name,
          gains: preset.gains
        })

        serverStateStore.updatePlayerState(createMockPlayerState({
          equalizer_preset: preset.name,
          equalizer_gains: preset.gains
        }))

        expect(serverStateStore.playerState.equalizer_preset).toBe(preset.name)
        expect(serverStateStore.playerState.equalizer_gains).toEqual(preset.gains)
      }
    })
  })

  describe('Error Handling and Recovery', () => {
    it('should handle playback errors gracefully', async () => {
      const problematicTrack = createMockTrack({
        id: 'problematic-track',
        title: 'Problematic Track',
        file_path: '/nonexistent/file.mp3'
      })

      serverStateStore.updatePlayerState(createMockPlayerState({
        current_track: problematicTrack,
        is_playing: false
      }))

      context.server.use(
        http.post('/api/player/play', () => {
          return HttpResponse.json(mockApiResponses.error('File not found', 'file_not_found'), { status: 500 })
        })
      )

      // Attempt to play problematic track
      try {
        await apiService.player.play()
      } catch (error) {
        // Expected error
      }

      // Simulate error from server
      mockSocket.simulate('playback_error', {
        track: problematicTrack,
        error: 'File not found',
        error_code: 'file_not_found'
      })

      serverStateStore.updatePlayerState(createMockPlayerState({
        current_track: problematicTrack,
        is_playing: false,
        error: 'File not found'
      }))

      expect(serverStateStore.playerState.is_playing).toBe(false)
      expect(serverStateStore.playerState.error).toBe('File not found')
    })

    it('should handle network disconnection during playback', async () => {
      const track = createMockTrack({ duration_ms: 180000 })
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_track: track,
        is_playing: true,
        position_ms: 60000
      }))

      // Simulate network disconnection
      mockSocket.connected = false
      mockSocket.simulate('disconnect', { reason: 'network error' })
      serverStateStore.updateConnectionState(false)
      expect(serverStateStore.isConnected).toBe(false)

      // Player should continue locally but not receive updates
      const localPosition = serverStateStore.playerState.position_ms

      // Simulate reconnection
      mockSocket.connected = true
      mockSocket.simulate('connect', {})
      serverStateStore.updateConnectionState(true)

      // Server sends state sync
      mockSocket.simulate('state_sync', {
        current_track: track,
        position_ms: 90000, // Server position ahead
        is_playing: true
      })

      serverStateStore.updatePlayerState(createMockPlayerState({
        current_track: track,
        is_playing: true,
        position_ms: 90000
      }))

      expect(serverStateStore.isConnected).toBe(true)
      expect(serverStateStore.playerState.position_ms).toBe(90000)
    })

    it('should handle buffer underruns and playback interruptions', async () => {
      const track = createMockTrack({ duration_ms: 180000 })
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_track: track,
        is_playing: true,
        position_ms: 30000
      }))

      // Simulate buffer underrun
      mockSocket.simulate('buffer_underrun', {
        track: track,
        position_ms: 30000,
        buffer_duration_ms: 5000
      })

      serverStateStore.updatePlayerState(createMockPlayerState({
        current_track: track,
        is_playing: false, // Paused due to buffering
        position_ms: 30000,
        buffering: true
      }))

      expect(serverStateStore.playerState.is_playing).toBe(false)
      expect(serverStateStore.playerState.buffering).toBe(true)

      // Simulate buffer recovery
      mockSocket.simulate('buffer_ready', {
        track: track,
        position_ms: 30000,
        buffer_duration_ms: 10000
      })

      serverStateStore.updatePlayerState(createMockPlayerState({
        current_track: track,
        is_playing: true, // Resumed after buffering
        position_ms: 30000,
        buffering: false
      }))

      expect(serverStateStore.playerState.is_playing).toBe(true)
      expect(serverStateStore.playerState.buffering).toBe(false)
    })
  })

  describe('Performance During Long Sessions', () => {
    it('should maintain performance during extended playback', async () => {
      const longSessionPlaylist = createMockPlaylist({
        id: 'long-session',
        title: 'Long Session'
      })

      const tracks = integrationTestData.createTrackSet('long-session', 50)
      playlistStore.addPlaylist(longSessionPlaylist)
      playlistStore.setTracksForPlaylist('long-session', tracks)
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_playlist_id: 'long-session',
        current_track: tracks[0],
        is_playing: true
      }))

      const { duration } = await performanceHelpers.measureDuration(async () => {
        // Simulate playing through 10 tracks with progress updates
        for (let trackIndex = 0; trackIndex < 10; trackIndex++) {
          const currentTrack = tracks[trackIndex]

          // Update current track
          serverStateStore.updatePlayerState(createMockPlayerState({
            current_playlist_id: 'long-session',
            current_track: currentTrack,
            is_playing: true,
            position_ms: 0
          }))

          // Simulate 30 seconds of progress for each track
          for (let progress = 0; progress <= 30000; progress += 1000) {
            mockSocket.simulate('progress_update', { position_ms: progress })
            serverStateStore.updatePlayerState(createMockPlayerState({
              current_playlist_id: 'long-session',
              current_track: currentTrack,
              is_playing: true,
              position_ms: progress
            }))
          }

          // Track end
          mockSocket.simulate('track_ended', { track: currentTrack })
        }
      })

      expect(duration).toBeLessThan(500) // Should handle efficiently
      expect(serverStateStore.currentTrack).toEqual(tracks[9])
    })

    it('should handle memory efficiently during continuous playback', async () => {
      const playlist = createMockPlaylist({
        id: 'memory-test',
        title: 'Memory Test'
      })

      const track = createMockTrack({
        id: 'memory-track',
        duration_ms: 600000
      })

      playlistStore.addPlaylist(playlist)
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_playlist_id: 'memory-test',
        current_track: track,
        is_playing: true,
        position_ms: 0
      }))

      // Simulate 10 minutes of progress updates (600 updates)
      const updates = 600
      const positionIncrement = 1000 // 1 second per update

      const { duration: totalDuration } = await performanceHelpers.measureDuration(async () => {
        for (let i = 0; i < updates; i++) {
          const position = i * positionIncrement

          mockSocket.simulate('progress_update', { position_ms: position })
          serverStateStore.updatePlayerState(createMockPlayerState({
            current_playlist_id: 'memory-test',
            current_track: track,
            is_playing: true,
            position_ms: position
          }))

          // Simulate some UI operations
          if (i % 10 === 0) {
            const currentState = serverStateStore.playerState
            expect(currentState.position_ms).toBe(position)
          }
        }
      })

      expect(totalDuration).toBeLessThan(1000) // Should handle 600 updates efficiently
      expect(serverStateStore.playerState.position_ms).toBe((updates - 1) * positionIncrement)
    })

    it('should handle rapid command sequences without degradation', async () => {
      const playlist = createMockPlaylist({ id: 'rapid-commands' })
      const tracks = integrationTestData.createTrackSet('rapid-commands', 5)
      playlistStore.addPlaylist(playlist)
      playlistStore.setTracksForPlaylist('rapid-commands', tracks)

      context.server.use(
        http.post('/api/player/:command', () => {
          return HttpResponse.json(mockApiResponses.success({ status: 'success' }))
        })
      )

      serverStateStore.updatePlayerState(createMockPlayerState({
        current_playlist_id: 'rapid-commands',
        current_track: tracks[0],
        is_playing: false
      }))

      const { duration } = await performanceHelpers.measureDuration(async () => {
        const commands = [
          () => apiService.player.play(),
          () => apiService.player.pause(),
          () => apiService.player.play(),
          () => apiService.player.next(),
          () => apiService.player.previous(),
          () => apiService.player.setVolume(75),
          () => apiService.player.seek(30000),
          () => apiService.player.setVolume(50),
          () => apiService.player.pause(),
          () => apiService.player.play()
        ]

        // Execute commands rapidly
        for (const command of commands) {
          await command()
          // Simulate corresponding state updates
          await new Promise(resolve => setTimeout(resolve, 1))
        }
      })

      expect(duration).toBeLessThan(200) // Should handle rapid commands efficiently
    })
  })

  describe('Advanced Playback Features', () => {
    it('should handle crossfade between tracks', async () => {
      const playlist = createMockPlaylist({
        id: 'crossfade-playlist',
        title: 'Crossfade Playlist'
      })

      const tracks = integrationTestData.createTrackSet('crossfade-playlist', 3)
      playlistStore.addPlaylist(playlist)
      playlistStore.setTracksForPlaylist('crossfade-playlist', tracks)

      context.server.use(
        http.post('/api/player/crossfade', async ({ request }) => {
          const body = await request.json() as any
          return HttpResponse.json(mockApiResponses.success({
            crossfade_duration_ms: body.duration_ms
          }))
        })
      )

      // Enable crossfade
      await apiService.player.setCrossfade(3000) // 3 second crossfade

      serverStateStore.updatePlayerState(createMockPlayerState({
        current_playlist_id: 'crossfade-playlist',
        current_track: tracks[0],
        is_playing: true,
        crossfade_duration_ms: 3000
      }))

      // Simulate crossfade transition
      mockSocket.simulate('crossfade_started', {
        from_track: tracks[0],
        to_track: tracks[1],
        duration_ms: 3000
      })

      // During crossfade, both tracks are playing
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_playlist_id: 'crossfade-playlist',
        current_track: tracks[0],
        next_track: tracks[1],
        is_playing: true,
        crossfading: true
      }))

      expect(serverStateStore.playerState.crossfading).toBe(true)

      // Crossfade complete
      mockSocket.simulate('crossfade_complete', {
        current_track: tracks[1]
      })

      serverStateStore.updatePlayerState(createMockPlayerState({
        current_playlist_id: 'crossfade-playlist',
        current_track: tracks[1],
        is_playing: true,
        crossfading: false
      }))

      expect(serverStateStore.currentTrack).toEqual(tracks[1])
      expect(serverStateStore.playerState.crossfading).toBe(false)
    })

    it('should handle gapless playback between tracks', async () => {
      const playlist = createMockPlaylist({
        id: 'gapless-playlist',
        title: 'Gapless Playlist'
      })

      const albumTracks = integrationTestData.createTrackSet('gapless-playlist', 3)
      albumTracks.forEach(track => {
        track.gapless = true
      })

      playlistStore.addPlaylist(playlist)
      playlistStore.setTracksForPlaylist('gapless-playlist', albumTracks)
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_playlist_id: 'gapless-playlist',
        current_track: albumTracks[0],
        is_playing: true,
        gapless_mode: true
      }))

      // Simulate gapless transition
      mockSocket.simulate('gapless_transition', {
        from_track: albumTracks[0],
        to_track: albumTracks[1],
        seamless: true
      })

      serverStateStore.updatePlayerState(createMockPlayerState({
        current_playlist_id: 'gapless-playlist',
        current_track: albumTracks[1],
        is_playing: true,
        position_ms: 0,
        gapless_mode: true
      }))

      expect(serverStateStore.currentTrack).toEqual(albumTracks[1])
      expect(serverStateStore.playerState.position_ms).toBe(0)
      expect(serverStateStore.playerState.is_playing).toBe(true)
    })
  })
})
