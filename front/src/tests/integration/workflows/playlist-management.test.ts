/**
 * Playlist Management Workflow Integration Tests
 *
 * Tests the complete playlist management workflows including creation, modification,
 * track management, and cross-store synchronization.
 *
 * Focus areas:
 * - Complete playlist lifecycle (CRUD operations)
 * - Track management within playlists
 * - Playlist-player integration
 * - Real-time synchronization across stores
 * - Bulk operations and performance
 * - Playlist sharing and collaboration
 * - Search and filtering workflows
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { http, HttpResponse } from 'msw'
import { useUnifiedPlaylistStore } from '@/stores/unifiedPlaylistStore'
import { useServerStateStore } from '@/stores/serverStateStore'
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
  createMockPlaylist,
  createMockTrack,
  createMockPlayerState
} from '@/tests/utils/testHelpers'

describe('Playlist Management Workflow Integration Tests', () => {
  let context: IntegrationTestContext
  let playlistStore: ReturnType<typeof useUnifiedPlaylistStore>
  let serverStateStore: ReturnType<typeof useServerStateStore>
  let mockSocket: ReturnType<typeof websocketMocks.createMockSocket>

  beforeEach(() => {
    context = setupIntegrationTest()
    playlistStore = useUnifiedPlaylistStore()
    serverStateStore = useServerStateStore()
    mockSocket = websocketMocks.createMockSocket()
  })

  afterEach(() => {
    cleanupHelpers.fullCleanup(context)
  })

  describe('Playlist Lifecycle Management', () => {
    it('should handle complete playlist creation workflow', async () => {
      const newPlaylistData = {
        title: 'New Workflow Playlist',
        description: 'Created through workflow test',
        is_public: false
      }

      const createdPlaylist = createMockPlaylist({
        id: 'workflow-playlist-1',
        ...newPlaylistData,
        created_at: new Date().toISOString()
      })

      context.server.use(
        http.post('/api/playlists', () => {
          return HttpResponse.json(mockApiResponses.success(createdPlaylist))
        }),
        http.get('/api/playlists/workflow-playlist-1', () => {
          return HttpResponse.json(mockApiResponses.success(createdPlaylist))
        })
      )

      // 1. Create playlist via API
      const result = await apiService.playlists.create(newPlaylistData)
      expect(result.id).toBe('workflow-playlist-1')

      // 2. Add to store
      playlistStore.addPlaylist(result)

      // 3. Simulate WebSocket notification
      mockSocket.simulate('playlist_created', {
        playlist: createdPlaylist,
        creator_id: 'user-123'
      })

      // 4. Verify state
      const storedPlaylist = playlistStore.getPlaylist('workflow-playlist-1')
      expect(storedPlaylist).toEqual(createdPlaylist)
      expect(playlistStore.playlists).toContainEqual(createdPlaylist)
    })

    it('should handle playlist update workflow', async () => {
      const originalPlaylist = createMockPlaylist({
        id: 'update-playlist',
        title: 'Original Title',
        description: 'Original Description',
        is_public: false
      })

      const updatedData = {
        title: 'Updated Title',
        description: 'Updated Description',
        is_public: true
      }

      const updatedPlaylist = { ...originalPlaylist, ...updatedData }

      // Setup initial state
      playlistStore.addPlaylist(originalPlaylist)

      context.server.use(
        http.put('/api/playlists/update-playlist', () => {
          return HttpResponse.json(mockApiResponses.success(updatedPlaylist))
        })
      )

      // 1. Update via API
      const result = await apiService.playlists.update('update-playlist', updatedData)

      // 2. Update store
      playlistStore.updatePlaylist(result)

      // 3. Simulate WebSocket notification
      mockSocket.simulate('playlist_updated', {
        playlist: updatedPlaylist,
        changes: updatedData
      })

      // 4. Verify state
      const storedPlaylist = playlistStore.getPlaylist('update-playlist')
      expect(storedPlaylist?.title).toBe('Updated Title')
      expect(storedPlaylist?.description).toBe('Updated Description')
      expect(storedPlaylist?.is_public).toBe(true)
    })

    it('should handle playlist deletion workflow', async () => {
      const playlistToDelete = createMockPlaylist({
        id: 'delete-playlist',
        title: 'To Be Deleted'
      })

      const tracks = integrationTestData.createTrackSet('delete-playlist', 3)

      // Setup initial state
      playlistStore.addPlaylist(playlistToDelete)
      playlistStore.setTracks('delete-playlist', tracks)

      context.server.use(
        http.delete('/api/playlists/delete-playlist', () => {
          return HttpResponse.json(mockApiResponses.success({
            deleted: true,
            playlist_id: 'delete-playlist'
          }))
        })
      )

      // 1. Delete via API
      await apiService.playlists.delete('delete-playlist')

      // 2. Remove from store
      playlistStore.removePlaylist('delete-playlist')

      // 3. Simulate WebSocket notification
      mockSocket.simulate('playlist_deleted', {
        playlist_id: 'delete-playlist',
        deleted_by: 'user-123'
      })

      // 4. Verify removal
      const deletedPlaylist = playlistStore.getPlaylist('delete-playlist')
      expect(deletedPlaylist).toBeUndefined()
      expect(playlistStore.getTracksForPlaylist('delete-playlist')).toHaveLength(0)
    })

    it('should handle playlist duplication workflow', async () => {
      const sourcePlaylist = createMockPlaylist({
        id: 'source-playlist',
        title: 'Source Playlist'
      })

      const sourceTracks = integrationTestData.createTrackSet('source-playlist', 5)

      const duplicatedPlaylist = createMockPlaylist({
        id: 'duplicated-playlist',
        title: 'Copy of Source Playlist',
        track_count: 5
      })

      // Setup initial state
      playlistStore.addPlaylist(sourcePlaylist)
      playlistStore.setTracks('source-playlist', sourceTracks)

      context.server.use(
        http.post('/api/playlists/source-playlist/duplicate', () => {
          return HttpResponse.json(mockApiResponses.success({
            original_playlist: sourcePlaylist,
            duplicated_playlist: duplicatedPlaylist,
            tracks_copied: sourceTracks.length
          }))
        }),
        http.get('/api/playlists/duplicated-playlist/tracks', () => {
          return HttpResponse.json(mockApiResponses.success(sourceTracks))
        })
      )

      // 1. Duplicate via API
      const result = await apiService.playlists.duplicate('source-playlist')

      // 2. Add duplicated playlist to store
      playlistStore.addPlaylist(result.duplicated_playlist)
      playlistStore.setTracks('duplicated-playlist', sourceTracks)

      // 3. Simulate WebSocket notification
      mockSocket.simulate('playlist_duplicated', {
        source_playlist: sourcePlaylist,
        new_playlist: duplicatedPlaylist,
        tracks_copied: sourceTracks.length
      })

      // 4. Verify duplication
      const duplicated = playlistStore.getPlaylist('duplicated-playlist')
      expect(duplicated).toBeDefined()
      expect(duplicated?.title).toBe('Copy of Source Playlist')

      const duplicatedTracks = playlistStore.getTracksForPlaylist('duplicated-playlist')
      expect(duplicatedTracks).toHaveLength(5)
      expect(duplicatedTracks).toEqual(sourceTracks)
    })
  })

  describe('Track Management Workflows', () => {
    it('should handle adding tracks to playlist workflow', async () => {
      const playlist = createMockPlaylist({
        id: 'add-tracks-playlist',
        title: 'Add Tracks Test'
      })

      const newTrack = createMockTrack({
        id: 'new-track-1',
        title: 'New Track to Add',
        track_number: 1
      })

      playlistStore.addPlaylist(playlist)

      context.server.use(
        http.post('/api/playlists/add-tracks-playlist/tracks', () => {
          return HttpResponse.json(mockApiResponses.success({
            track: newTrack,
            position: 1,
            playlist_track_count: 1
          }))
        })
      )

      // 1. Add track via API
      const result = await apiService.playlists.addTrack('add-tracks-playlist', 'new-track-1')

      // 2. Add to store
      playlistStore.addTrackToPlaylist('add-tracks-playlist', newTrack)

      // 3. Simulate WebSocket notification
      mockSocket.simulate('track_added_to_playlist', {
        playlist_id: 'add-tracks-playlist',
        track: newTrack,
        position: 1
      })

      // 4. Verify addition
      const playlistTracks = playlistStore.getTracksForPlaylist('add-tracks-playlist')
      expect(playlistTracks).toContainEqual(newTrack)
      expect(playlistTracks).toHaveLength(1)
    })

    it('should handle removing tracks from playlist workflow', async () => {
      const playlist = createMockPlaylist({
        id: 'remove-tracks-playlist',
        title: 'Remove Tracks Test'
      })

      const tracks = integrationTestData.createTrackSet('remove-tracks-playlist', 3)
      const trackToRemove = tracks[1] // Remove middle track

      // Setup initial state
      playlistStore.addPlaylist(playlist)
      playlistStore.setTracks('remove-tracks-playlist', tracks)

      context.server.use(
        http.delete('/api/playlists/remove-tracks-playlist/tracks/track-2', () => {
          return HttpResponse.json(mockApiResponses.success({
            removed: true,
            track_id: 'track-2',
            playlist_track_count: 2
          }))
        })
      )

      // 1. Remove track via API
      await apiService.playlists.removeTrack('remove-tracks-playlist', trackToRemove.id)

      // 2. Remove from store
      playlistStore.removeTrackFromPlaylist('remove-tracks-playlist', trackToRemove.id)

      // 3. Simulate WebSocket notification
      mockSocket.simulate('track_removed_from_playlist', {
        playlist_id: 'remove-tracks-playlist',
        track_id: trackToRemove.id,
        removed_position: 2
      })

      // 4. Verify removal
      const remainingTracks = playlistStore.getTracksForPlaylist('remove-tracks-playlist')
      expect(remainingTracks).toHaveLength(2)
      expect(remainingTracks.find(t => t.id === trackToRemove.id)).toBeUndefined()
    })

    it('should handle track reordering workflow', async () => {
      const playlist = createMockPlaylist({
        id: 'reorder-playlist',
        title: 'Reorder Test'
      })

      const originalTracks = integrationTestData.createTrackSet('reorder-playlist', 5)
      const reorderedTracks = [
        originalTracks[2], // Track 3 -> Position 1
        originalTracks[0], // Track 1 -> Position 2
        originalTracks[4], // Track 5 -> Position 3
        originalTracks[1], // Track 2 -> Position 4
        originalTracks[3]  // Track 4 -> Position 5
      ]

      // Setup initial state
      playlistStore.addPlaylist(playlist)
      playlistStore.setTracks('reorder-playlist', originalTracks)

      context.server.use(
        http.put('/api/playlists/reorder-playlist/reorder', () => {
          return HttpResponse.json(mockApiResponses.success({
            playlist_id: 'reorder-playlist',
            new_order: reorderedTracks.map(t => t.id),
            updated_tracks: reorderedTracks
          }))
        })
      )

      // 1. Reorder via API
      const newOrder = reorderedTracks.map(t => t.id)
      await apiService.playlists.reorderTracks('reorder-playlist', newOrder)

      // 2. Update store
      playlistStore.reorderTracks('reorder-playlist', reorderedTracks)

      // 3. Simulate WebSocket notification
      mockSocket.simulate('playlist_tracks_reordered', {
        playlist_id: 'reorder-playlist',
        new_track_order: newOrder
      })

      // 4. Verify reordering
      const orderedTracks = playlistStore.getTracksForPlaylist('reorder-playlist')
      expect(orderedTracks).toEqual(reorderedTracks)
      expect(orderedTracks[0].id).toBe(originalTracks[2].id)
      expect(orderedTracks[1].id).toBe(originalTracks[0].id)
    })

    it('should handle bulk track operations workflow', async () => {
      const sourcePlaylist = createMockPlaylist({
        id: 'source-bulk',
        title: 'Source Bulk'
      })

      const targetPlaylist = createMockPlaylist({
        id: 'target-bulk',
        title: 'Target Bulk'
      })

      const sourceTracks = integrationTestData.createTrackSet('source-bulk', 10)
      const tracksToMove = sourceTracks.slice(2, 7) // Move tracks 3-7

      // Setup initial state
      playlistStore.addPlaylist(sourcePlaylist)
      playlistStore.addPlaylist(targetPlaylist)
      playlistStore.setTracks('source-bulk', sourceTracks)
      playlistStore.setTracks('target-bulk', [])

      context.server.use(
        http.post('/api/playlists/bulk-operations', () => {
          return HttpResponse.json(mockApiResponses.success({
            operation: 'move_tracks',
            source_playlist: 'source-bulk',
            target_playlist: 'target-bulk',
            tracks_moved: tracksToMove.length,
            track_ids: tracksToMove.map(t => t.id)
          }))
        })
      )

      // 1. Bulk move via API
      const trackIds = tracksToMove.map(t => t.id)
      await apiService.playlists.bulkMoveTracksToPlaylist('source-bulk', 'target-bulk', trackIds)

      // 2. Update stores
      tracksToMove.forEach(track => {
        playlistStore.removeTrackFromPlaylist('source-bulk', track.id)
        playlistStore.addTrackToPlaylist('target-bulk', track)
      })

      // 3. Simulate WebSocket notification
      mockSocket.simulate('bulk_tracks_moved', {
        source_playlist: 'source-bulk',
        target_playlist: 'target-bulk',
        moved_tracks: tracksToMove
      })

      // 4. Verify bulk operation
      const remainingSourceTracks = playlistStore.getTracksForPlaylist('source-bulk')
      const targetTracks = playlistStore.getTracksForPlaylist('target-bulk')

      expect(remainingSourceTracks).toHaveLength(5) // 10 - 5 moved
      expect(targetTracks).toHaveLength(5)
      expect(targetTracks).toEqual(tracksToMove)
    })
  })

  describe('Playlist-Player Integration', () => {
    it('should handle playlist loading in player workflow', async () => {
      const playlist = createMockPlaylist({
        id: 'player-playlist',
        title: 'Player Test'
      })

      const tracks = integrationTestData.createTrackSet('player-playlist', 8)
      const firstTrack = tracks[0]

      // Setup initial state
      playlistStore.addPlaylist(playlist)
      playlistStore.setTracks('player-playlist', tracks)

      context.server.use(
        http.post('/api/player/load-playlist', () => {
          return HttpResponse.json(mockApiResponses.success({
            playlist_loaded: playlist,
            current_track: firstTrack,
            track_count: tracks.length
          }))
        })
      )

      // 1. Load playlist in player via API
      await apiService.player.loadPlaylist('player-playlist')

      // 2. Update player state
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_playlist_id: 'player-playlist',
        current_track: firstTrack,
        is_playing: false
      }))

      // 3. Simulate WebSocket notification
      mockSocket.simulate('playlist_loaded_in_player', {
        playlist: playlist,
        current_track: firstTrack,
        total_tracks: tracks.length
      })

      // 4. Verify player-playlist integration
      expect(serverStateStore.playerState.current_playlist_id).toBe('player-playlist')
      expect(serverStateStore.currentTrack).toEqual(firstTrack)

      const loadedPlaylist = playlistStore.getPlaylist('player-playlist')
      expect(loadedPlaylist).toEqual(playlist)
    })

    it('should handle track navigation affecting playlist state', async () => {
      const playlist = createMockPlaylist({
        id: 'navigation-playlist',
        title: 'Navigation Test'
      })

      const tracks = integrationTestData.createTrackSet('navigation-playlist', 5)

      // Setup initial state
      playlistStore.addPlaylist(playlist)
      playlistStore.setTracks('navigation-playlist', tracks)
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_playlist_id: 'navigation-playlist',
        current_track: tracks[0]
      }))

      context.server.use(
        http.post('/api/player/next', () => {
          return HttpResponse.json(mockApiResponses.success({
            current_track: tracks[1],
            track_position: 2
          }))
        })
      )

      // 1. Navigate to next track
      await apiService.player.next()

      // 2. Update player state
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_playlist_id: 'navigation-playlist',
        current_track: tracks[1]
      }))

      // 3. Simulate WebSocket notification
      mockSocket.simulate('track_changed', {
        playlist_id: 'navigation-playlist',
        current_track: tracks[1],
        previous_track: tracks[0],
        track_position: 2
      })

      // 4. Verify navigation state
      expect(serverStateStore.currentTrack).toEqual(tracks[1])
      expect(serverStateStore.playerState.current_playlist_id).toBe('navigation-playlist')

      // Playlist state should remain consistent
      const playlistTracks = playlistStore.getTracksForPlaylist('navigation-playlist')
      expect(playlistTracks).toHaveLength(5)
      expect(playlistTracks[1]).toEqual(tracks[1])
    })

    it('should handle shuffle mode affecting track order', async () => {
      const playlist = createMockPlaylist({
        id: 'shuffle-playlist',
        title: 'Shuffle Test'
      })

      const tracks = integrationTestData.createTrackSet('shuffle-playlist', 10)
      const shuffledOrder = [...tracks].sort(() => Math.random() - 0.5)

      playlistStore.addPlaylist(playlist)
      playlistStore.setTracks('shuffle-playlist', tracks)

      context.server.use(
        http.post('/api/player/shuffle', () => {
          return HttpResponse.json(mockApiResponses.success({
            shuffle_enabled: true,
            shuffled_order: shuffledOrder.map(t => t.id)
          }))
        })
      )

      // 1. Enable shuffle mode
      await apiService.player.toggleShuffle(true)

      // 2. Update player state
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_playlist_id: 'shuffle-playlist',
        shuffle_enabled: true
      }))

      // 3. Simulate WebSocket notification
      mockSocket.simulate('shuffle_toggled', {
        playlist_id: 'shuffle-playlist',
        shuffle_enabled: true,
        shuffled_order: shuffledOrder.map(t => t.id)
      })

      // 4. Verify shuffle state
      expect(serverStateStore.playerState.shuffle_enabled).toBe(true)

      // Original playlist order should remain unchanged
      const originalTracks = playlistStore.getTracksForPlaylist('shuffle-playlist')
      expect(originalTracks).toEqual(tracks) // Original order preserved
    })
  })

  describe('Real-time Synchronization', () => {
    it('should handle collaborative playlist editing', async () => {
      const sharedPlaylist = createMockPlaylist({
        id: 'collaborative-playlist',
        title: 'Shared Playlist',
        is_public: true
      })

      const originalTracks = integrationTestData.createTrackSet('collaborative-playlist', 3)
      const newTrackFromOtherUser = createMockTrack({
        id: 'external-track',
        title: 'Added by Another User',
        track_number: 4
      })

      // Setup initial state
      playlistStore.addPlaylist(sharedPlaylist)
      playlistStore.setTracks('collaborative-playlist', originalTracks)

      // Simulate another user adding a track
      mockSocket.simulate('external_track_added', {
        playlist_id: 'collaborative-playlist',
        track: newTrackFromOtherUser,
        added_by: 'user-456',
        position: 4
      })

      // Update local state
      playlistStore.addTrackToPlaylist('collaborative-playlist', newTrackFromOtherUser)

      // Verify collaborative update
      const updatedTracks = playlistStore.getTracksForPlaylist('collaborative-playlist')
      expect(updatedTracks).toHaveLength(4)
      expect(updatedTracks).toContainEqual(newTrackFromOtherUser)
    })

    it('should handle conflict resolution in collaborative editing', async () => {
      const playlist = createMockPlaylist({
        id: 'conflict-playlist',
        title: 'Conflict Test'
      })

      const originalTracks = integrationTestData.createTrackSet('conflict-playlist', 5)
      playlistStore.addPlaylist(playlist)
      playlistStore.setTracks('conflict-playlist', originalTracks)

      // Simulate concurrent modifications
      const localReorder = [originalTracks[1], originalTracks[0], ...originalTracks.slice(2)]
      const serverReorder = [originalTracks[2], originalTracks[0], originalTracks[1], ...originalTracks.slice(3)]

      // Local change first
      playlistStore.reorderTracks('conflict-playlist', localReorder)

      // Server sends conflicting change
      mockSocket.simulate('playlist_conflict_resolution', {
        playlist_id: 'conflict-playlist',
        server_version: serverReorder,
        conflict_type: 'track_order',
        resolution: 'server_wins'
      })

      // Apply server resolution
      playlistStore.reorderTracks('conflict-playlist', serverReorder)

      // Verify conflict resolution
      const resolvedTracks = playlistStore.getTracksForPlaylist('conflict-playlist')
      expect(resolvedTracks).toEqual(serverReorder)
    })

    it('should handle real-time playlist metadata updates', async () => {
      const playlist = createMockPlaylist({
        id: 'realtime-playlist',
        title: 'Original Title',
        description: 'Original Description'
      })

      playlistStore.addPlaylist(playlist)

      // Simulate real-time metadata updates
      const updates = [
        { title: 'Updated Title 1' },
        { description: 'Updated Description' },
        { title: 'Final Title', is_public: true }
      ]

      for (const update of updates) {
        mockSocket.simulate('playlist_metadata_updated', {
          playlist_id: 'realtime-playlist',
          updates: update,
          updated_by: 'user-456'
        })

        playlistStore.updatePlaylist({ ...playlist, ...update })
      }

      // Verify final state
      const updatedPlaylist = playlistStore.getPlaylist('realtime-playlist')
      expect(updatedPlaylist?.title).toBe('Final Title')
      expect(updatedPlaylist?.description).toBe('Updated Description')
      expect(updatedPlaylist?.is_public).toBe(true)
    })
  })

  describe('Search and Filtering Workflows', () => {
    it('should handle playlist search workflow', async () => {
      const playlists = integrationTestData.createPlaylistSet(20)
      const searchTerm = 'rock'
      const matchingPlaylists = playlists.filter(p =>
        p.title.toLowerCase().includes(searchTerm.toLowerCase())
      )

      // Setup initial state
      playlists.forEach(playlist => playlistStore.addPlaylist(playlist))

      context.server.use(
        http.get('/api/playlists/search', ({ request }) => {
          const url = new URL(request.url)
          const query = url.searchParams.get('q')

          if (query === searchTerm) {
            return HttpResponse.json(mockApiResponses.success({
              results: matchingPlaylists,
              total: matchingPlaylists.length,
              query: searchTerm
            }))
          }
          return HttpResponse.json(mockApiResponses.success({
            results: [],
            total: 0
          }))
        })
      )

      // 1. Perform search
      const searchResult = await apiService.playlists.search(searchTerm)

      // 2. Update store with filtered results
      playlistStore.setSearchResults(searchResult.results)

      // 3. Verify search results
      expect(searchResult.results).toEqual(matchingPlaylists)
      expect(playlistStore.searchResults).toEqual(matchingPlaylists)
    })

    it('should handle advanced filtering workflow', async () => {
      const playlists = integrationTestData.createPlaylistSet(15)

      // Setup initial state
      playlists.forEach(playlist => playlistStore.addPlaylist(playlist))

      const filters = {
        is_public: true,
        min_track_count: 5,
        created_after: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(), // Last week
        genre: 'electronic'
      }

      context.server.use(
        http.get('/api/playlists/filter', () => {
          const filteredPlaylists = playlists.filter(p =>
            p.is_public === filters.is_public &&
            p.track_count >= filters.min_track_count
          )

          return HttpResponse.json(mockApiResponses.success({
            results: filteredPlaylists,
            filters_applied: filters,
            total: filteredPlaylists.length
          }))
        })
      )

      // 1. Apply filters
      const filterResult = await apiService.playlists.filter(filters)

      // 2. Update store
      playlistStore.setFilteredResults(filterResult.results)

      // 3. Verify filtering
      expect(filterResult.results.every(p => p.is_public)).toBe(true)
      expect(filterResult.results.every(p => p.track_count >= 5)).toBe(true)
    })

    it('should handle tag-based organization workflow', async () => {
      const playlist = createMockPlaylist({
        id: 'tagged-playlist',
        title: 'Tagged Playlist',
        tags: ['rock', 'classic']
      })

      playlistStore.addPlaylist(playlist)

      const newTags = ['motivation', 'gym']
      const updatedPlaylist = {
        ...playlist,
        tags: [...playlist.tags, ...newTags]
      }

      context.server.use(
        http.put('/api/playlists/tagged-playlist/tags', () => {
          return HttpResponse.json(mockApiResponses.success({
            playlist: updatedPlaylist,
            tags_added: newTags
          }))
        })
      )

      // 1. Add tags via API
      await apiService.playlists.addTags('tagged-playlist', newTags)

      // 2. Update store
      playlistStore.updatePlaylist(updatedPlaylist)

      // 3. Simulate WebSocket notification
      mockSocket.simulate('playlist_tags_updated', {
        playlist_id: 'tagged-playlist',
        new_tags: newTags,
        all_tags: updatedPlaylist.tags
      })

      // 4. Verify tag management
      const taggedPlaylist = playlistStore.getPlaylist('tagged-playlist')
      expect(taggedPlaylist?.tags).toContain('motivation')
      expect(taggedPlaylist?.tags).toContain('gym')
      expect(taggedPlaylist?.tags).toHaveLength(4)
    })
  })

  describe('Performance and Bulk Operations', () => {
    it('should handle large playlist operations efficiently', async () => {
      const largePlaylist = createMockPlaylist({
        id: 'large-playlist',
        title: 'Large Playlist',
        track_count: 1000
      })

      const largeBatch = Array.from({ length: 1000 }, (_, i) =>
        createMockTrack({
          id: `track-${i}`,
          track_number: i + 1,
          title: `Track ${i + 1}`
        })
      )

      playlistStore.addPlaylist(largePlaylist)

      const { duration } = await performanceHelpers.measureDuration(async () => {
        // Simulate batch track loading
        playlistStore.setTracks('large-playlist', largeBatch)

        // Simulate bulk operations
        const reorderedBatch = largeBatch.reverse()
        playlistStore.reorderTracks('large-playlist', reorderedBatch)
      })

      expect(duration).toBeLessThan(100) // Should handle 1000 tracks efficiently

      const loadedTracks = playlistStore.getTracksForPlaylist('large-playlist')
      expect(loadedTracks).toHaveLength(1000)
      expect(loadedTracks[0].track_number).toBe(1000) // Reversed order
    })

    it('should optimize memory usage during intensive operations', async () => {
      const playlistCount = 100
      const playlists = Array.from({ length: playlistCount }, (_, i) =>
        createMockPlaylist({
          id: `memory-playlist-${i}`,
          title: `Memory Test Playlist ${i}`
        })
      )

      // Add all playlists
      playlists.forEach(playlist => {
        playlistStore.addPlaylist(playlist)

        // Add tracks for each playlist
        const tracks = integrationTestData.createTrackSet(playlist.id, 10)
        playlistStore.setTracks(playlist.id, tracks)
      })

      // Perform operations
      for (let i = 0; i < 50; i++) {
        const playlistId = `memory-playlist-${i}`

        // Update playlist
        playlistStore.updatePlaylist({
          ...playlists[i],
          title: `Updated ${playlists[i].title}`
        })

        // Reorder tracks
        const tracks = playlistStore.getTracksForPlaylist(playlistId)
        playlistStore.reorderTracks(playlistId, tracks.reverse())
      }

      // Verify state consistency
      expect(playlistStore.playlists).toHaveLength(playlistCount)

      // Check a few random playlists
      const randomPlaylist = playlistStore.getPlaylist('memory-playlist-25')
      expect(randomPlaylist?.title).toContain('Updated')

      const randomTracks = playlistStore.getTracksForPlaylist('memory-playlist-25')
      expect(randomTracks).toHaveLength(10)
    })
  })
})
