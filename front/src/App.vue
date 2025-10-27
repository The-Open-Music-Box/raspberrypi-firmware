<template>
  <div id="app" class="min-h-screen" style="background: var(--background); padding: 24px;">
    <div class="container mx-auto max-w-4xl">
      <div
        v-if="socketError"
        class="error-banner show mb-4"
        role="alert"
      >
        <span style="font-size: 18px;">⚠️</span>
        <div>
          <strong class="font-bold">{{ t('common.socketError') }}</strong>
          <span class="block sm:inline"> {{ t('common.fallbackToMock') }}</span>
        </div>
      </div>

      <HeaderNavigation />
      <router-view />
    </div>
  </div>
</template>

<script setup>
/**
 * App Component - Application Root
 *
 * The main entry point for the application.
 * Sets up global structure and socket connection state.
 */
import HeaderNavigation from './components/HeaderNavigation.vue'
import { onMounted, onUnmounted, ref, getCurrentInstance } from 'vue'
import { useI18n } from 'vue-i18n'
import { logger } from '@/utils/logger'

const { t } = useI18n()
const { proxy } = getCurrentInstance()
const socketError = ref(false)



/**
 * Set up socket event listeners
 */
const setupSocketListeners = () => {
  proxy.$socketService.on('response', (data) => {
    logger.debug('Received response from server', { data }, 'App')
  })

  proxy.$socketService.on('connect_error', (error) => {
    logger.error('Socket connection error', { error }, 'App')
    socketError.value = true
  })

  proxy.$socketService.on('connect', () => {
    logger.info('Socket connected successfully', {}, 'App')
    socketError.value = false
  })

  proxy.$socketService.on('disconnect', (reason) => {
    logger.warn('Socket disconnected', { reason }, 'App')
    socketError.value = true
  })
}

// Component lifecycle hooks
onMounted(() => {
  setupSocketListeners()
})

onUnmounted(() => {
  if (proxy.$socketService.disconnect) {
    proxy.$socketService.disconnect()
  }
})
</script>

<style lang="scss">
#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Inter, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: var(--text);
}

.error-banner {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
  padding: 12px 16px;
  border-radius: 8px;
  display: none;
  align-items: center;
  gap: 8px;
}

.error-banner.show {
  display: flex;
}
</style>