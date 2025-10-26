<template>
  <div class="flex flex-col items-center space-y-2">
    <h2 :class="['text-xl font-semibold', 'text-onBackground']">
      {{ track?.title || t('audio.noTrackSelected') }}
    </h2>
    <!-- Affichage du nom de playlist si disponible -->
    <div v-if="playlistTitle" :class="['text-md', 'text-disabled']">
      {{ playlistTitle }}
    </div>
    <!-- Informations durée -->
    <div :class="['flex items-center space-x-4 text-sm', 'text-disabled']">
      <span>{{ t('audio.duration') }}: {{ duration ? formatDurationMs(duration) : (track && track.duration_ms ? formatDurationMs(track.duration_ms) : '00:00') }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
// Using theme tokens directly in class bindings
/**
 * TrackInfo Component
 *
 * Displays metadata about the currently selected track.
 * Shows title, filename, duration, and play count.
 */

import type { Track } from '../files/types'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

defineProps<{
  /** The track to display information for */
  track: Track | null | undefined
  /** The playlist title to display */
  playlistTitle?: string | null
  /** The actual duration from the audio player (in milliseconds) */
  duration?: number
}>()

/**
 * Format duration in milliseconds to MM:SS format
 * @param {string|number} duration - Duration in milliseconds as string or number
 * @returns {string} Formatted duration
 */
function formatDurationMs(duration: string | number): string {
  const ms = typeof duration === 'string' ? parseInt(duration) : duration
  if (isNaN(ms) || ms < 0) return '00:00'
  const totalSeconds = Math.floor(ms / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const remainingSeconds = totalSeconds % 60
  return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`
}
</script>
