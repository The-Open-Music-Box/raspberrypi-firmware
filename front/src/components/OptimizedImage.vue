<template>
  <img
    :src="currentSrc"
    :alt="alt"
    :class="imageClass"
    @load="onLoad"
    @error="onError"
    ref="imageRef"
  />
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { supportsWebP, lazyLoadImage } from '@/utils/imageUtils'

interface Props {
  src: string
  alt: string
  lazy?: boolean
  webpSrc?: string
  class?: string
}

const props = withDefaults(defineProps<Props>(), {
  lazy: false,
  class: ''
})

const imageRef = ref<HTMLImageElement>()
const loaded = ref(false)
const error = ref(false)
const webpSupported = ref(false)

const currentSrc = computed(() => {
  if (error.value) return props.src
  if (props.webpSrc && webpSupported.value) return props.webpSrc
  return props.src
})

const imageClass = computed(() => {
  const baseClass = props.class
  const statusClass = loaded.value ? 'loaded' : 'loading'
  const lazyClass = props.lazy ? 'lazy' : ''
  return `${baseClass} ${statusClass} ${lazyClass}`.trim()
})

const onLoad = () => {
  loaded.value = true
}

const onError = () => {
  error.value = true
  loaded.value = true
}

onMounted(async () => {
  // Check WebP support
  webpSupported.value = await supportsWebP()
  
  // Setup lazy loading if enabled
  if (props.lazy && imageRef.value) {
    lazyLoadImage(imageRef.value, currentSrc.value)
  }
})
</script>

<style scoped>
.loading {
  opacity: 0;
  transition: opacity 0.3s ease;
}

.loaded {
  opacity: 1;
}

.lazy {
  background: #f0f0f0;
  min-height: 100px;
}
</style>
