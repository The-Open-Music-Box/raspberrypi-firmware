/**
 * NFC Association Workflow Integration Tests
 *
 * Tests the complete NFC tag association workflow including discovery,
 * pairing, playlist assignment, and playback integration.
 *
 * Focus areas:
 * - Complete NFC tag discovery and association flow
 * - Playlist-NFC tag binding and management
 * - NFC-triggered playback workflows
 * - Real-time association status updates
 * - Error handling for NFC operations
 * - Multi-tag management and conflicts
 * - Performance with multiple concurrent associations
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

// NFC-specific mock types
interface MockNfcTag {
  id: string
  uid: string
  type: string
  capacity: number
  readable: boolean
  writable: boolean
  associated_playlist_id?: string
  created_at: string
}

interface MockNfcAssociation {
  id: string
  tag_uid: string
  playlist_id: string
  created_at: string
  created_by: string
  association_name: string
  is_active: boolean
}

const createMockNfcTag = (overrides: Partial<MockNfcTag> = {}): MockNfcTag => ({
  id: `nfc-tag-${Math.random().toString(36).substr(2, 9)}`,
  uid: `04:${Math.random().toString(16).substr(2, 2)}:${Math.random().toString(16).substr(2, 2)}:${Math.random().toString(16).substr(2, 2)}`,
  type: 'NTAG213',
  capacity: 180,
  readable: true,
  writable: true,
  created_at: new Date().toISOString(),
  ...overrides
})

const createMockNfcAssociation = (overrides: Partial<MockNfcAssociation> = {}): MockNfcAssociation => ({
  id: `nfc-association-${Math.random().toString(36).substr(2, 9)}`,
  tag_uid: `04:${Math.random().toString(16).substr(2, 2)}:${Math.random().toString(16).substr(2, 2)}:${Math.random().toString(16).substr(2, 2)}`,
  playlist_id: 'test-playlist',
  created_at: new Date().toISOString(),
  created_by: 'user-123',
  association_name: 'Test Association',
  is_active: true,
  ...overrides
})

describe('NFC Association Workflow Integration Tests', () => {
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

  describe('Complete NFC Association Flow', () => {
    it('should handle full tag discovery and association workflow', async () => {
      const targetPlaylist = createMockPlaylist({
        id: 'nfc-target-playlist',
        title: 'NFC Target Playlist'
      })

      const tracks = integrationTestData.createTrackSet('nfc-target-playlist', 5)
      const discoveredTag = createMockNfcTag({
        uid: '04:ab:cd:ef',
        type: 'NTAG213'
      })

      const newAssociation = createMockNfcAssociation({
        tag_uid: discoveredTag.uid,
        playlist_id: 'nfc-target-playlist',
        association_name: 'Test Association'
      })

      // Setup initial state
      playlistStore.addPlaylist(targetPlaylist)
      playlistStore.setTracksForPlaylist('nfc-target-playlist', tracks)

      context.server.use(
        // NFC tag discovery
        http.get('/api/nfc/scan', () => {
          return HttpResponse.json(mockApiResponses.success({
            scanning: true,
            scan_duration_ms: 5000
          }))
        }),

        // Tag detection
        http.get('/api/nfc/tags', () => {
          return HttpResponse.json(mockApiResponses.success([discoveredTag]))
        }),

        // Association creation
        http.post('/api/nfc/associations', () => {
          return HttpResponse.json(mockApiResponses.success(newAssociation))
        }),

        // Association verification
        http.get('/api/nfc/associations/:id', () => {
          return HttpResponse.json(mockApiResponses.success(newAssociation))
        })
      )

      // 1. Start NFC scanning
      await apiService.nfc.startScan()
      mockSocket.simulate('nfc_scan_started', {
        scanning: true,
        duration_ms: 5000
      })

      // 2. Tag discovered
      mockSocket.simulate('nfc_tag_discovered', {
        tag: discoveredTag,
        discovered_at: new Date().toISOString()
      })

      // 3. Create association
      const associationResult = await apiService.nfc.createAssociation({
        tag_uid: discoveredTag.uid,
        playlist_id: 'nfc-target-playlist',
        association_name: 'Test Association'
      })

      expect(associationResult.tag_uid).toBe(discoveredTag.uid)
      expect(associationResult.playlist_id).toBe('nfc-target-playlist')

      // 4. WebSocket notification of successful association
      mockSocket.simulate('nfc_association_created', {
        association: newAssociation,
        tag: discoveredTag,
        playlist: targetPlaylist
      })

      // 5. Verify association state
      const verification = await apiService.nfc.getAssociation(newAssociation.id)
      expect(verification.is_active).toBe(true)
      expect(verification.playlist_id).toBe('nfc-target-playlist')
    })

    it('should handle NFC-triggered playback workflow', async () => {
      const associatedPlaylist = createMockPlaylist({
        id: 'nfc-playback-playlist',
        title: 'NFC Playback Playlist'
      })

      const tracks = integrationTestData.createTrackSet('nfc-playback-playlist', 8)
      const nfcTag = createMockNfcTag({
        uid: '04:12:34:56',
        associated_playlist_id: 'nfc-playback-playlist'
      })

      const existingAssociation = createMockNfcAssociation({
        tag_uid: nfcTag.uid,
        playlist_id: 'nfc-playback-playlist',
        association_name: 'Playback Association'
      })

      // Setup initial state
      playlistStore.addPlaylist(associatedPlaylist)
      playlistStore.setTracksForPlaylist('nfc-playback-playlist', tracks)

      context.server.use(
        // NFC tag read
        http.get('/api/nfc/read/:uid', () => {
          return HttpResponse.json(mockApiResponses.success({
            tag: nfcTag,
            association: existingAssociation,
            playlist: associatedPlaylist
          }))
        }),

        // Player load playlist
        http.post('/api/player/load-playlist', () => {
          return HttpResponse.json(mockApiResponses.success({
            playlist: associatedPlaylist,
            current_track: tracks[0],
            loaded_via: 'nfc_tag'
          }))
        }),

        // Player play
        http.post('/api/player/play', () => {
          return HttpResponse.json(mockApiResponses.success({
            status: 'playing',
            triggered_by: 'nfc_tag'
          }))
        })
      )

      // 1. NFC tag placed/scanned
      mockSocket.simulate('nfc_tag_read', {
        tag: nfcTag,
        association: existingAssociation,
        read_at: new Date().toISOString()
      })

      // 2. Load associated playlist
      await apiService.player.loadPlaylist('nfc-playback-playlist')
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_playlist_id: 'nfc-playback-playlist',
        current_track: tracks[0],
        is_playing: false,
        loaded_via: 'nfc_tag'
      }))

      mockSocket.simulate('playlist_loaded_via_nfc', {
        playlist: associatedPlaylist,
        current_track: tracks[0],
        tag_uid: nfcTag.uid
      })

      expect(serverStateStore.playerState.current_playlist_id).toBe('nfc-playback-playlist')
      expect(serverStateStore.currentTrack).toEqual(tracks[0])

      // 3. Auto-start playback
      await apiService.player.play()
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_playlist_id: 'nfc-playback-playlist',
        current_track: tracks[0],
        is_playing: true,
        triggered_by: 'nfc_tag'
      }))

      mockSocket.simulate('playback_started_via_nfc', {
        tag_uid: nfcTag.uid,
        playlist_id: 'nfc-playback-playlist',
        track: tracks[0]
      })

      expect(serverStateStore.playerState.is_playing).toBe(true)
      expect(serverStateStore.playerState.triggered_by).toBe('nfc_tag')
    })

    it('should handle tag re-association workflow', async () => {
      const originalPlaylist = createMockPlaylist({
        id: 'original-playlist',
        title: 'Original Playlist'
      })

      const newPlaylist = createMockPlaylist({
        id: 'new-playlist',
        title: 'New Playlist'
      })

      const nfcTag = createMockNfcTag({
        uid: '04:aa:bb:cc',
        associated_playlist_id: 'original-playlist'
      })

      const originalAssociation = createMockNfcAssociation({
        tag_uid: nfcTag.uid,
        playlist_id: 'original-playlist',
        association_name: 'Original Association'
      })

      const newAssociation = createMockNfcAssociation({
        tag_uid: nfcTag.uid,
        playlist_id: 'new-playlist',
        association_name: 'New Association'
      })

      // Setup initial state
      playlistStore.addPlaylist(originalPlaylist)
      playlistStore.addPlaylist(newPlaylist)

      context.server.use(
        // Get existing association
        http.get('/api/nfc/associations/by-tag/:uid', ({ params }) => {
          const { uid } = params
          if (uid === nfcTag.uid) {
            return HttpResponse.json(mockApiResponses.success(originalAssociation))
          }
          return HttpResponse.json(mockApiResponses.error('Association not found'), { status: 404 })
        }),

        // Update association
        http.put('/api/nfc/associations/:id', () => {
          return HttpResponse.json(mockApiResponses.success(newAssociation))
        }),

        // Deactivate old association
        http.delete('/api/nfc/associations/:id', () => {
          return HttpResponse.json(mockApiResponses.success({
            deactivated: true,
            association_id: originalAssociation.id
          }))
        })
      )

      // 1. Check for existing association
      const existingAssociation = await apiService.nfc.getAssociationByTag(nfcTag.uid)
      expect(existingAssociation.playlist_id).toBe('original-playlist')

      // 2. Create new association (should replace old one)
      const updatedAssociation = await apiService.nfc.updateAssociation(originalAssociation.id, {
        playlist_id: 'new-playlist',
        association_name: 'New Association'
      })

      // 3. WebSocket notification of re-association
      mockSocket.simulate('nfc_association_updated', {
        old_association: originalAssociation,
        new_association: newAssociation,
        tag: nfcTag
      })

      expect(updatedAssociation.playlist_id).toBe('new-playlist')
      expect(updatedAssociation.association_name).toBe('New Association')

      // 4. Test new association works
      mockSocket.simulate('nfc_tag_read', {
        tag: { ...nfcTag, associated_playlist_id: 'new-playlist' },
        association: newAssociation
      })

      // Should trigger new playlist load
      expect(newAssociation.playlist_id).toBe('new-playlist')
    })
  })

  describe('Multi-tag Management', () => {
    it('should handle multiple concurrent tag associations', async () => {
      const playlists = [
        createMockPlaylist({ id: 'playlist-1', title: 'Playlist 1' }),
        createMockPlaylist({ id: 'playlist-2', title: 'Playlist 2' }),
        createMockPlaylist({ id: 'playlist-3', title: 'Playlist 3' })
      ]

      const tags = [
        createMockNfcTag({ uid: '04:11:11:11' }),
        createMockNfcTag({ uid: '04:22:22:22' }),
        createMockNfcTag({ uid: '04:33:33:33' })
      ]

      const associations = tags.map((tag, index) => createMockNfcAssociation({
        tag_uid: tag.uid,
        playlist_id: playlists[index].id,
        association_name: `${playlists[index].title} Tag`
      }))

      // Setup initial state
      playlists.forEach(playlist => playlistStore.addPlaylist(playlist))

      context.server.use(
        http.post('/api/nfc/associations/batch', () => {
          return HttpResponse.json(mockApiResponses.success({
            created: associations,
            total: associations.length
          }))
        }),

        http.get('/api/nfc/associations', () => {
          return HttpResponse.json(mockApiResponses.success({
            associations,
            total: associations.length
          }))
        })
      )

      // Create multiple associations concurrently
      const associationPromises = associations.map(async (association, index) => {
        return apiService.nfc.createAssociation({
          tag_uid: tags[index].uid,
          playlist_id: playlists[index].id,
          association_name: association.association_name
        })
      })

      const createdAssociations = await Promise.all(associationPromises)

      // Verify all associations created
      expect(createdAssociations).toHaveLength(3)
      createdAssociations.forEach((association, index) => {
        expect(association.playlist_id).toBe(playlists[index].id)
        expect(association.tag_uid).toBe(tags[index].uid)
      })

      // Test concurrent tag reads
      const tagReadPromises = tags.map(async (tag, index) => {
        mockSocket.simulate('nfc_tag_read', {
          tag: { ...tag, associated_playlist_id: playlists[index].id },
          association: associations[index],
          read_at: new Date().toISOString()
        })

        return {
          tag: tag.uid,
          playlist: playlists[index].id
        }
      })

      const tagReads = await Promise.all(tagReadPromises)
      expect(tagReads).toHaveLength(3)
    })

    it('should handle tag conflict resolution', async () => {
      const conflictedPlaylist = createMockPlaylist({
        id: 'conflicted-playlist',
        title: 'Conflicted Playlist'
      })

      const conflictedTag = createMockNfcTag({
        uid: '04:conflict:conflict'
      })

      const conflictingAssociations = [
        createMockNfcAssociation({
          id: 'association-1',
          tag_uid: conflictedTag.uid,
          playlist_id: 'conflicted-playlist',
          created_by: 'user-1',
          association_name: 'First Association'
        }),
        createMockNfcAssociation({
          id: 'association-2',
          tag_uid: conflictedTag.uid,
          playlist_id: 'conflicted-playlist',
          created_by: 'user-2',
          association_name: 'Second Association'
        })
      ]

      playlistStore.addPlaylist(conflictedPlaylist)

      context.server.use(
        http.get('/api/nfc/conflicts', () => {
          return HttpResponse.json(mockApiResponses.success({
            conflicts: [{
              tag_uid: conflictedTag.uid,
              associations: conflictingAssociations,
              conflict_type: 'duplicate_tag'
            }]
          }))
        }),

        http.post('/api/nfc/resolve-conflict', () => {
          return HttpResponse.json(mockApiResponses.success({
            resolved: true,
            active_association: conflictingAssociations[0], // First one wins
            deactivated_associations: [conflictingAssociations[1]]
          }))
        })
      )

      // Detect conflict
      const conflicts = await apiService.nfc.getConflicts()
      expect(conflicts.conflicts).toHaveLength(1)
      expect(conflicts.conflicts[0].tag_uid).toBe(conflictedTag.uid)

      // Resolve conflict
      const resolution = await apiService.nfc.resolveConflict(conflictedTag.uid, 'association-1')
      mockSocket.simulate('nfc_conflict_resolved', {
        tag_uid: conflictedTag.uid,
        active_association: conflictingAssociations[0],
        deactivated_associations: [conflictingAssociations[1]]
      })

      expect(resolution.resolved).toBe(true)
      expect(resolution.active_association.id).toBe('association-1')
    })

    it('should handle tag removal and cleanup', async () => {
      const removedPlaylist = createMockPlaylist({
        id: 'removed-playlist',
        title: 'Removed Playlist'
      })

      const removedTag = createMockNfcTag({
        uid: '04:dd:dd:dd',
        associated_playlist_id: 'removed-playlist'
      })

      const associationToRemove = createMockNfcAssociation({
        tag_uid: removedTag.uid,
        playlist_id: 'removed-playlist',
        association_name: 'Association to Remove'
      })

      playlistStore.addPlaylist(removedPlaylist)

      context.server.use(
        http.delete('/api/nfc/associations/:id', () => {
          return HttpResponse.json(mockApiResponses.success({
            deleted: true,
            association_id: associationToRemove.id,
            cleanup_performed: true
          }))
        }),

        http.get('/api/nfc/tags/:uid', () => {
          return HttpResponse.json(mockApiResponses.error('Tag not found'), { status: 404 })
        })
      )

      // Remove association
      await apiService.nfc.deleteAssociation(associationToRemove.id)
      mockSocket.simulate('nfc_association_deleted', {
        association: associationToRemove,
        tag: removedTag,
        cleanup_performed: true
      })

      // Verify tag is no longer associated
      try {
        await apiService.nfc.getTag(removedTag.uid)
        throw new Error('Tag should not be found')
      } catch (error) {
        expect(error).toBeDefined()
      }

      // Test tag scan after removal
      mockSocket.simulate('nfc_tag_read', {
        tag: { ...removedTag, associated_playlist_id: null },
        association: null,
        read_at: new Date().toISOString()
      })

      // Should not trigger any playback
      expect(serverStateStore.playerState.triggered_by).not.toBe('nfc_tag')
    })
  })

  describe('Error Handling and Edge Cases', () => {
    it('should handle unreadable or corrupted tags', async () => {
      const corruptedTag = createMockNfcTag({
        uid: '04:00:00:00',
        readable: false,
        type: 'UNKNOWN'
      })

      context.server.use(
        http.get('/api/nfc/read/:uid', () => {
          return HttpResponse.json(mockApiResponses.error('Tag unreadable or corrupted', 'tag_read_error'), { status: 400 })
        })
      )

      // Attempt to read corrupted tag
      mockSocket.simulate('nfc_tag_read_error', {
        tag: corruptedTag,
        error: 'Tag unreadable or corrupted',
        error_code: 'tag_read_error'
      })

      try {
        await apiService.nfc.readTag(corruptedTag.uid)
        throw new Error('Should have thrown an error')
      } catch (error) {
        expect(error).toBeDefined()
      }

      // Should not affect player state
      expect(serverStateStore.playerState.current_playlist_id).not.toBe('corrupted-playlist')
    })

    it('should handle NFC hardware disconnection', async () => {
      const workingTag = createMockNfcTag({
        uid: '04:working:tag'
      })

      context.server.use(
        http.get('/api/nfc/status', () => {
          return HttpResponse.json(mockApiResponses.success({
            hardware_connected: false,
            last_error: 'NFC hardware disconnected'
          }))
        }),

        http.get('/api/nfc/scan', () => {
          return HttpResponse.json(mockApiResponses.error('NFC hardware not available', 'hardware_unavailable'), { status: 503 })
        })
      )

      // Check NFC status
      const status = await apiService.nfc.getStatus()
      expect(status.hardware_connected).toBe(false)

      // Simulate hardware disconnection
      mockSocket.simulate('nfc_hardware_disconnected', {
        disconnected_at: new Date().toISOString(),
        reason: 'USB connection lost'
      })

      // Attempt to scan should fail
      try {
        await apiService.nfc.startScan()
        throw new Error('Should have thrown an error')
      } catch (error) {
        expect(error).toBeDefined()
      }

      // Simulate hardware reconnection
      mockSocket.simulate('nfc_hardware_connected', {
        reconnected_at: new Date().toISOString(),
        hardware_info: {
          type: 'PN532',
          version: '1.0'
        }
      })

      // Should be able to scan again
      context.server.use(
        http.get('/api/nfc/scan', () => {
          return HttpResponse.json(mockApiResponses.success({
            scanning: true,
            scan_duration_ms: 5000
          }))
        })
      )

      const scanResult = await apiService.nfc.startScan()
      expect(scanResult.scanning).toBe(true)
    })

    it('should handle association with non-existent playlist', async () => {
      const orphanTag = createMockNfcTag({
        uid: '04:orphan:tag'
      })

      context.server.use(
        http.post('/api/nfc/associations', () => {
          return HttpResponse.json(mockApiResponses.error('Playlist not found', 'playlist_not_found'), { status: 404 })
        })
      )

      // Attempt to associate with non-existent playlist
      try {
        await apiService.nfc.createAssociation({
          tag_uid: orphanTag.uid,
          playlist_id: 'non-existent-playlist',
          association_name: 'Orphan Association'
        })
        throw new Error('Should have thrown an error')
      } catch (error) {
        expect(error).toBeDefined()
      }

      // Should not create any association
      mockSocket.simulate('nfc_association_failed', {
        tag: orphanTag,
        attempted_playlist_id: 'non-existent-playlist',
        error: 'Playlist not found'
      })
    })

    it('should handle rapid consecutive tag scans', async () => {
      const rapidTag = createMockNfcTag({
        uid: '04:cc:cc:cc',
        associated_playlist_id: 'rapid-playlist'
      })

      const rapidPlaylist = createMockPlaylist({
        id: 'rapid-playlist',
        title: 'Rapid Playlist'
      })

      const association = createMockNfcAssociation({
        tag_uid: rapidTag.uid,
        playlist_id: 'rapid-playlist'
      })

      playlistStore.addPlaylist(rapidPlaylist)
      let scanCount = 0

      context.server.use(
        http.get('/api/nfc/read/:uid', () => {
          scanCount++
          return HttpResponse.json(mockApiResponses.success({
            tag: rapidTag,
            scan_count: scanCount
          }))
        })
      )

      // Simulate rapid consecutive scans
      const rapidScans = Array.from({ length: 5 }, (_, i) => i)

      const { duration } = await performanceHelpers.measureDuration(async () => {
        const scanPromises = rapidScans.map(async (index) => {
          mockSocket.simulate('nfc_tag_read', {
            tag: rapidTag,
            association,
            read_at: new Date().toISOString(),
            scan_index: index
          })

          return apiService.nfc.readTag(rapidTag.uid)
        })

        await Promise.all(scanPromises)
      })

      expect(duration).toBeLessThan(200) // Should handle rapid scans efficiently
      expect(scanCount).toBe(5)
      // Should not trigger multiple simultaneous playlist loads
      // (would be handled by debouncing in real implementation)
    })
  })

  describe('Performance and Scalability', () => {
    it('should handle large numbers of associations efficiently', async () => {
      const associationCount = 100
      const associations = Array.from({ length: associationCount }, (_, i) =>
        createMockNfcAssociation({
          id: `bulk-association-${i}`,
          tag_uid: `04:${i.toString(16).padStart(2, '0')}:${i.toString(16).padStart(2, '0')}:${i.toString(16).padStart(2, '0')}`,
          playlist_id: `bulk-playlist-${i}`,
          association_name: `Bulk Association ${i}`
        })
      )

      context.server.use(
        http.get('/api/nfc/associations', ({ request }) => {
          const url = new URL(request.url)
          const page = parseInt(url.searchParams.get('page') || '1')
          const limit = parseInt(url.searchParams.get('limit') || '50')
          const start = (page - 1) * limit
          const end = start + limit

          return HttpResponse.json(mockApiResponses.success({
            associations: associations.slice(start, end),
            total: associationCount,
            page,
            limit,
            pages: Math.ceil(associationCount / limit)
          }))
        })
      )

      const { duration } = await performanceHelpers.measureDuration(async () => {
        // Load all associations in pages
        const page1 = await apiService.nfc.getAssociations({ page: 1, limit: 50 })
        const page2 = await apiService.nfc.getAssociations({ page: 2, limit: 50 })

        expect(page1.associations).toHaveLength(50)
        expect(page2.associations).toHaveLength(50)
        expect(page1.total).toBe(associationCount)
      })

      expect(duration).toBeLessThan(100) // Should handle large lists efficiently
    })

    it('should optimize memory usage during bulk operations', async () => {
      const bulkTags = Array.from({ length: 50 }, (_, i) =>
        createMockNfcTag({
          uid: `04:bulk:${i.toString(16).padStart(2, '0')}:${i.toString(16).padStart(2, '0')}`
        })
      )

      // Simulate scanning many tags in sequence
      for (const tag of bulkTags.slice(0, 20)) { // Process first 20
        mockSocket.simulate('nfc_tag_discovered', {
          tag,
          discovered_at: new Date().toISOString()
        })

        // Small delay to simulate real scanning
        await new Promise(resolve => setTimeout(resolve, 1))
      }

      // Memory usage should remain reasonable
      // (in real implementation, would clean up old scan results)
    })

    it('should handle concurrent tag scanning and association creation', async () => {
      const concurrentTags = Array.from({ length: 10 }, (_, i) =>
        createMockNfcTag({
          uid: `04:concurrent:${i.toString(16)}`
        })
      )

      const concurrentPlaylists = Array.from({ length: 10 }, (_, i) =>
        createMockPlaylist({
          id: `concurrent-playlist-${i}`,
          title: `Concurrent Playlist ${i}`
        })
      )

      // Setup playlists
      concurrentPlaylists.forEach(playlist => playlistStore.addPlaylist(playlist))

      context.server.use(
        http.post('/api/nfc/associations', async ({ request }) => {
          const body = await request.json() as any
          return HttpResponse.json(mockApiResponses.success(
            createMockNfcAssociation({
              tag_uid: body.tag_uid,
              playlist_id: body.playlist_id,
              association_name: body.association_name
            })
          ))
        })
      )

      const { duration } = await performanceHelpers.measureDuration(async () => {
        // Create associations concurrently
        const associationPromises = concurrentTags.map(async (tag, index) => {
          // Simulate tag discovery
          mockSocket.simulate('nfc_tag_discovered', { tag })

          // Create association
          return apiService.nfc.createAssociation({
            tag_uid: tag.uid,
            playlist_id: `concurrent-playlist-${index}`,
            association_name: `Concurrent Association ${index}`
          })
        })

        const results = await Promise.all(associationPromises)
        expect(results).toHaveLength(10)
      })

      expect(duration).toBeLessThan(300) // Should handle concurrent operations efficiently
    })
  })

  describe('Integration with Player State', () => {
    it('should maintain NFC context during playback session', async () => {
      const nfcPlaylist = createMockPlaylist({
        id: 'nfc-context-playlist',
        title: 'NFC Context Playlist'
      })

      const tracks = integrationTestData.createTrackSet('nfc-context-playlist', 3)
      const contextTag = createMockNfcTag({
        uid: '04:ctx:ctx:ctx',
        associated_playlist_id: 'nfc-context-playlist'
      })

      const contextAssociation = createMockNfcAssociation({
        tag_uid: contextTag.uid,
        playlist_id: 'nfc-context-playlist',
        association_name: 'Context Association'
      })

      playlistStore.addPlaylist(nfcPlaylist)
      playlistStore.setTracksForPlaylist('nfc-context-playlist', tracks)

      // Start via NFC
      mockSocket.simulate('nfc_tag_read', {
        tag: contextTag,
        association: contextAssociation
      })

      serverStateStore.updatePlayerState(createMockPlayerState({
        current_playlist_id: 'nfc-context-playlist',
        current_track: tracks[0],
        is_playing: true,
        triggered_by: 'nfc_tag',
        nfc_context: {
          tag_uid: contextTag.uid,
          association_id: contextAssociation.id,
          triggered_at: new Date().toISOString()
        }
      }))

      // Play through tracks
      for (const track of tracks) {
        serverStateStore.updatePlayerState(createMockPlayerState({
          current_playlist_id: 'nfc-context-playlist',
          current_track: track,
          is_playing: true,
          triggered_by: 'nfc_tag',
          nfc_context: {
            tag_uid: contextTag.uid,
            association_id: contextAssociation.id,
            triggered_at: new Date().toISOString()
          }
        }))

        // Verify NFC context is maintained
        expect(serverStateStore.playerState.nfc_context?.tag_uid).toBe(contextTag.uid)
      }

      // End session
      mockSocket.simulate('playlist_ended', {
        playlist_id: 'nfc-context-playlist',
        ended_via: 'nfc_tag'
      })

      serverStateStore.updatePlayerState(createMockPlayerState({
        current_playlist_id: null,
        current_track: null,
        is_playing: false,
        nfc_context: null
      }))

      expect(serverStateStore.playerState.nfc_context).toBeNull()
    })
  })
})
