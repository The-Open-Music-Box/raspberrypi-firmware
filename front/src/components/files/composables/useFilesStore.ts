/**
 * FilesStore Composable - DEPRECATED
 *
 * ⚠️  DEPRECATED: This composable has been replaced by the unified playlist store.
 * Use `useUnifiedPlaylistStore` instead for all playlist and track operations.
 * This file provides backward compatibility during migration.
 * 
 * @deprecated Use useUnifiedPlaylistStore instead
 */
import { ref } from 'vue'
import { logger } from '@/utils/logger'
import { useUnifiedPlaylistStore } from '@/stores/unifiedPlaylistStore'

export function useFilesStore() {
  // DEPRECATED: Use unified store instead
  logger.warn('useFilesStore is deprecated - use useUnifiedPlaylistStore instead')
  const unifiedStore = useUnifiedPlaylistStore()
  
  // Return a backward compatibility wrapper
  return {
    // State - delegates to unified store
    playlists: unifiedStore.getAllPlaylists,
    isLoading: unifiedStore.isLoading,
    error: unifiedStore.error,
    isEditMode: ref(false),
    isSaving: ref(false),

    // Methods - delegates to unified store
    async loadPlaylists() {
      logger.warn('useFilesStore.loadPlaylists is deprecated')
      return unifiedStore.loadAllPlaylists()
    },

    async deleteTrack(playlistId: string, trackNumber: number) {
      logger.warn('useFilesStore.deleteTrack is deprecated')
      return unifiedStore.deleteTrack(playlistId, trackNumber)
    },

    toggleEditMode() {
      logger.warn('useFilesStore.toggleEditMode is deprecated - handle edit mode locally')
      // Just a no-op for compatibility
    },

    async updatePlaylistTitle(playlistId: string, newTitle: string) {
      logger.warn('useFilesStore.updatePlaylistTitle is deprecated')
      return unifiedStore.updatePlaylist(playlistId, { title: newTitle })
    },

    async reorderPlaylistTracks(playlistId: string, newOrder: number[]) {
      logger.warn('useFilesStore.reorderPlaylistTracks is deprecated')
      return unifiedStore.reorderTracks(playlistId, newOrder)
    },

    async moveTrackBetweenPlaylists(
      sourcePlaylistId: string, 
      targetPlaylistId: string, 
      trackNumber: number,
      targetPosition?: number
    ) {
      logger.warn('useFilesStore.moveTrackBetweenPlaylists is deprecated')
      return unifiedStore.moveTrackBetweenPlaylists(
        sourcePlaylistId, 
        targetPlaylistId, 
        trackNumber, 
        targetPosition
      )
    },

    async createNewPlaylist(title: string) {
      logger.warn('useFilesStore.createNewPlaylist is deprecated')
      return unifiedStore.createPlaylist(title)
    },

    setupRealtimeListeners() {
      logger.warn('useFilesStore.setupRealtimeListeners is deprecated - unified store handles this automatically')
      // No-op - unified store handles all WebSocket listeners
    },

    cleanupRealtimeListeners() {
      logger.warn('useFilesStore.cleanupRealtimeListeners is deprecated - unified store handles this automatically')
      // No-op - unified store handles cleanup
    }
  }
}