<template>
  <div id="app" class="min-h-full">
    <div
      v-if="socketError"
      :class="['bg-error bg-opacity-10', 'border', 'border-error', 'text-error', 'px-4 py-3 rounded relative', 'mb-4']"
      role="alert"
    >
      <strong class="font-bold">{{ t('common.socketError') }}</strong>
      <span class="block sm:inline"> {{ t('common.fallbackToMock') }}</span>
    </div>
    
    <HeaderNavigation />
    <router-view />
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
import { colors } from '@/theme/colors'
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
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: v-bind('colors.light.onBackground')
}
</style>