/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-non-null-assertion */
/**
 * Unified Playlist Store
 * 
 * Single source of truth for all playlist and track data.
 * Centralizes WebSocket management and eliminates data source conflicts.
 */

import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { PlayList, Track } from '@/components/files/types'
import { logger } from '@/utils/logger'
import socketService from '@/services/socketService'
import { SOCKET_EVENTS } from '@/constants/apiRoutes'
import apiService from '@/services/apiService'
import {
  filterTrackByNumber,
  filterTracksByNumbers,
  validateTracksForDrag,
  createTrackIndexMap,
  findTrackByNumberSafe,
  getTrackNumber
} from '@/utils/trackFieldAccessor'
import { handleDragError, DragContext } from '@/utils/dragOperationErrorHandler'

// Note: Interface kept for documentation but not used in implementation

export const useUnifiedPlaylistStore = defineStore('unifiedPlaylist', () => {
  // === STATE ===
  const playlists = ref<Map<string, PlayList>>(new Map())
  const tracks = ref<Map<string, Track[]>>(new Map())
  // Performance optimization: Track index maps for O(1) lookups
  const trackIndexMaps = ref<Map<string, Map<number, Track>>>(new Map())
  const isLoading = ref<boolean>(false)
  const error = ref<string | null>(null)
  const lastSync = ref<number>(0)
  const isInitialized = ref<boolean>(false)
  
  // Track ongoing drag operations to prevent WebSocket conflicts
  const ongoingDragOperations = ref<Set<string>>(new Set())

  // === GETTERS ===
  const getAllPlaylists = computed<PlayList[]>(() => {
    return Array.from(playlists.value.values())
  })

  const getPlaylistById = computed(() => {
    return (id: string): PlayList | undefined => {
      return playlists.value.get(id)
    }
  })

  const getPlaylistWithTracks = computed(() => {
    return (id: string): PlayList | undefined => {
      const playlist = playlists.value.get(id)
      if (!playlist) return undefined

      return {
        ...playlist,
        tracks: tracks.value.get(id) || []
      }
    }
  })

  const getTracksForPlaylist = computed(() => {
    return (id: string): Track[] => {
      return tracks.value.get(id) || []
    }
  })

  const getTrackByNumber = computed(() => {
    return (playlistId: string, trackNumber: number): Track | undefined => {
      const playlistTracks = tracks.value.get(playlistId) || []
      return playlistTracks.find(t => getTrackNumber(t) === trackNumber)
    }
  })

  const hasPlaylistData = computed(() => {
    return (id: string): boolean => {
      return playlists.value.has(id)
    }
  })

  const hasTracksData = computed(() => {
    return (id: string): boolean => {
      const playlistTracks = tracks.value.get(id)
      return playlistTracks !== undefined && playlistTracks.length > 0
    }
  })

  // === ACTIONS ===

  /**
   * Initialize the store and setup WebSocket listeners
   */
  async function initialize(): Promise<void> {
    if (isInitialized.value) {
      logger.debug('Unified playlist store already initialized')
      return
    }

    try {
      logger.info('Initializing unified playlist store')
      
      // Setup WebSocket listeners first
      setupWebSocketListeners()
      
      // Load initial data
      await loadAllPlaylists()
      
      // Join playlists room for real-time updates
      socketService.emit(SOCKET_EVENTS.JOIN_PLAYLISTS, {})
      
      isInitialized.value = true
      logger.info('Unified playlist store initialized successfully')
      
    } catch (err) {
      error.value = 'Failed to initialize playlist store'
      logger.error('Failed to initialize unified playlist store', { error: err })
      throw err
    }
  }

  /**
   * Load all playlists from the API
   */
  async function loadAllPlaylists(): Promise<void> {
    try {
      isLoading.value = true
      error.value = null

      const playlistsData = await apiService.getPlaylists()
      
      if (!Array.isArray(playlistsData)) {
        throw new Error('Invalid playlists data format')
      }

      // Clear existing data
      playlists.value.clear()
      tracks.value.clear()

      // Store playlists and their tracks
      for (const playlist of playlistsData) {
        playlists.value.set(playlist.id, {
          ...playlist,
          tracks: [] // Will be populated separately
        })
        
        if (playlist.tracks && Array.isArray(playlist.tracks)) {
          tracks.value.set(playlist.id, playlist.tracks)
        }
      }

      lastSync.value = Date.now()
      logger.info(`Loaded ${playlistsData.length} playlists into unified store`)

    } catch (err) {
      error.value = 'Failed to load playlists'
      logger.error('Failed to load playlists', { error: err })
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Load tracks for a specific playlist
   */
  async function loadPlaylistTracks(playlistId: string): Promise<Track[]> {
    try {
      // Check if we already have tracks data
      if (hasTracksData.value(playlistId)) {
        return tracks.value.get(playlistId)!
      }

      logger.debug('Loading tracks for playlist', { playlistId })
      
      const fullPlaylist = await apiService.getPlaylist(playlistId)
      
      if (fullPlaylist && fullPlaylist.tracks) {
        // Update tracks data
        tracks.value.set(playlistId, fullPlaylist.tracks)
        
        // Update performance index
        updateTrackIndexMap(playlistId, fullPlaylist.tracks)
        
        // Update playlist metadata if needed
        if (playlists.value.has(playlistId)) {
          const existingPlaylist = playlists.value.get(playlistId)!
          playlists.value.set(playlistId, {
            ...existingPlaylist,
            ...fullPlaylist,
            tracks: [] // Keep tracks separate
          })
        }
        
        logger.debug(`Loaded ${fullPlaylist.tracks.length} tracks for playlist ${playlistId}`)
        return fullPlaylist.tracks
      }

      return []
    } catch (err) {
      logger.error('Failed to load playlist tracks', { playlistId, error: err })
      throw err
    }
  }

  /**
   * Clear tracks for a specific playlist to force reload
   */
  function clearPlaylistTracks(playlistId: string): void {
    logger.debug('Clearing tracks for playlist', { playlistId })
    tracks.value.set(playlistId, [])
  }

  /**
   * Create a new playlist
   */
  async function createPlaylist(title: string, description = ''): Promise<string> {
    try {
      isLoading.value = true
      
      const newPlaylistData = await apiService.createPlaylist(title, description)
      const playlistId = newPlaylistData.id
      
      // The playlist will be added via WebSocket events
      // But we can optimistically add it locally for immediate UI feedback
      const newPlaylist: PlayList = {
        ...newPlaylistData,
        type: 'playlist' as const,
        tracks: [], // Keep tracks separate in our store
        track_count: 0,
        last_played: 0 // Initialize with 0
      }
      
      playlists.value.set(playlistId, newPlaylist)
      tracks.value.set(playlistId, [])
      
      logger.info('Created new playlist', { playlistId, title })
      return playlistId
      
    } catch (err) {
      logger.error('Failed to create playlist', { title, error: err })
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Update playlist metadata
   */
  async function updatePlaylist(playlistId: string, updates: { title?: string; description?: string }): Promise<void> {
    try {
      await apiService.updatePlaylist(playlistId, updates)
      
      // Update local data optimistically
      const existingPlaylist = playlists.value.get(playlistId)
      if (existingPlaylist) {
        playlists.value.set(playlistId, {
          ...existingPlaylist,
          ...updates
        })
      }
      
      logger.info('Updated playlist', { playlistId, updates })
      
    } catch (err) {
      logger.error('Failed to update playlist', { playlistId, updates, error: err })
      throw err
    }
  }

  /**
   * Delete a playlist
   */
  async function deletePlaylist(playlistId: string): Promise<void> {
    try {
      await apiService.deletePlaylist(playlistId)
      
      // Remove from local data optimistically
      playlists.value.delete(playlistId)
      tracks.value.delete(playlistId)
      trackIndexMaps.value.delete(playlistId) // Clean up index map
      
      logger.info('Deleted playlist', { playlistId })
      
    } catch (err) {
      logger.error('Failed to delete playlist', { playlistId, error: err })
      throw err
    }
  }

  /**
   * Update track index map for performance optimization
   */
  function updateTrackIndexMap(playlistId: string, trackList: Track[]): void {
    const indexMap = createTrackIndexMap(trackList)
    trackIndexMaps.value.set(playlistId, indexMap)
  }

  /**
   * Get track by number using O(1) lookup
   */
  function getTrackByNumberOptimized(playlistId: string, trackNumber: number): Track | null {
    const indexMap = trackIndexMaps.value.get(playlistId)
    if (indexMap) {
      return indexMap.get(trackNumber) || null
    }
    
    // Fallback to O(n) if index not available
    const trackList = tracks.value.get(playlistId)
    if (trackList) {
      const { track } = findTrackByNumberSafe(trackList, trackNumber)
      return track
    }
    
    return null
  }

  /**
   * Delete a track from a playlist
   */
  async function deleteTrack(playlistId: string, trackNumber: number): Promise<void> {
    try {
      await apiService.deleteTrack(playlistId, trackNumber)
      
      // Remove from local data optimistically using centralized logic
      const playlistTracks = tracks.value.get(playlistId)
      if (playlistTracks) {
        const updatedTracks = filterTrackByNumber(playlistTracks, trackNumber)
        tracks.value.set(playlistId, updatedTracks)
        
        // Update performance index
        updateTrackIndexMap(playlistId, updatedTracks)
        
        // Update playlist track count
        const playlist = playlists.value.get(playlistId)
        if (playlist) {
          playlists.value.set(playlistId, {
            ...playlist,
            track_count: updatedTracks.length
          })
        }
      }
      
      logger.info('Deleted track', { playlistId, trackNumber })
      
    } catch (err) {
      logger.error('Failed to delete track', { playlistId, trackNumber, error: err })
      throw err
    }
  }

  // Removed obsolete drag operation tracking functions

  /**
   * Apply optimistic track updates (for immediate UI feedback during drag)
   */
  function setTracksOptimistic(playlistId: string, newTracks: Track[]): void {
    tracks.value.set(playlistId, newTracks)
    // Update performance index
    updateTrackIndexMap(playlistId, newTracks)
    logger.debug('Applied optimistic tracks update', { playlistId, trackCount: newTracks.length })
  }

  /**
   * Reorder tracks in a playlist
   */
  async function reorderTracks(playlistId: string, newOrder: number[]): Promise<void> {
    // Mark drag operation as ongoing to prevent WebSocket conflicts
    ongoingDragOperations.value.add(playlistId)

    try {
      // Convert track numbers to track IDs for API call
      const playlistTracks = tracks.value.get(playlistId)
      if (!playlistTracks || playlistTracks.length === 0) {
        logger.warn('No tracks found for reorder, skipping', { playlistId })
        return
      }

      // Validate tracks before reordering
      const validation = validateTracksForDrag(playlistTracks)
      if (!validation.valid) {
        logger.warn('Track validation issues during reorder', { playlistId, errors: validation.errors })
      }

      // Use existing index map if available, otherwise create one
      let trackMap = trackIndexMaps.value.get(playlistId)
      if (!trackMap) {
        trackMap = createTrackIndexMap(playlistTracks)
        trackIndexMaps.value.set(playlistId, trackMap)
      }

      // Map track numbers to track IDs
      const trackIds = newOrder
        .map(num => {
          const track = trackMap!.get(num)
          if (!track) {
            logger.warn(`Track with number ${num} not found in playlist ${playlistId}`, { availableTracks: playlistTracks.length })
            return null
          }
          return track.id
        })
        .filter((id): id is string => id !== null)

      if (trackIds.length === 0) {
        logger.warn('No valid track IDs found for reorder, skipping', { playlistId, newOrder })
        return
      }

      if (trackIds.length !== newOrder.length) {
        logger.warn(`Could not map all track numbers to IDs: expected ${newOrder.length}, got ${trackIds.length}`, {
          playlistId,
          newOrder,
          mappedIds: trackIds.length
        })
        // Continue with partial reorder if we have at least some valid tracks
      }

      // Send track IDs to backend (not track numbers)
      await apiService.reorderTracks(playlistId, trackIds)

      // Update local data optimistically using centralized logic and performance optimization
      const reorderedTracks = newOrder
        .map(num => trackMap!.get(num))
        .filter((track): track is Track => track !== undefined)
        .map((track, index) => ({
          ...track,
          track_number: index + 1, // Update track numbers for new positions
          number: undefined // Remove legacy field
        }))

      tracks.value.set(playlistId, reorderedTracks)
      // Update performance index with new data
      updateTrackIndexMap(playlistId, reorderedTracks)

      logger.info('Reordered tracks', { playlistId, newOrder })
      
      // CRITICAL FIX: Clear drag operation immediately after successful API call
      // to allow WebSocket broadcast to update the UI properly
      ongoingDragOperations.value.delete(playlistId)
      logger.debug('Cleared drag operation flag after successful reorder', { playlistId })
      
    } catch (err: any) {
      // Use centralized error handling
      const context: DragContext = {
        operation: 'reorder',
        playlistId,
        trackNumbers: newOrder,
        component: 'UnifiedPlaylistStore'
      }
      
      const dragError = handleDragError(err, context, { logLevel: 'error' })
      
      // Handle 404 errors - playlist might not exist anymore
      if (err?.response?.status === 404 || err?.status === 404) {
        logger.warn('Playlist not found during reorder, removing from local store', { playlistId })
        // Remove the playlist from local store since it doesn't exist on backend
        playlists.value.delete(playlistId)
        tracks.value.delete(playlistId)
        trackIndexMaps.value.delete(playlistId) // Clean up index map
        
        // Force a full sync to get current state
        setTimeout(() => {
          loadAllPlaylists().catch(error => 
            logger.error('Failed to sync after playlist not found', { error })
          )
        }, 1000)
      }
      
      throw dragError
    } finally {
      // Ensure cleanup even on error (already cleaned on success above)
      ongoingDragOperations.value.delete(playlistId)
    }
  }

  /**
   * Move track between playlists
   */
  async function moveTrackBetweenPlaylists(
    sourcePlaylistId: string,
    targetPlaylistId: string,
    trackNumber: number,
    targetPosition?: number
  ): Promise<void> {
    try {
      await apiService.moveTrackBetweenPlaylists(
        sourcePlaylistId,
        targetPlaylistId,
        trackNumber,
        targetPosition
      )
      
      // The tracks will be updated via WebSocket events
      logger.info('Moved track between playlists', { 
        sourcePlaylistId, 
        targetPlaylistId, 
        trackNumber, 
        targetPosition 
      })
      
    } catch (err) {
      logger.error('Failed to move track between playlists', { 
        sourcePlaylistId, 
        targetPlaylistId, 
        trackNumber, 
        error: err 
      })
      throw err
    }
  }

  /**
   * Manual sync for fallback scenarios
   */
  async function forceSync(): Promise<void> {
    logger.info('Force syncing unified playlist store')
    await loadAllPlaylists()
  }

  // === WEBSOCKET EVENT HANDLERS ===

  function setupWebSocketListeners(): void {
    // Listen for playlist state changes
    socketService.on('state:playlist', handlePlaylistStateUpdate)
    
    // Listen for playlists collection updates
    socketService.on('state:playlists', handlePlaylistsStateUpdate)
    
    // Listen for track additions
    socketService.on('state:track_added', handleTrackAdded)
    
    // Listen for track updates
    socketService.on('state:track', handleTrackUpdate)
    
    // Listen for track deletions
    socketService.on('state:track_deleted', handleTrackDeleted)
    
    // Note: Track reordering is handled via 'state:playlists' updates
    
    // Listen for playlist creation
    socketService.on('state:playlist_created', handlePlaylistCreated)
    
    // Listen for playlist updates
    socketService.on('state:playlist_updated', handlePlaylistUpdated)
    
    // Listen for playlist deletions
    socketService.on('state:playlist_deleted', handlePlaylistDeleted)
    
    // Listen for NFC association updates
    socketService.on('nfc_association_state', handleNfcAssociationUpdate)

    logger.info('WebSocket listeners setup for unified playlist store')
  }

  function handlePlaylistStateUpdate(event: any): void {
    const playlistData = 'data' in event ? event.data : event
    if (!playlistData?.id) return

    logger.debug('Received playlist state update', { playlistId: playlistData.id })
    
    // Update playlist metadata
    playlists.value.set(playlistData.id, {
      ...playlistData,
      tracks: [] // Keep tracks separate
    })
    
    // Update tracks if provided
    if (playlistData.tracks && Array.isArray(playlistData.tracks)) {
      tracks.value.set(playlistData.id, playlistData.tracks)
    }
  }

  function handlePlaylistsStateUpdate(event: any): void {
    const payload = 'data' in event ? event.data : event
    if (!payload?.playlists || !Array.isArray(payload.playlists)) return

    logger.debug('Received playlists state update', { count: payload.playlists.length })
    
    // Only update/add the playlists that are in this event
    // DON'T clear existing data to avoid overwriting optimistic updates
    for (const playlist of payload.playlists) {
      // Skip updates for playlists with active drag operations to prevent conflicts
      if (ongoingDragOperations.value.has(playlist.id)) {
        logger.debug('Skipping WebSocket update for playlist with active drag operation', { playlistId: playlist.id })
        continue
      }
      // Update playlist metadata
      const existingPlaylist = playlists.value.get(playlist.id)
      playlists.value.set(playlist.id, {
        ...existingPlaylist,
        ...playlist,
        tracks: [] // Keep tracks separate
      })
      
      // Update tracks with proper track_numbers from backend
      if (playlist.tracks && Array.isArray(playlist.tracks)) {
        // Sort tracks by track_number to ensure correct order
        const sortedTracks = playlist.tracks.slice().sort((a: any, b: any) =>
          getTrackNumber(a) - getTrackNumber(b)
        )
        tracks.value.set(playlist.id, sortedTracks)

        logger.debug('Updated tracks with WebSocket data', {
          playlistId: playlist.id,
          tracksCount: sortedTracks.length,
          firstTrackNumber: sortedTracks[0] ? getTrackNumber(sortedTracks[0]) : 0
        })
      }
    }
  }

  function handleTrackAdded(data: any): void {
    if (!data.playlist_id || !data.track) return

    logger.debug('Received track added event', { playlistId: data.playlist_id })

    const playlistTracks = tracks.value.get(data.playlist_id) || []
    const trackNumber = getTrackNumber(data.track)

    // Check if track already exists
    if (!playlistTracks.find(t => getTrackNumber(t) === trackNumber)) {
      const updatedTracks = [...playlistTracks, data.track].sort(
        (a, b) => getTrackNumber(a) - getTrackNumber(b)
      )
      tracks.value.set(data.playlist_id, updatedTracks)

      // Update playlist track count
      const playlist = playlists.value.get(data.playlist_id)
      if (playlist) {
        playlists.value.set(data.playlist_id, {
          ...playlist,
          track_count: updatedTracks.length
        })
      }
    }
  }

  function handleTrackUpdate(trackData: any): void {
    if (!trackData?.id) return

    logger.debug('Received track update', { trackId: trackData.id })

    const trackDataNumber = getTrackNumber(trackData)

    // Find and update the track across all playlists
    for (const [playlistId, playlistTracks] of tracks.value.entries()) {
      const trackIndex = playlistTracks.findIndex(t =>
        getTrackNumber(t) === trackDataNumber
      )

      if (trackIndex !== -1) {
        const updatedTracks = [...playlistTracks]
        updatedTracks[trackIndex] = trackData
        tracks.value.set(playlistId, updatedTracks)
        break
      }
    }
  }

  function handleTrackDeleted(data: any): void {
    if (!data.playlist_id || !data.track_numbers) return
    
    logger.debug('Received track deleted event', { 
      playlistId: data.playlist_id, 
      trackNumbers: data.track_numbers 
    })
    
    const playlistTracks = tracks.value.get(data.playlist_id)
    if (playlistTracks) {
      // Use centralized filtering logic for consistency
      const updatedTracks = filterTracksByNumbers(playlistTracks, data.track_numbers)
      tracks.value.set(data.playlist_id, updatedTracks)
      
      // Update performance index
      updateTrackIndexMap(data.playlist_id, updatedTracks)
      
      // Update playlist track count
      const playlist = playlists.value.get(data.playlist_id)
      if (playlist) {
        playlists.value.set(data.playlist_id, {
          ...playlist,
          track_count: updatedTracks.length
        })
      }
    }
  }

  // handleTracksReordered removed - reordering is now handled via 'state:playlists' updates

  function handlePlaylistCreated(event: any): void {
    const data = 'data' in event ? event.data : event
    if (!data?.playlist) return
    
    logger.debug('Received playlist created event', { playlistId: data.playlist.id })
    
    playlists.value.set(data.playlist.id, {
      ...data.playlist,
      tracks: []
    })
    
    if (data.playlist.tracks && Array.isArray(data.playlist.tracks)) {
      tracks.value.set(data.playlist.id, data.playlist.tracks)
    } else {
      tracks.value.set(data.playlist.id, [])
    }
  }

  function handlePlaylistUpdated(event: any): void {
    const data = 'data' in event ? event.data : event
    if (!data?.playlist) return
    
    logger.debug('Received playlist updated event', { playlistId: data.playlist.id })
    
    playlists.value.set(data.playlist.id, {
      ...data.playlist,
      tracks: []
    })
    
    if (data.playlist.tracks && Array.isArray(data.playlist.tracks)) {
      tracks.value.set(data.playlist.id, data.playlist.tracks)
    }
  }

  function handlePlaylistDeleted(event: any): void {
    const data = 'data' in event ? event.data : event
    if (!data?.playlist_id) return
    
    logger.debug('Received playlist deleted event', { playlistId: data.playlist_id })
    
    playlists.value.delete(data.playlist_id)
    tracks.value.delete(data.playlist_id)
  }

  function handleNfcAssociationUpdate(event: any): void {
    const data = 'data' in event ? event.data : event
    if (!data?.playlist_id) return
    
    logger.debug('Received NFC association update', { 
      playlistId: data.playlist_id, 
      state: data.state,
      tagId: data.tag_id 
    })
    
    // Only handle successful associations for playlist updates
    if (data.state === 'success' && data.playlist_id && data.tag_id) {
      const existingPlaylist = playlists.value.get(data.playlist_id)
      if (existingPlaylist) {
        // Update playlist with NFC tag information
        playlists.value.set(data.playlist_id, {
          ...existingPlaylist,
          nfc_tag_id: data.tag_id
        })
        
        logger.info('Updated playlist with NFC tag association', { 
          playlistId: data.playlist_id, 
          tagId: data.tag_id 
        })
      }
    }
    
    // Handle association removal
    if (data.state === 'removed' && data.playlist_id) {
      const existingPlaylist = playlists.value.get(data.playlist_id)
      if (existingPlaylist && existingPlaylist.nfc_tag_id) {
        // Remove NFC tag association
        playlists.value.set(data.playlist_id, {
          ...existingPlaylist,
          nfc_tag_id: undefined
        })
        
        logger.info('Removed NFC tag association from playlist', { 
          playlistId: data.playlist_id 
        })
      }
    }
  }

  /**
   * Cleanup WebSocket listeners
   */
  function cleanup(): void {
    socketService.off('state:playlist', handlePlaylistStateUpdate)
    socketService.off('state:playlists', handlePlaylistsStateUpdate)
    socketService.off('state:track_added', handleTrackAdded)
    socketService.off('state:track', handleTrackUpdate)
    socketService.off('state:track_deleted', handleTrackDeleted)
    // state:tracks_reordered listener removed (handled via state:playlists)
    socketService.off('state:playlist_created', handlePlaylistCreated)
    socketService.off('state:playlist_updated', handlePlaylistUpdated)
    socketService.off('state:playlist_deleted', handlePlaylistDeleted)
    socketService.off('nfc_association_state', handleNfcAssociationUpdate)
    
    logger.info('Cleaned up WebSocket listeners for unified playlist store')
  }

  return {
    // State
    isLoading,
    error,
    lastSync,
    isInitialized,

    // Getters
    getAllPlaylists,
    getPlaylistById,
    getPlaylistWithTracks,
    getTracksForPlaylist,
    getTrackByNumber,
    getTrackByNumberOptimized, // Optimized O(1) lookup
    hasPlaylistData,
    hasTracksData,

    // Actions
    initialize,
    loadAllPlaylists,
    loadPlaylistTracks,
    clearPlaylistTracks,
    setTracksOptimistic, // For optimistic UI updates
    createPlaylist,
    updatePlaylist,
    deletePlaylist,
    deleteTrack,
    reorderTracks,
    moveTrackBetweenPlaylists,
    forceSync,
    cleanup,
    
    // Drag operation management - simplified
  }
})