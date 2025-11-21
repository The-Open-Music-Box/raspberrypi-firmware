<template>
  <div class="space-y-2">
    <div class="relative">
      <div
        class="bg-background rounded-full overflow-hidden cursor-pointer select-none"
        @click="handleClick"
        @mousedown.prevent="onMouseDown"
        @touchstart.prevent="onTouchStart"
      >
        <div
          class="bg-primary h-2"
          :style="{ width: `${progressPercentage}%` }"
          role="progressbar"
          aria-label="music progress"
          :aria-valuenow="displayTime"
          :aria-valuemin="0"
          :aria-valuemax="duration"
        ></div>
      </div>
      <div
        class="absolute top-1/2 transform -translate-y-1/2"
        :style="{ left: `${progressPercentage}%` }"
      >
        <div class="w-4 h-4 flex items-center justify-center bg-surface rounded-full shadow">
          <div class="w-1.5 h-1.5 bg-primary rounded-full ring-1 ring-inset ring-border"></div>
        </div>
      </div>
    </div>
    <div class="flex justify-between text-sm leading-6 font-medium tabular-nums">
      <div class="text-primary">{{ formatTime(displayTime) }}</div>
      <div class="text-disabled">{{ formatTime(duration) }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * ProgressBar Component
 *
 * Visual representation of audio playback progress.
 * Shows current time, total duration, and a draggable progress indicator.
 */
import { computed, ref, onBeforeUnmount } from 'vue'

const props = defineProps<{
  /** Current playback time in milliseconds */
  currentTime: number;
  /** Total duration of the track in milliseconds */
  duration: number;
}>()

const emit = defineEmits<{
  /** Emitted when user seeks to a new position (in milliseconds) */
  (e: 'seek', time: number): void;
}>()

/** Calculate progress percentage based on current time and duration */
const isDragging = ref(false)
const previewTime = ref<number | null>(null)
const ignoreNextClick = ref(false)

const displayTime = computed(() => (isDragging.value && previewTime.value !== null) ? previewTime.value : props.currentTime)
const progressPercentage = computed(() => {
  const percentage = props.duration > 0 ? (displayTime.value / props.duration) * 100 : 0
  return percentage
})

/**
 * Format time in milliseconds to MM:SS display format
 * @param {number} time - Time in milliseconds
 * @returns {string} Formatted time string
 */
const formatTime = (time: number) => {
  const totalSeconds = Math.floor(time / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = Math.floor(totalSeconds % 60).toString().padStart(2, '0')
  return `${minutes}:${seconds}`
}

/**
 * Handle click on the progress bar
 * @param {MouseEvent} event - The click event
 */
const handleClick = (event: MouseEvent) => {
  if (ignoreNextClick.value) {
    // Skip the click triggered after drag end
    ignoreNextClick.value = false
    return
  }
  const target = event.currentTarget as HTMLElement;
  const rect = target.getBoundingClientRect();
  const offsetX = event.clientX - rect.left;
  const percentage = offsetX / rect.width;
  const seekTime = props.duration * percentage;
  
  // Progress bar clicked at ${seekTime}s
  
  emit('seek', seekTime);
}

function positionToTime(clientX: number, target: HTMLElement): number {
  const rect = target.getBoundingClientRect()
  const offsetX = Math.max(0, Math.min(clientX - rect.left, rect.width))
  const percentage = rect.width > 0 ? offsetX / rect.width : 0
  return props.duration * percentage
}

  /* eslint-disable @typescript-eslint/no-explicit-any */
let moveListener: any = null
let upListener: any = null
  /* eslint-enable @typescript-eslint/no-explicit-any */

const onMouseDown = (event: MouseEvent) => {
  const target = event.currentTarget as HTMLElement
  isDragging.value = true
  previewTime.value = positionToTime(event.clientX, target)

  moveListener = (e: MouseEvent) => {
    previewTime.value = positionToTime(e.clientX, target)
  }
  upListener = () => {
    isDragging.value = false
    if (previewTime.value !== null) {
      // Drag ended at ${previewTime.value}s
      emit('seek', previewTime.value)
    }
    previewTime.value = null
    ignoreNextClick.value = true
    removeMouseListeners()
  }
  window.addEventListener('mousemove', moveListener)
  window.addEventListener('mouseup', upListener)
}

function removeMouseListeners() {
  if (moveListener) window.removeEventListener('mousemove', moveListener)
  if (upListener) window.removeEventListener('mouseup', upListener)
  moveListener = null
  upListener = null
}

const onTouchStart = (event: TouchEvent) => {
  const target = event.currentTarget as HTMLElement
  isDragging.value = true
  const touch = event.touches[0]
  previewTime.value = positionToTime(touch.clientX, target)

  const onTouchMove = (e: TouchEvent) => {
    const t = e.touches[0]
    previewTime.value = positionToTime(t.clientX, target)
  }
  const onTouchEnd = () => {
    isDragging.value = false
    if (previewTime.value !== null) {
      // Touch ended at ${previewTime.value}s
      emit('seek', previewTime.value)
    }
    previewTime.value = null
    ignoreNextClick.value = true
    window.removeEventListener('touchmove', onTouchMove)
    window.removeEventListener('touchend', onTouchEnd)
    window.removeEventListener('touchcancel', onTouchEnd)
  }
  window.addEventListener('touchmove', onTouchMove)
  window.addEventListener('touchend', onTouchEnd)
  window.addEventListener('touchcancel', onTouchEnd)
}

onBeforeUnmount(() => {
  removeMouseListeners()
})
</script>
