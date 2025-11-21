<template>
  <div>
    <!-- Loading and error states -->
    <div v-if="isLoading" :class="['text-disabled', 'py-4']">{{ t('common.loading') }}</div>
    <div v-if="error" :class="['text-error', 'py-2']">{{ error }}</div>

    <template v-if="!isLoading && !error">
      <FilesList
        :playlists="playlists"
        :selectedTrack="selectedTrack"
        :playingPlaylistId="playingPlaylistId"
        :playingTrackNumber="playingTrackNumber"
        @deleteTrack="handleDeleteTrack"
        @select-track="handleSelectTrack"
        @play-playlist="handlePlayPlaylist"
        @feedback="onFeedback"
        @playlist-added="loadPlaylists"
        @playlist-deleted="loadPlaylists"
        @playlist-updated="loadPlaylists"
      />
      <DeleteDialog
        :open="showDeleteDialog"
        :track="localSelectedTrack"
        :playlist="selectedPlaylist"
        @close="closeDeleteDialog"
        @confirm="handleDeleteConfirm"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
/**
 * FileListContainer Component (MIGRATED)
 *
 * Container component for managing playlists and audio files.
 * Now uses unified playlist store as single source of truth.
 */
import { onMounted, onUnmounted, ref, computed } from 'vue'
import FilesList from './FilesList.vue'
import DeleteDialog from './DeleteDialog.vue'
import type { PlayList, Track } from './types'
import { useI18n } from 'vue-i18n'
import { logger } from '@/utils/logger'
import { useServerStateStore } from '@/stores/serverStateStore'
import { useUnifiedPlaylistStore } from '@/stores/unifiedPlaylistStore'
import { getTrackNumber, findTrackByNumber } from '@/utils/trackFieldAccessor'

const { t } = useI18n()
const serverStateStore = useServerStateStore()
const unifiedStore = useUnifiedPlaylistStore()

const props = defineProps<{
  /** Currently selected track, if any */
  selectedTrack?: Track | null
}>()

const localSelectedTrack = ref<Track | null>(props.selectedTrack || null)

const emit = defineEmits<{
  /** Emitted when a track is selected for playback */
  (e: 'select-track', data: { track: Track, playlist: PlayList }): void
  /** Emitted when feedback needs to be shown */
  (e: 'feedback', data: { type: 'success' | 'error', message: string }): void
}>()

// UNIFIED STORE AS SINGLE SOURCE OF TRUTH
const playlists = computed(() => {
  return unifiedStore.getAllPlaylists.map(playlist => ({
    ...playlist,
    tracks: unifiedStore.getTracksForPlaylist(playlist.id)
  }))
})

const isLoading = computed(() => unifiedStore.isLoading)
const error = computed(() => unifiedStore.error)

const showDeleteDialog = ref(false)
const selectedPlaylist = ref<PlayList | null>(null)

// SIMPLIFIED: No more manual loading - store handles everything
const loadPlaylists = async () => {
  try {
    logger.debug('Requesting playlist reload via unified store', {}, 'FileListContainer')
    await unifiedStore.forceSync()
  } catch (err) {
    logger.error('Failed to reload playlists', { error: err }, 'FileListContainer')
    emit('feedback', { type: 'error', message: t('file.errorLoading') })
  }
}

// SIMPLIFIED: Delete via unified store
const deleteTrack = async (playlistId: string, trackNumber: number) => {
  try {
    await unifiedStore.deleteTrack(playlistId, trackNumber)
    logger.info('Track deletion completed via unified store', { playlistId, trackNumber }, 'FileListContainer')
  } catch (err) {
    logger.error('Failed to delete track', { playlistId, trackNumber, error: err }, 'FileListContainer')
    throw err
  }
}

// Current playing info from server state
const playingPlaylistId = computed(() => serverStateStore.playerState.active_playlist_id)
const playingTrackId = computed(() => serverStateStore.playerState.active_track_id)

// Find the track number for the currently playing track using unified accessor
const playingTrackNumber = computed(() => {
  if (!playingPlaylistId.value || !playingTrackId.value) return null
  
  const playlistTracks = unifiedStore.getTracksForPlaylist(playingPlaylistId.value)
  const track = playlistTracks.find(t => t.id === playingTrackId.value)
  return track ? getTrackNumber(track) : null
})

/**
 * Close the delete confirmation dialog
 */
const closeDeleteDialog = () => {
  showDeleteDialog.value = false
  selectedPlaylist.value = null
  localSelectedTrack.value = null
}

/**
 * Handle track selection for playback
 * @param {Object} data - Track and playlist data
 */
const handleSelectTrack = (data: { track: Track, playlist: PlayList }) => {
  emit('select-track', data)
}

/**
 * Handle track selection for deletion (SIMPLIFIED)
 * @param {Object} data - Track and playlist identifiers  
 */
const handleDeleteTrack = async ({ playlistId, trackNumber }: { playlistId: string, trackNumber: number }) => {
  logger.info('DELETE TRACK EVENT RECEIVED', { playlistId, trackNumber }, 'FileListContainer')
  
  // SIMPLIFIED: Use unified store to get playlist and tracks
  const playlist = unifiedStore.getPlaylistById(playlistId)
  if (!playlist) {
    logger.warn('Playlist not found in unified store', { playlistId })
    return
  }

  // Ensure tracks are loaded for this playlist
  let tracks = unifiedStore.getTracksForPlaylist(playlistId)
  if (tracks.length === 0 && playlist.track_count && playlist.track_count > 0) {
    logger.debug('Loading tracks for playlist before deletion', { playlistId })
    try {
      tracks = await unifiedStore.loadPlaylistTracks(playlistId)
    } catch (error) {
      logger.error('Failed to load tracks for deletion', { playlistId, error })
      emit('feedback', { type: 'error', message: t('file.errorLoading') })
      return
    }
  }
  
  // Find the track using unified accessor
  const track = findTrackByNumber(tracks, trackNumber)
  if (!track) {
    logger.warn('Track not found for deletion', { 
      playlistId, 
      trackNumber, 
      availableTracks: tracks.map(t => ({ title: t.title, trackNumber: getTrackNumber(t) }))
    })
    return
  }

  // Open delete confirmation dialog
  selectedPlaylist.value = {
    ...playlist,
    tracks // Include tracks for dialog
  }
  localSelectedTrack.value = track
  showDeleteDialog.value = true
  
  logger.debug('Opening delete dialog', { playlistId, trackNumber, trackTitle: track.title })
}

/**
 * Handle track deletion confirmation (SIMPLIFIED)
 */
const handleDeleteConfirm = async () => {
  if (!localSelectedTrack.value || !selectedPlaylist.value) return
  
  try {
    const trackNumber = getTrackNumber(localSelectedTrack.value)
    await deleteTrack(selectedPlaylist.value.id, trackNumber)
    closeDeleteDialog()
    
    // Show success feedback
    emit('feedback', { type: 'success', message: t('file.trackDeleted') })
    
  } catch (err) {
    logger.error('Track deletion failed', { 
      playlistId: selectedPlaylist.value.id, 
      trackNumber: getTrackNumber(localSelectedTrack.value),
      error: err 
    })
    emit('feedback', { type: 'error', message: t('file.errorDeleting') })
  }
}

/**
 * Handle play playlist action from FilesList (SIMPLIFIED)
 * @param {PlayList} playlist - Playlist to play
 */
const handlePlayPlaylist = async (playlist: PlayList) => {
  try {
    // Use apiService import for playback control (server-authoritative)
    const apiService = await import('@/services/apiService')
    await apiService.default.startPlaylist(playlist.id)
    logger.info(`Playlist started successfully: ${playlist.title}`, { playlistId: playlist.id }, 'FileListContainer')
    
    // Player state will be updated via WebSocket events automatically
    // No manual state checking needed with unified architecture
    
  } catch (err) {
    // Show error feedback to user
    const errorMessage = err instanceof Error ? err.message : t('file.errorStartingPlaylist')
    emit('feedback', { type: 'error', message: errorMessage })
    logger.error('Error starting playlist', { error: err, playlistId: playlist.id }, 'FileListContainer')
  }
}

/**
 * Initialize unified store and setup component
 */
onMounted(async () => {
  logger.debug('FileListContainer mounting - initializing unified store')
  
  try {
    // Initialize the unified playlist store
    await unifiedStore.initialize()
    logger.info('FileListContainer: Unified store initialized successfully')
  } catch (err) {
    logger.error('Failed to initialize unified store', { error: err })
    emit('feedback', { type: 'error', message: t('file.errorLoading') })
  }
})

/**
 * Cleanup on unmount
 */
onUnmounted(() => {
  logger.debug('FileListContainer unmounting - cleaning up resources')
  // Store cleanup is handled by store itself via its cleanup method
})

// Forward feedback event to FilesList
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function onFeedback(_: { type: 'success' | 'error', message: string }) {
  // No-op: FilesList handles its own feedback; this is just to satisfy the event interface
}

</script>
