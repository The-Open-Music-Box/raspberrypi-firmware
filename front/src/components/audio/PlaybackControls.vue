<template>
  <div class="flex items-center justify-between w-full max-w-full gap-x-0 sm:gap-x-10 px-4 sm:px-6">
    <!-- Groupe gauche -->
    <div class="flex items-center gap-x-0 sm:gap-x-6">
      <button
        type="button"
        class="block"
        :class="{ 'opacity-50 cursor-not-allowed': !props.canPrevious }"
        :disabled="!props.canPrevious"
        :aria-label="t('player.previous')"
        @click="handlePrevious()"
      >
        <svg width="24" height="24" fill="none">
          <path
            d="m10 12 8-6v12l-8-6Z"
            fill="currentColor"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
          <path
            d="M6 6v12"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </button>
      <!-- Rewind button removed per spec -->
    </div>
    <!-- Bouton central -->
    <button
      type="button"
      class="bg-surface text-onBackground -my-2 mx-auto w-16 h-16 sm:w-20 sm:h-20 rounded-full ring-1 ring-border shadow-md flex items-center justify-center"
      :aria-label="t('player.playPause')"
      @click="$emit('togglePlayPause')"
    >
      <svg v-if="isPlaying" width="30" height="32" fill="currentColor">
        <rect x="6" y="4" width="4" height="24" rx="2" />
        <rect x="20" y="4" width="4" height="24" rx="2" />
      </svg>
      <svg v-else width="30" height="32" fill="currentColor">
        <polygon points="5,3 25,16 5,29" />
      </svg>
    </button>
    <!-- Groupe droit -->
    <div class="flex items-center gap-x-0 sm:gap-x-6">
      <!-- Skip 10s button removed per spec -->
      <button
        type="button"
        class="block"
        :class="{ 'opacity-50 cursor-not-allowed': !props.canNext }"
        :disabled="!props.canNext"
        :aria-label="t('player.next')"
        @click="handleNext()"
      >
        <svg width="24" height="24" fill="none">
          <path
            d="M14 12 6 6v12l8-6Z"
            fill="currentColor"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
          <path
            d="M18 6v12"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * PlaybackControls Component
 *
 * Provides a set of controls for audio playback including:
 * - Play/pause button
 * - Previous/next track buttons
 * - Previous/next buttons (rewind/skip removed)
 */

import { useI18n } from 'vue-i18n'
import { logger } from '@/utils/logger'

const { t } = useI18n()

const props = defineProps<{
  /** Whether audio is currently playing */
  isPlaying: boolean
  /** Whether previous track is available */
  canPrevious?: boolean
  /** Whether next track is available */
  canNext?: boolean
}>()

const emit = defineEmits<{
  /** Emitted when play/pause button is clicked */
  (e: 'togglePlayPause'): void;
  /** Emitted when previous track button is clicked */
  (e: 'previous'): void;
  /** Emitted when next track button is clicked */
  (e: 'next'): void;
  // rewind/skip removed
}>()

const handlePrevious = () => {
  if (!props.canPrevious) {
    logger.debug('Previous button clicked but disabled', {}, 'PlaybackControls')
    return
  }
  logger.debug('Previous button clicked', {}, 'PlaybackControls')
  emit('previous')
}

const handleNext = () => {
  if (!props.canNext) {
    logger.debug('Next button clicked but disabled', {}, 'PlaybackControls')
    return
  }
  logger.debug('Next button clicked', {}, 'PlaybackControls')
  emit('next')
}
</script>
