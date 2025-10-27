<template>
  <div class="playlists-section">
    <!-- Edit mode toggle and controls -->
    <div class="playlists-header">
      <h2 class="playlists-title">{{ t('file.playlists') }}</h2>
      <div class="header-actions" style="display: flex; gap: 12px;">
        <button
          v-if="false"
          @click="showYoutubeModal = true"
          class="btn-modern danger"
        >
          Add from YouTube
        </button>
        <button
          @click="toggleEditMode"
          :class="[
            'btn-modern',
            isEditMode ? 'active' : 'secondary'
          ]"
        >
          {{ isEditMode ? t('common.doneEditing') : t('common.edit') }}
        </button>
        <NewPlaylistButton
          v-if="isEditMode"
          @click="showCreatePlaylistDialog = true"
        />
      </div>
    </div>

    <!-- Error message -->
    <div v-if="error" :class="['text-error', 'py-4']">
      {{ error }}
    </div>

    <!-- Empty state message -->
    <div v-if="!error && (!playlists || playlists.length === 0)" class="flex flex-col items-center justify-center py-10 px-4 bg-surface border border-border rounded-lg">
      <div class="text-center mb-6">
        <h3 class="text-lg font-medium text-onBackground mb-2">{{ t('file.noPlaylistsYet') }}</h3>
        <p class="text-onBackground-medium">{{ t('file.createPlaylistPrompt') }}</p>
      </div>
      <NewPlaylistButton
        @click="showCreatePlaylistDialog = true"
      />
    </div>

    <!-- Playlists list -->
    <div v-for="playlist in localPlaylists" :key="playlist.id" class="playlist-item">
      <!-- Playlist header (always visible) -->
      <div
        class="playlist-header"
        @click="!isEditMode && togglePlaylist(playlist.id)"
        :style="{ cursor: isEditMode ? 'default' : 'pointer' }"
      >
        <div class="playlist-main">
          <div class="playlist-info">
            <h3>
              <span style="font-size: 18px; margin-right: 8px;">🎵</span>

              <!-- Editable title in edit mode -->
              <input
                v-if="isEditMode"
                v-model="editableTitles[playlist.id]"
                @blur="updatePlaylistTitle(playlist.id)"
                @keyup.enter="updatePlaylistTitle(playlist.id)"
                class="playlist-title-input"
                :placeholder="t('file.playlistTitle')"
                @click.stop
              />

              <!-- Regular title otherwise -->
              <span v-else class="playlist-title-display">{{ playlist.title }}</span>

              <!-- NFC status badge -->
              <span v-if="playlist.nfc_tag_id" class="nfc-status linked">
                NFC: {{ playlist.nfc_tag_id.substring(0, 6) }}
              </span>
              <span v-else class="nfc-status none">{{ t('common.noNfc') || 'No NFC' }}</span>
            </h3>

            <!-- Playlist metadata -->
            <div class="playlist-meta">
              <span>{{ playlist.track_count || playlist.tracks?.length || 0 }} {{ t('file.tracks') || 'tracks' }}</span>
              <span>{{ formatTotalDuration(playlist.tracks) }}</span>
              <span v-if="playlist.last_played">
                {{ t('file.lastPlayed') || 'Last' }}: {{ new Date(playlist.last_played).toLocaleDateString() }}
              </span>
              <span v-else>{{ t('file.neverPlayed') || 'Never played' }}</span>
            </div>
          </div>

          <!-- Playlist actions -->
          <div class="playlist-actions" :class="{ 'edit-mode': isEditMode }">
            <!-- Play button (not in edit mode) -->
            <button
              v-if="!isEditMode"
              @click.stop="$emit('play-playlist', playlist)"
              class="action-btn play"
              :title="playingPlaylistId === playlist.id ? (t('common.playing') || 'Playing') : (t('common.play') || 'Play')"
            >
              ▶
            </button>

            <!-- NFC button (not in edit mode) -->
            <button
              v-if="!isEditMode"
              @click.stop="openNfcDialog(playlist.id)"
              :class="['action-btn', 'nfc', playlist.nfc_tag_id ? 'override' : '']"
              :title="playlist.nfc_tag_id ? t('common.nfcLinkedTooltip') : t('common.linkNfc')"
            >
              📡
            </button>

            <!-- Delete button (only in edit mode) -->
            <button
              v-if="isEditMode"
              @click.stop="confirmDeletePlaylist(playlist.id)"
              class="action-btn delete-playlist-btn"
              :title="t('common.delete')"
            >
              🗑️
            </button>

            <!-- Expand/collapse chevron (not in edit mode) -->
            <span v-if="!isEditMode" style="margin-left: 8px; color: var(--text-muted);">
              <svg
                width="20"
                height="20"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                class="transform transition-transform"
                :class="{ 'rotate-180': openPlaylists.includes(playlist.id) }"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </span>
          </div>
        </div>
      </div>


      <!-- Upload Zone (in edit mode only) -->
      <div
        v-if="isEditMode"
        class="upload-zone show"
        @click="openUploadModal(playlist.id)"
      >
        <div class="upload-icon">📁</div>
        <div class="upload-text">{{ t('file.uploadFiles') || 'Upload Files' }}</div>
        <div class="upload-subtext">{{ t('file.uploadHint') || 'MP3, WAV, FLAC, M4A accepted' }}</div>
      </div>

      <!-- Tracks list (visible only if playlist is open) -->
      <div
        v-if="openPlaylists.includes(playlist.id)"
        class="playlist-content show"
      >
        <!-- Loading state for tracks -->
        <div v-if="trackLoadingStates[playlist.id]" class="px-4 py-3 text-disabled text-sm">
          {{ t('common.loading') }} tracks...
        </div>

        <div class="track-list">
          <draggable
            v-model="playlist.tracks"
            :disabled="!isEditMode"
            group="tracks"
            item-key="number"
            :animation="200"
            ghost-class="track-item-ghost"
            chosen-class="track-item-chosen"
            drag-class="track-item-dragging"
            :data-playlist-id="playlist.id"
            @start="dragStart"
            @end="dragEnd"
            @change="handleDragChange($event, playlist.id)"
          >
            <template #item="{element: track}">
              <div
                @click="isEditMode ? null : $emit('select-track', { track, playlist })"
                :class="[
                  'track-item',
                  isEditMode ? 'edit-mode' : '',
                  (playingPlaylistId === playlist.id && playingTrackNumber === getTrackNumber(track)) ? 'current' : ''
                ]"
                :style="{ cursor: isEditMode ? 'grab' : 'pointer' }"
              >
                <!-- Drag handle (edit mode only) -->
                <span v-if="isEditMode" class="track-drag-handle">⋮⋮</span>

                <!-- Track number (or playing indicator) -->
                <span v-if="!(playingPlaylistId === playlist.id && playingTrackNumber === getTrackNumber(track))" class="track-number">
                  {{ String(getTrackDisplayPosition(track, playlist.id)).padStart(2, '0') }}
                </span>
                <span v-else class="track-number wavy-anim" title="Playing">
                  <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
                    <rect x="2" y="6" width="2" height="8" rx="1" class="wavy-bar bar1"/>
                    <rect x="6" y="4" width="2" height="12" rx="1" class="wavy-bar bar2"/>
                    <rect x="10" y="7" width="2" height="6" rx="1" class="wavy-bar bar3"/>
                    <rect x="14" y="5" width="2" height="10" rx="1" class="wavy-bar bar4"/>
                  </svg>
                </span>

                <!-- Track name -->
                <span class="track-name">{{ track.title }}</span>

                <!-- Track duration -->
                <span class="track-duration">{{ formatDuration(track) }}</span>

                <!-- Delete button (edit mode only) -->
                <button
                  v-if="isEditMode"
                  @click.stop="handleDeleteTrackClick(playlist.id, getTrackNumber(track))"
                  class="track-delete-btn"
                  :title="t('common.delete')"
                >
                  🗑️
                </button>
              </div>
            </template>
          </draggable>
        </div>
        
        <!-- Empty state for playlists with no tracks -->
        <div v-if="!trackLoadingStates[playlist.id] && (!playlist.tracks || playlist.tracks.length === 0)" 
             class="px-4 py-3 text-disabled text-sm text-center">
          {{ playlist.track_count === 0 ? t('file.noTracksInPlaylist') || 'No tracks in this playlist' : 'Tracks not loaded yet' }}
        </div>
      </div>
    </div>
    <!-- NFC Association Dialog -->
    <NfcAssociateDialog
      :visible="showNfcDialog"
      :playlistId="selectedPlaylistId"
      :playlistTitle="selectedPlaylistTitle"
      @success="handleNfcSuccess"
      @update:visible="showNfcDialog = $event"
    />

    <!-- Delete Confirmation Dialog -->
    <DeleteDialog
      :open="showDeleteDialog"
      :title="t('file.deletePlaylistTitle')"
      :message="t('file.deletePlaylistMessage')"
      @confirm="deletePlaylist"
      @cancel="showDeleteDialog = false"
    />

    <!-- YouTube Integration Modal -->
    <div v-if="showYoutubeModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg max-w-4xl max-h-[90vh] w-full mx-4 overflow-auto">
        <div class="flex justify-between items-center p-4 border-b border-gray-200">
          <h2 class="text-xl font-semibold">Add from YouTube</h2>
          <button
            @click="showYoutubeModal = false"
            class="text-gray-500 hover:text-gray-700"
          >
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </button>
        </div>
        <div class="p-4">
          <YoutubeIntegration />
        </div>
      </div>
    </div>

    <!-- Create Playlist Dialog -->
    <CreatePlaylistDialog
      :open="showCreatePlaylistDialog"
      @create="createNewPlaylist"
      @cancel="showCreatePlaylistDialog = false"
    />

    <!-- Upload Modal -->
    <UploadModal v-if="currentUploadPlaylistId" :playlist-id="currentUploadPlaylistId" />

    <!-- Feedback toast message -->
    <transition
      enter-active-class="transform transition ease-out duration-300"
      enter-from-class="translate-y-2 opacity-0 sm:translate-y-0 sm:translate-x-2"
      enter-to-class="translate-y-0 opacity-100 sm:translate-x-0"
      leave-active-class="transition ease-in duration-200"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="feedbackMessage"
        :class="[
          'fixed bottom-4 right-4 px-4 py-3 rounded-lg shadow-lg z-50 max-w-sm',
          feedbackType === 'success' ? 'bg-success text-onSuccess' : 'bg-error text-onError'
        ]"
      >
        <div class="flex items-center">
          <svg v-if="feedbackType === 'success'" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
          <svg v-else class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{{ feedbackMessage }}</span>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { PlayList, Track } from './types'
import { logger } from '@/utils/logger'
import NfcAssociateDialog from './NfcAssociateDialog.vue'
import DeleteDialog from './DeleteDialog.vue'
import CreatePlaylistDialog from './CreatePlaylistDialog.vue'
import NewPlaylistButton from './NewPlaylistButton.vue'
import UploadModal from '@/components/upload/UploadModal.vue'
import YoutubeIntegration from '@/components/youtube/YoutubeIntegration.vue'
import { useUploadStore } from '@/stores/uploadStore'
import { useUnifiedPlaylistStore } from '@/stores/unifiedPlaylistStore'
import { getTrackNumber, getTrackDurationSeconds, formatTrackDuration } from '@/utils/trackFieldAccessor'
import { handleDragError, getDragErrorMessage, DragContext } from '@/utils/dragOperationErrorHandler'
import socketService from '@/services/socketService'
import { SOCKET_EVENTS } from '@/constants/apiRoutes'
import { NfcAssociationStateData } from '@/types/socket'
import draggable from 'vuedraggable'

const { t } = useI18n()
const uploadStore = useUploadStore()
const unifiedStore = useUnifiedPlaylistStore()

const props = defineProps<{
  playlists?: PlayList[]; // Optional - will use unified store if not provided
  error?: string;
  selectedTrack?: Track | null;
  playingPlaylistId?: string | null;
  playingTrackNumber?: number | null;
}>()

// SIMPLIFIED EVENTS - no more circular events
const emit = defineEmits(['play-playlist', 'select-track', 'deleteTrack', 'feedback'])


// Edit mode state - simplified
const isEditMode = ref(false)
const toggleEditMode = () => {
  isEditMode.value = !isEditMode.value
  logger.debug('Edit mode toggled', { editMode: isEditMode.value }, 'FilesList')
}

// OPTIMIZED DATA SOURCE - with performance improvements
const localPlaylists = computed(() => {
  // Use props playlists if provided (for backward compatibility)
  // Otherwise use unified store
  if (props.playlists && props.playlists.length > 0) {
    return props.playlists
  }
  
  // Cache the playlists array to avoid recalculating on every access
  const allPlaylists = unifiedStore.getAllPlaylists
  
  // Use Map for O(1) lookups instead of O(n) for each playlist
  return allPlaylists.map(playlist => {
    const tracks = unifiedStore.getTracksForPlaylist(playlist.id)
    return {
      ...playlist,
      tracks
    }
  })
})

const trackLoadingStates = ref<Record<string, boolean>>({})

// Editable titles for playlists
const editableTitles = ref<Record<string, string>>({})

// Watch for playlists and initialize editable titles
watch(localPlaylists, (newPlaylists) => {
  newPlaylists.forEach(playlist => {
    if (!editableTitles.value[playlist.id]) {
      editableTitles.value[playlist.id] = playlist.title
    }
  })
}, { immediate: true })

// Simplified delete track handler using unified accessor
const handleDeleteTrackClick = (playlistId: string, trackNumber: number) => {
  logger.info('DELETE BUTTON CLICKED', { playlistId, trackNumber, editMode: isEditMode.value }, 'FilesList')
  
  // Emit the event to parent - no debugging noise needed with unified store
  emit('deleteTrack', { playlistId, trackNumber })
}

// Delete dialog state
const showDeleteDialog = ref(false)
const playlistToDelete = ref<string | null>(null)

// Create playlist dialog state
const showCreatePlaylistDialog = ref(false)

// YouTube modal state
const showYoutubeModal = ref(false)

// Upload modal state
const currentUploadPlaylistId = ref<string | null>(null)

// Drag and drop state
const draggedTrack = ref<Track | null>(null)
const dragSourcePlaylistId = ref<string | null>(null)
const dragTargetPlaylistId = ref<string | null>(null)

// Debounce for drag operations to prevent multiple API calls
const dragOperationInProgress = ref(false)
let dragDebounceTimer: ReturnType<typeof setTimeout> | null = null

// Feedback messages
const feedbackMessage = ref('')
const feedbackType = ref<'success' | 'error' | ''>('')
const feedbackTimeout = ref<number | null>(null)

// Initialize with empty playlist ids (all playlists closed by default)
const openPlaylists = ref<string[]>([])

// No auto-open behavior needed, playlists will be closed by default
// Playlists initialized in closed state by default

// Removed unused watcher - playlists are managed by unified store

// NFC dialog state and logic
const showNfcDialog = ref(false)
const selectedPlaylistId = ref<string | null>(null)
const selectedPlaylistTitle = ref<string | null>(null)

/**
 * Handle successful NFC tag association
 * Force sync to ensure icon is updated immediately
 * @param {string} playlistId - ID of the playlist that was associated
 */
const handleNfcSuccess = async (playlistId: string) => {
  logger.debug('NFC association success', { playlistId })

  try {
    // Force sync the unified store to ensure NFC tag data is updated
    await unifiedStore.forceSync()
    logger.debug('Forced sync after NFC association success', { playlistId })

    showFeedback('success', t('file.nfcAssociationSuccess'))
  } catch (error) {
    logger.error('Failed to sync after NFC association', { playlistId, error })
    // Still show success message since the association succeeded
    showFeedback('success', t('file.nfcAssociationSuccess'))
  }
}

function openNfcDialog(id: string) {
  selectedPlaylistId.value = id
  // Find the playlist title from localPlaylists
  const playlist = localPlaylists.value.find(p => p.id === id)
  selectedPlaylistTitle.value = playlist?.title || null
  showNfcDialog.value = true
}

/**
 * Update a playlist title after editing (SIMPLIFIED)
 * @param {string} playlistId - Playlist identifier
 */
async function updatePlaylistTitle(playlistId: string) {
  const newTitle = editableTitles.value[playlistId]?.trim()
  if (!newTitle) return

  try {
    // Use unified store for consistency
    await unifiedStore.updatePlaylist(playlistId, { title: newTitle })
    showFeedback('success', t('file.playlistUpdated'))
    logger.info('Playlist title updated via unified store', { playlistId, newTitle })
  } catch (error) {
    showFeedback('error', t('file.errorUpdating'))
    logger.error('Failed to update playlist title', { playlistId, error }, 'FilesList')
  }
}

/**
 * Show delete confirmation dialog for a playlist
 * @param {string} playlistId - Playlist identifier
 */
function confirmDeletePlaylist(playlistId: string) {
  playlistToDelete.value = playlistId
  showDeleteDialog.value = true
}

/**
 * Delete a playlist after confirmation (SIMPLIFIED)
 */
async function deletePlaylist() {
  if (!playlistToDelete.value) return

  try {
    const deletedPlaylistId = playlistToDelete.value
    
    // Use unified store for consistency
    await unifiedStore.deletePlaylist(deletedPlaylistId)
    
    logger.info('Playlist deleted via unified store', { playlistId: deletedPlaylistId }, 'FilesList')
    showFeedback('success', t('file.playlistDeleted'))
    
    // No manual refresh needed - unified store handles WebSocket updates automatically
    
  } catch (err) {
    logger.error('Failed to delete playlist', { playlistId: playlistToDelete.value, error: err }, 'FilesList')
    showFeedback('error', t('file.errorDeletingPlaylist'))
  } finally {
    showDeleteDialog.value = false
    playlistToDelete.value = null
  }
}

/**
 * Create new playlist (SIMPLIFIED)
 * @param {string} title - Title for the new playlist
 */
async function createNewPlaylist(title: string) {
  try {
    logger.info('Creating new playlist via unified store', { title }, 'FilesList')

    // Use unified store for consistency
    const newPlaylistId = await unifiedStore.createPlaylist(title)
    
    logger.info('Playlist created successfully', { playlistId: newPlaylistId }, 'FilesList')
    showFeedback('success', t('file.playlistCreated'))

    // Enable edit mode if not already enabled
    if (!isEditMode.value) {
      isEditMode.value = true
    }

    // No manual refresh needed - unified store handles WebSocket updates automatically
    
  } catch (err) {
    logger.error('Failed to create playlist', { error: err }, 'FilesList')
    showFeedback('error', t('file.errorCreating'))
  } finally {
    // Always close the dialog
    showCreatePlaylistDialog.value = false
  }
}

/**
 * Show feedback toast message
 * @param {string} type - Message type (success/error)
 * @param {string} message - Message to display
 */
function showFeedback(type: 'success' | 'error', message: string) {
  // Clear any existing timeout
  if (feedbackTimeout.value) {
    clearTimeout(feedbackTimeout.value)
  }

  // Set message and type
  feedbackType.value = type
  feedbackMessage.value = message

  // Auto-hide after 3 seconds
  feedbackTimeout.value = window.setTimeout(() => {
    feedbackMessage.value = ''
    feedbackType.value = ''
    feedbackTimeout.value = null
  }, 3000)
}

/**
 * Handle drag start event
 * @param {Event} evt - Drag event
 */
function dragStart(evt: DragEvent & { item?: Track; from?: { dataset?: { playlistId?: string } } }) {
  draggedTrack.value = evt.item || null
  dragSourcePlaylistId.value = evt.from?.dataset?.playlistId || null
  logger.debug('Drag started', { sourcePlaylistId: dragSourcePlaylistId.value }, 'FilesList')
}

/**
 * Handle drag end event
 * @param {Event} evt - Drag event
 */
function dragEnd() {
  draggedTrack.value = null
  dragSourcePlaylistId.value = null
  dragTargetPlaylistId.value = null
}

/**
 * Handle drag change event (SIMPLIFIED with unified accessors)
 * @param {Event} evt - Change event
 * @param {string} playlistId - Current playlist ID
 */
async function handleDragChange(evt: { moved?: { element: Track }; added?: { element: Track }; from?: { dataset?: { playlistId?: string } } }, playlistId: string) {
  const eventType = evt.added ? 'added' : evt.moved ? 'moved' : 'unknown'
  logger.debug('Drag change event', { eventType, playlistId, operationInProgress: dragOperationInProgress.value }, 'FilesList')

  // Prevent multiple simultaneous drag operations
  if (dragOperationInProgress.value) {
    logger.debug('Drag operation already in progress, skipping', { eventType, playlistId }, 'FilesList')
    return
  }

  // Clear any existing debounce timer
  if (dragDebounceTimer) {
    clearTimeout(dragDebounceTimer)
  }

  // Set debounce timer to prevent rapid-fire drag events
  dragDebounceTimer = setTimeout(async () => {
    await processDragEvent(evt, playlistId, eventType)
  }, 150) // 150ms debounce
}

/**
 * Process the actual drag event logic
 */
async function processDragEvent(evt: { moved?: { element: Track }; added?: { element: Track }; from?: { dataset?: { playlistId?: string } } }, playlistId: string, eventType: string) {
  dragOperationInProgress.value = true
  
  try {
    logger.debug('Processing drag event', { eventType, playlistId }, 'FilesList')
    
    // Drag operation protection is handled in the store's reorderTracks function

    // Handle reordering within the same playlist
    if (evt.moved) {
      // Get the current playlist from localPlaylists which has been updated by vuedraggable
      const currentPlaylist = localPlaylists.value.find(p => p.id === playlistId)
      if (!currentPlaylist || !currentPlaylist.tracks) {
        throw new Error('Playlist not found or has no tracks')
      }
      
      // Get the new order from the visual position (after drag & drop)
      // Do NOT modify the tracks directly here - they're from computed property
      const trackNumbers: number[] = []
      currentPlaylist.tracks.forEach((track) => {
        trackNumbers.push(getTrackNumber(track)) // Original track number in new position
      })

      logger.debug('Drag reorder details', {
        playlistId,
        trackCount: currentPlaylist.tracks.length,
        newOrder: trackNumbers,
        firstThreeTracks: currentPlaylist.tracks.slice(0, 3).map(t => ({ number: getTrackNumber(t), title: t.title }))
      }, 'FilesList')

      // reorderTracks handles optimistic update internally
      await unifiedStore.reorderTracks(playlistId, trackNumbers)
      logger.info('Tracks reordered via unified store', { playlistId, newOrder: trackNumbers }, 'FilesList')
      showFeedback('success', t('file.tracksReordered'))
    }
    
    // Handle moving between playlists
    if (evt.added && evt.from) {
      const sourcePlaylistId = evt.from.dataset?.playlistId
      if (sourcePlaylistId && sourcePlaylistId !== playlistId) {
        const movedTrack = evt.added.element
        const trackNumber = getTrackNumber(movedTrack)
        
        logger.info('Track moved between playlists', { trackNumber, from: sourcePlaylistId, to: playlistId }, 'FilesList')

        // Use unified store for consistency
        await unifiedStore.moveTrackBetweenPlaylists(
          sourcePlaylistId,
          playlistId,
          trackNumber
        )
        showFeedback('success', t('file.trackMoved'))
      }
    }
  } catch (error) {
    // Use centralized error handling
    const context: DragContext = {
      operation: eventType === 'moved' ? 'reorder' : 'move',
      playlistId,
      trackNumbers: eventType === 'moved' ? [] : undefined,
      trackNumber: eventType === 'moved' ? undefined : 1,
      component: 'FilesList'
    }
    
    const dragError = handleDragError(error as Error, context, { 
      logLevel: 'error',
      showUserFeedback: true 
    })
    
    const userMessage = getDragErrorMessage(context.operation, dragError)
    showFeedback('error', userMessage)
    
    // Drag operation cleanup is handled automatically in the store
  } finally {
    // Always clear the operation flag
    dragOperationInProgress.value = false
    
    // Note: Drag operation end is marked in the unified store's reorderTracks method
    // This ensures proper timing with the API call completion
    
    // Clear debounce timer
    if (dragDebounceTimer) {
      clearTimeout(dragDebounceTimer)
      dragDebounceTimer = null
    }
  }
}

/**
 * Toggle a playlist's expanded/collapsed state (SIMPLIFIED)
 * @param {string} playlistId - Playlist identifier
 */
async function togglePlaylist(playlistId: string) {
  const index = openPlaylists.value.indexOf(playlistId)
  if (index === -1) {
    // Expanding playlist
    openPlaylists.value.push(playlistId)
    
    // Check if tracks need to be loaded using unified store
    const playlist = unifiedStore.getPlaylistById(playlistId)
    if (playlist && !unifiedStore.hasTracksData(playlistId) && playlist.track_count && playlist.track_count > 0) {
      if (!trackLoadingStates.value[playlistId]) {
        trackLoadingStates.value[playlistId] = true
        logger.debug('Loading tracks for playlist via unified store', { playlistId, trackCount: playlist.track_count }, 'FilesList')
        
        try {
          // Use unified store for consistent track loading
          const tracks = await unifiedStore.loadPlaylistTracks(playlistId)
          
          logger.debug('Tracks loaded for playlist', { 
            playlistId, 
            tracksLoaded: tracks.length
          }, 'FilesList')
          
        } catch (error) {
          logger.error('Failed to load tracks for playlist', { playlistId, error }, 'FilesList')
          showFeedback('error', t('file.errorLoading'))
        } finally {
          trackLoadingStates.value[playlistId] = false
        }
      }
    }
  } else {
    // Collapsing playlist
    openPlaylists.value.splice(index, 1)
  }
}


/**
 * Open upload modal for a playlist
 * @param {string} playlistId - Playlist identifier
 */
function openUploadModal(playlistId: string) {
  logger.debug('Opening upload modal for playlist', { playlistId }, 'FilesList')
  currentUploadPlaylistId.value = playlistId
  uploadStore.openUploadModal(playlistId)
  logger.debug('Upload store state updated', { isModalOpen: uploadStore.isModalOpen, modalPlaylistId: uploadStore.modalPlaylistId }, 'FilesList')
}

// Watch for modal close - simplified (no manual refresh needed)
watch(() => uploadStore.isModalOpen, (isOpen) => {
  if (!isOpen && currentUploadPlaylistId.value) {
    // Unified store handles WebSocket updates automatically
    // No manual refresh needed
    logger.debug('Upload modal closed', { playlistId: currentUploadPlaylistId.value }, 'FilesList')
    currentUploadPlaylistId.value = null
  }
})

// SIMPLIFIED: Only NFC state listener needed (no more playlist event duplication)
function setupGlobalNfcListener() {
  socketService.on(SOCKET_EVENTS.NFC_ASSOCIATION_STATE, (data: NfcAssociationStateData) => {
    logger.debug('Global NFC state received', { state: data.state, playlistId: data.playlist_id })
    
    // Only handle active/waiting states that should open dialogs
    if ((data.state === 'activated' || data.state === 'waiting') && data.playlist_id) {
      selectedPlaylistId.value = data.playlist_id
      showNfcDialog.value = true
    }
    
    // Success state feedback is handled by dialog component now
    if (data.state === 'success') {
      showFeedback('success', t('file.nfcAssociationSuccess'))
    }
  })
}

function cleanupGlobalNfcListener() {
  socketService.off(SOCKET_EVENTS.NFC_ASSOCIATION_STATE)
}

// REMOVED DUPLICATE LISTENERS - All playlist WebSocket events are now handled by unified store
// This eliminates the circular event problem identified in the audit

// Setup only NFC listener on mount
onMounted(() => {
  setupGlobalNfcListener()
  logger.debug('FilesList mounted - NFC listener setup (unified store handles playlist events)')
})

// Cleanup on unmount
onUnmounted(() => {
  cleanupGlobalNfcListener()
  
  // Clean up drag debounce timer
  if (dragDebounceTimer) {
    clearTimeout(dragDebounceTimer)
    dragDebounceTimer = null
  }
  
  logger.debug('FilesList unmounted - cleaned up NFC listener and drag timers')
})
/**
 * Format single track duration using unified accessor
 * @param {Track | string | number} track - Track object or duration value
 * @returns {string} Formatted duration
 */
function formatDuration(track: Track | string | number): string {
  if (typeof track === 'object' && track !== null) {
    // Use unified track accessor
    return formatTrackDuration(track)
  }
  
  // Legacy support for direct duration values
  const durationValue = typeof track === 'string' ? parseFloat(track) : track
  if (isNaN(durationValue)) return '00:00'
  
  const totalSeconds = Math.floor(durationValue)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  
  if (minutes >= 60) {
    const hours = Math.floor(minutes / 60)
    const remainingMinutes = minutes % 60
    return `${hours}:${remainingMinutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
  }
  
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

/**
 * Get track display position (visual position in the list)
 * @param {Track} track - Track object
 * @param {string} playlistId - Playlist ID
 * @returns {number} Display position (1-based)
 */
function getTrackDisplayPosition(track: Track, playlistId: string): number {
  const playlist = localPlaylists.value.find(p => p.id === playlistId)
  if (!playlist || !playlist.tracks) return getTrackNumber(track)
  
  const trackIndex = playlist.tracks.findIndex(t => 
    (t.id && track.id && t.id === track.id) || 
    (getTrackNumber(t) === getTrackNumber(track) && t.title === track.title)
  )
  
  return trackIndex >= 0 ? trackIndex + 1 : getTrackNumber(track)
}

/**
 * Format total duration of tracks using unified accessors
 * @param {Track[]} tracks - Array of tracks
 * @returns {string} Formatted total duration
 */
function formatTotalDuration(tracks: Track[]): string {
  if (!tracks || tracks.length === 0) return '00:00'
  
  let totalSeconds = 0
  for (const track of tracks) {
    // Use unified track accessor for consistent duration handling
    totalSeconds += getTrackDurationSeconds(track)
  }
  
  if (totalSeconds === 0) return '00:00'
  
  const totalSecondsInt = Math.floor(totalSeconds)
  const hours = Math.floor(totalSecondsInt / 3600)
  const minutes = Math.floor((totalSecondsInt % 3600) / 60)
  const secondsRemainder = totalSecondsInt % 60
  
  if (hours > 0) {
    return `${hours}h${minutes.toString().padStart(2, '0')}m`
  } else {
    return `${minutes.toString().padStart(2, '0')}:${secondsRemainder.toString().padStart(2, '0')}`
  }
}
</script>

<style scoped>

</style>
