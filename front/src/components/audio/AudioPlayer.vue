<template>
  <div v-if="!serverStateStore" class="w-full max-w-xl mx-auto p-4 text-center text-gray-500">
    Loading player...
  </div>
  <div v-else class="w-full max-w-xl mx-auto">
    <div class="bg-surface border-border border-b rounded-t-xl p-4 pb-6 sm:p-10 sm:pb-8 lg:p-6 xl:p-10 xl:pb-8 space-y-6 sm:space-y-8 lg:space-y-6 xl:space-y-8 items-center">
      <TrackInfo 
        :track="currentTrack || undefined" 
        :playlistTitle="playerState?.active_playlist_title"
        :duration="duration"
      />
      <ProgressBar
        :currentTime="currentTime"
        :duration="duration"
        @seek="seekTo"
      />
    </div>
    <div class="bg-background text-disabled rounded-b-xl flex items-center justify-center w-full">
      <div class="w-full max-w-[380px] mx-auto flex justify-center">
        <PlaybackControls
          :isPlaying="isPlaying"
          :canPrevious="playerState?.can_prev || false"
          :canNext="playerState?.can_next || false"
          @toggle-play-pause="togglePlayPause"
          @previous="previous"
          @next="next"
        />
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
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import TrackInfo from './TrackInfo.vue'
import ProgressBar from './ProgressBar.vue'
import PlaybackControls from './PlaybackControls.vue'
import type { Track, PlayList } from '../files/types'
import { useServerStateStore } from '@/stores/serverStateStore'
import { useUnifiedPlaylistStore } from '@/stores/unifiedPlaylistStore'
import { storeToRefs } from 'pinia'
import apiService from '@/services/apiService'
import { logger } from '@/utils/logger'
import { getTrackNumber, getTrackDurationMs } from '@/utils/trackFieldAccessor'

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
      logger.debug('[AudioPlayer] Component unmounted with cleanup')
    })
    
  } catch (error) {
    logger.error('[AudioPlayer] Failed to subscribe to playlists room:', error)
  }
})

// onUnmounted cleanup is now handled in the try block above
</script>