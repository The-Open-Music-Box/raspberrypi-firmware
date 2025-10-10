<template>
  <div v-if="!serverStateStore" class="w-full max-w-4xl mx-auto p-4 text-center" style="color: var(--text-secondary);">
    Loading player...
  </div>
  <div v-else class="card-modern w-full max-w-4xl mx-auto">
    <!-- Compact Player -->
    <div class="compact-player">
      <!-- Player Info Row -->
      <div class="player-info">
        <!-- Album Cover -->
        <div class="player-cover">
          🎵
        </div>

        <!-- Track Details -->
        <div class="track-details">
          <div class="track-title-modern">
            {{ currentTrack?.title || t('audio.noTrackSelected') }}
          </div>
          <div class="track-artist-modern">
            {{ playerState?.active_playlist_title || t('audio.noPlaylist') }}
          </div>
        </div>

        <!-- Playback Controls (horizontal) -->
        <div class="player-controls">
          <button
            class="control-btn"
            :disabled="!playerState?.can_prev"
            :aria-label="t('player.previous')"
            @click="previous"
          >
            <svg width="16" height="16" fill="none">
              <path
                d="m10 8 4-3.5v7L10 8Z"
                fill="currentColor"
                stroke="currentColor"
                stroke-width="1.5"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
              <path
                d="M6 4.5v7"
                stroke="currentColor"
                stroke-width="1.5"
                stroke-linecap="round"
              />
            </svg>
          </button>

          <button
            class="control-btn play-btn"
            :aria-label="t('player.playPause')"
            @click="togglePlayPause"
          >
            <svg v-if="isPlaying" width="18" height="18" fill="currentColor">
              <rect x="5" y="3" width="2.5" height="12" rx="1.25" />
              <rect x="10.5" y="3" width="2.5" height="12" rx="1.25" />
            </svg>
            <svg v-else width="18" height="18" fill="currentColor">
              <polygon points="5,2 14,9 5,16" />
            </svg>
          </button>

          <button
            class="control-btn"
            :disabled="!playerState?.can_next"
            :aria-label="t('player.next')"
            @click="next"
          >
            <svg width="16" height="16" fill="none">
              <path
                d="m6 8 4-3.5v7L6 8Z"
                fill="currentColor"
                stroke="currentColor"
                stroke-width="1.5"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
              <path
                d="M10 4.5v7"
                stroke="currentColor"
                stroke-width="1.5"
                stroke-linecap="round"
              />
            </svg>
          </button>

          <!-- Volume Control -->
          <div class="volume-control">
            <svg width="16" height="16" fill="none" style="color: var(--text-secondary);">
              <path
                d="M8 3L5 6H2v4h3l3 3V3Z"
                fill="currentColor"
                stroke="currentColor"
                stroke-width="1.5"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
              <path
                d="M11 6.5c.5.5 1 1.2 1 2.5s-.5 2-1 2.5"
                stroke="currentColor"
                stroke-width="1.5"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
            <div class="volume-slider-container">
              <input
                type="range"
                min="0"
                max="100"
                :value="volume"
                @input="handleVolumeChange"
                class="volume-slider"
                aria-label="Volume"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Progress Bar -->
      <div class="progress-section">
        <div
          class="progress-bar-modern"
          @click="handleProgressClick"
          ref="progressBarRef"
        >
          <div
            class="progress-fill"
            :style="{ width: `${progressPercentage}%` }"
          ></div>
        </div>
        <div class="time-indicators">
          <span>{{ formatTime(currentTime) }}</span>
          <span>{{ formatTime(duration) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Simplified AudioPlayer Component
 *
 * Server-authoritative player with:
 * - Position updates from server state:track_position events (200ms)
 * - No frontend timers - all position comes from backend
 * - Optimistic UI updates for seek operations only
 * - Compact modern design with inline controls
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import type { Track, PlayList } from '../files/types'
import { useServerStateStore } from '@/stores/serverStateStore'
import { useUnifiedPlaylistStore } from '@/stores/unifiedPlaylistStore'
import { storeToRefs } from 'pinia'
import apiService from '@/services/apiService'
import { logger } from '@/utils/logger'
import { getTrackNumber, getTrackDurationMs } from '@/utils/trackFieldAccessor'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

// Props
interface Props {
  selectedTrack?: Track
  playlist?: PlayList
}
const props = defineProps<Props>()

// Stores
const serverStateStore = useServerStateStore()
const unifiedStore = useUnifiedPlaylistStore()
const { playerState } = storeToRefs(serverStateStore)

// Local reactive state - with smooth interpolation (all in milliseconds)
const currentTime = ref<number>(0)  // milliseconds
const isSeekInProgress = ref<boolean>(false)
const lastServerTime = ref<number>(0)  // milliseconds
const lastServerUpdate = ref<number>(0)
const animationFrame = ref<number | null>(null)

// Computed properties - enhanced with unified store data
const currentTrack = computed(() => {
  // Priority: server state > props > unified store lookup
  let track = playerState.value?.active_track || props.selectedTrack || null
  
  // If we have a track from server state or props, try to get full data from unified store
  if (track && playerState.value?.active_playlist_id) {
    const fullTrack = unifiedStore.getTrackByNumber(
      playerState.value.active_playlist_id, 
      getTrackNumber(track)
    )
    if (fullTrack) {
      track = fullTrack // Use full track data from store
    }
  }
  
  return track
})

const duration = computed(() => {
  // Priority: server state duration > track duration using unified accessor
  if (playerState.value?.duration_ms && playerState.value.duration_ms > 0) {
    return playerState.value.duration_ms // Keep in milliseconds
  }

  if (currentTrack.value) {
    return getTrackDurationMs(currentTrack.value) // Use millisecond accessor
  }

  return 0
})

const isPlaying = computed(() => {
  return Boolean(playerState.value?.is_playing)
})

// Progress bar handling
const progressBarRef = ref<HTMLElement | null>(null)
const progressPercentage = computed(() => {
  return duration.value > 0 ? (currentTime.value / duration.value) * 100 : 0
})

// Volume control
const volume = ref(75) // Default volume 75%
const isUserAdjustingVolume = ref(false) // Flag to prevent server updates during user interaction

// Initialize volume from player state
if (playerState.value?.volume != null) {
  volume.value = playerState.value.volume
}

// Watch for volume changes from server (Socket.IO events or other sources)
// BUT don't update if user is currently adjusting the volume slider
const unwatchVolume = serverStateStore.$subscribe((mutation, state) => {
  if (!isUserAdjustingVolume.value && state.playerState.volume != null && state.playerState.volume !== volume.value) {
    volume.value = state.playerState.volume
    logger.debug('[AudioPlayer] Volume updated from server', { volume: volume.value })
  }
})

// Format time in milliseconds to MM:SS
function formatTime(timeMs: number): string {
  const totalSeconds = Math.floor(timeMs / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
}

// Handle progress bar click
function handleProgressClick(event: MouseEvent) {
  if (!progressBarRef.value) return
  const rect = progressBarRef.value.getBoundingClientRect()
  const offsetX = event.clientX - rect.left
  const percentage = offsetX / rect.width
  const seekTime = duration.value * percentage
  seekTo(seekTime)
}

// Debounce timer for volume changes
let volumeDebounceTimer: ReturnType<typeof setTimeout> | null = null

// Handle volume change with debouncing to avoid too many API calls
function handleVolumeChange(event: Event) {
  const target = event.target as HTMLInputElement
  const newVolume = parseInt(target.value)

  // Mark that user is adjusting volume to prevent server updates from interfering
  isUserAdjustingVolume.value = true

  // Update UI immediately for smooth slider movement
  volume.value = newVolume

  // Clear existing timer
  if (volumeDebounceTimer) {
    clearTimeout(volumeDebounceTimer)
  }

  // Debounce API call by 300ms
  volumeDebounceTimer = setTimeout(async () => {
    try {
      logger.debug('[AudioPlayer] Setting volume via API', { volume: newVolume })
      await apiService.setVolume(newVolume)
      logger.debug('[AudioPlayer] Volume set successfully', { volume: newVolume })
    } catch (error) {
      logger.error('[AudioPlayer] Failed to set volume', { volume: newVolume, error })
      // Revert to previous volume on error
      if (playerState.value?.volume != null) {
        volume.value = playerState.value.volume
      }
    } finally {
      // Allow server updates again after a short delay (500ms after API call completes)
      setTimeout(() => {
        isUserAdjustingVolume.value = false
      }, 500)
    }
  }, 300)
}

// Smooth position interpolation
function startSmoothAnimation() {
  if (animationFrame.value) {
    cancelAnimationFrame(animationFrame.value)
  }
  
  const animate = () => {
    if (!isPlaying.value || isSeekInProgress.value) {
      animationFrame.value = null
      return
    }
    
    const now = Date.now()
    const timeSinceLastUpdate = now - lastServerUpdate.value
    const interpolatedTime = lastServerTime.value + timeSinceLastUpdate  // All in milliseconds

    // Only update if interpolation seems reasonable (within 2 seconds of last server update)
    if (timeSinceLastUpdate < 2000) {  // 2000ms = 2 seconds
      currentTime.value = interpolatedTime
    }
    
    animationFrame.value = requestAnimationFrame(animate)
  }
  
  animationFrame.value = requestAnimationFrame(animate)
}

function stopSmoothAnimation() {
  if (animationFrame.value) {
    cancelAnimationFrame(animationFrame.value)
    animationFrame.value = null
  }
}

// Watch for position updates from server
let lastServerPosition = 0
const unwatchPosition = serverStateStore.$subscribe((mutation, state) => {
  if (state.playerState.position_ms !== lastServerPosition) {
    lastServerPosition = state.playerState.position_ms
    
    // Only update if we're not currently seeking
    if (!isSeekInProgress.value) {
      const newTime = state.playerState.position_ms  // Keep in milliseconds
      lastServerTime.value = newTime
      lastServerUpdate.value = Date.now()
      currentTime.value = newTime

      // Start smooth animation if playing
      if (state.playerState.is_playing) {
        startSmoothAnimation()
      } else {
        stopSmoothAnimation()
      }
    }
  }
  
  // Handle play/pause state changes
  const nowPlaying = Boolean(state.playerState.is_playing)
  if (nowPlaying !== isPlaying.value) {
    if (nowPlaying) {
      startSmoothAnimation()
    } else {
      stopSmoothAnimation()
    }
  }
})

// Player control methods
async function togglePlayPause() {
  // Save current state for rollback on error
  const previousState = { ...playerState.value }
  const wasPlaying = isPlaying.value

  try {
    // OPTIMISTIC UPDATE: Update UI immediately for instant feedback
    // This will be confirmed or rolled back based on server response
    const optimisticState = {
      ...previousState,
      is_playing: !wasPlaying
    }
    logger.debug('[AudioPlayerSimplified] Optimistic update:', { was: wasPlaying, now: !wasPlaying })
    serverStateStore.handlePlayerState(optimisticState)

    // Make API call
    let response
    if (wasPlaying) {
      response = await apiService.pausePlayer()
      logger.debug('[AudioPlayerSimplified] Pause requested')
    } else {
      response = await apiService.playPlayer()
      logger.debug('[AudioPlayerSimplified] Play requested')
    }

    // CONFIRM with server response (may include additional state updates)
    // Note: apiService returns direct PlayerState (already unwrapped by ApiResponseHandler)
    if (response && typeof response === 'object') {
      logger.debug('[AudioPlayerSimplified] Confirming state with HTTP response:', response)
      serverStateStore.handlePlayerState(response)
    }
  } catch (error) {
    logger.error('[AudioPlayerSimplified] Failed to toggle play/pause:', error)

    // ROLLBACK: Restore previous state on error
    logger.warn('[AudioPlayerSimplified] Rolling back to previous state due to error')
    serverStateStore.handlePlayerState(previousState)

    // TODO: Show error notification to user (toast/snackbar)
    // Example: notificationStore.showError('Failed to toggle playback')
  }
}

async function previous() {
  try {
    const response = await apiService.previousTrack()
    logger.debug('[AudioPlayerSimplified] Previous track requested')

    // Update store immediately with HTTP response
    // Note: apiService returns direct PlayerState (already unwrapped by ApiResponseHandler)
    if (response && typeof response === 'object') {
      logger.debug('[AudioPlayerSimplified] Updating player state from previous response:', response)
      serverStateStore.handlePlayerState(response)
    }
  } catch (error) {
    logger.error('[AudioPlayerSimplified] Failed to go to previous track:', error)
    // TODO: Show error notification to user
  }
}

async function next() {
  try {
    const response = await apiService.nextTrack()
    logger.debug('[AudioPlayerSimplified] Next track requested')

    // Update store immediately with HTTP response
    // Note: apiService returns direct PlayerState (already unwrapped by ApiResponseHandler)
    if (response && typeof response === 'object') {
      logger.debug('[AudioPlayerSimplified] Updating player state from next response:', response)
      serverStateStore.handlePlayerState(response)
    }
  } catch (error) {
    logger.error('[AudioPlayerSimplified] Failed to go to next track:', error)
    // TODO: Show error notification to user
  }
}

async function seekTo(timeMs: number) {
  try {
    // Client-side validation for seek duration (max 24 hours in milliseconds)
    const maxDurationMs = 86400000 // 24 hours in milliseconds
    if (timeMs < 0 || timeMs > maxDurationMs) {
      logger.error('[AudioPlayerSimplified] Seek position out of bounds', {
        timeMs,
        maxDurationMs
      })
      return
    }

    // Stop smooth animation during seek
    stopSmoothAnimation()

    // Optimistic update for immediate UI feedback
    isSeekInProgress.value = true
    currentTime.value = timeMs  // Already in milliseconds
    lastServerTime.value = timeMs
    lastServerUpdate.value = Date.now()

    // Send seek request to server - already in milliseconds
    await apiService.seekPlayer(Math.floor(timeMs))

    logger.debug('[AudioPlayerSimplified] Seek completed', {
      timeMs
    })
    
    // Clear seek flag after a short delay to allow server update to come through
    setTimeout(() => {
      isSeekInProgress.value = false
      // Restart smooth animation if playing
      if (isPlaying.value) {
        startSmoothAnimation()
      }
    }, 500)
    
  } catch (error) {
    logger.error('[AudioPlayerSimplified] Failed to seek:', error)
    
    // Revert optimistic update on error
    const fallbackTime = playerState.value?.position_ms || 0  // Already in milliseconds
    currentTime.value = fallbackTime
    lastServerTime.value = fallbackTime
    lastServerUpdate.value = Date.now()
    isSeekInProgress.value = false
    
    // Restart smooth animation if playing
    if (isPlaying.value) {
      startSmoothAnimation()
    }
  }
}

// Lifecycle - enhanced with unified store initialization
onMounted(async () => {
  logger.debug('[AudioPlayer] Component mounted - initializing unified integration')
  
  // Initialize unified store if not already done
  if (!unifiedStore.isInitialized) {
    try {
      await unifiedStore.initialize()
      logger.debug('[AudioPlayer] Unified store initialized')
    } catch (error) {
      logger.warn('[AudioPlayer] Failed to initialize unified store:', error)
      // Continue anyway - server state store will still work
    }
  }
  
  // Initialize position from current player state
  if (playerState.value?.position_ms) {
    const initialTime = playerState.value.position_ms  // Keep in milliseconds
    currentTime.value = initialTime
    lastServerTime.value = initialTime
    lastServerUpdate.value = Date.now()
    lastServerPosition = playerState.value.position_ms

    // Start smooth animation if already playing
    if (playerState.value.is_playing) {
      startSmoothAnimation()
    }
  }
  
  // Subscribe to playlists room for player state updates
  try {
    await serverStateStore.subscribeToPlaylists()
    logger.debug('[AudioPlayer] Subscribed to playlists room')
    
    await serverStateStore.requestInitialPlayerState()
    logger.debug('[AudioPlayer] Requested initial player state')
    
    // Set up periodic state sync as fallback
    const syncInterval = setInterval(async () => {
      try {
        if (!playerState.value?.active_track && serverStateStore.isConnected) {
          await serverStateStore.requestInitialPlayerState()
        }
      } catch (error) {
        logger.debug('[AudioPlayer] Periodic sync failed:', error)
      }
    }, 5000)
    
    // Add cleanup to unmount
    onUnmounted(() => {
      clearInterval(syncInterval)
      stopSmoothAnimation()
      unwatchPosition()
      unwatchVolume()
      if (volumeDebounceTimer) {
        clearTimeout(volumeDebounceTimer)
        volumeDebounceTimer = null
      }
      logger.debug('[AudioPlayer] Component unmounted with cleanup')
    })
    
  } catch (error) {
    logger.error('[AudioPlayer] Failed to subscribe to playlists room:', error)
  }
})

// onUnmounted cleanup is now handled in the try block above
</script>