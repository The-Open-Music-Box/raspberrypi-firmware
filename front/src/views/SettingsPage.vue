<template>
  <div class="settings-page max-w-2xl mx-auto py-10 px-4">
    <h1 class="text-2xl font-bold mb-6">{{ t('settings.title') }}</h1>
    <div class="space-y-6">
      <section>
        <h2 class="text-lg font-semibold mb-2">{{ t('settings.language') }}</h2>
        <select v-model="selectedLocale" @change="changeLocale" class="border rounded px-2 py-1">
          <option v-for="locale in availableLocales" :key="locale" :value="locale">
            {{ t('settings.locales.' + locale) }}
          </option>
        </select>
      </section>
      <section>
        <h2 class="text-lg font-semibold mb-2">{{ t('settings.systemStatus') }}</h2>
        <StatsInfo />
      </section>

      <!-- Real-time (Socket.IO) debug info -->
      <section>
        <h2 class="text-lg font-semibold mb-2">Real-time (Socket.IO)</h2>
        <div class="rounded border border-border p-4 bg-background">
          <div class="grid grid-cols-2 gap-3 text-sm">
            <div class="text-onBackground-medium">Connection</div>
            <div class="text-onBackground">{{ isConnected ? 'connected' : 'disconnected' }}</div>

            <div class="text-onBackground-medium">Socket ID</div>
            <div class="text-onBackground">{{ socketId || '-' }}</div>

            <div class="text-onBackground-medium">Last server_seq</div>
            <div class="text-onBackground">{{ lastServerSeq }}</div>

            <div class="text-onBackground-medium">Last event</div>
            <div class="text-onBackground">{{ lastEventName || '-' }}</div>

            <div class="text-onBackground-medium">Last playlist_id</div>
            <div class="text-onBackground">{{ lastPlaylistId || '-' }}</div>

            <div class="text-onBackground-medium">Last timestamp</div>
            <div class="text-onBackground">{{ lastTimestamp ? new Date(lastTimestamp * 1000).toLocaleString() : '-' }}</div>
          </div>

          <div class="mt-3">
            <button class="text-primary underline text-sm" @click="showPayload = !showPayload">
              {{ showPayload ? 'Hide' : 'Show' }} last payload
            </button>
            <pre v-if="showPayload" class="mt-2 text-xs overflow-auto max-h-64 bg-surface p-2 rounded">
{{ formattedPayload }}
            </pre>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
/* eslint-disable @typescript-eslint/no-explicit-any */
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import StatsInfo from '../components/StatsInfo.vue'
import socketService from '@/services/socketService'
import { SOCKET_EVENTS } from '@/constants/apiRoutes'

const { t, locale, availableLocales } = useI18n()
const selectedLocale = ref(locale.value)

function changeLocale() {
  locale.value = selectedLocale.value
}

// Realtime debug state
const isConnected = ref(false)
const socketId = ref<string | null>(null)
const lastServerSeq = ref(0)
const lastEventName = ref<string | null>(null)
const lastPlaylistId = ref<string | null>(null)
const lastTimestamp = ref<number | null>(null)
const lastPayload = ref<any>(null)
const showPayload = ref(false)

const formattedPayload = computed(() => {
  try {
    return lastPayload.value ? JSON.stringify(lastPayload.value, null, 2) : '-'
  } catch {
    return String(lastPayload.value)
  }
})

function handleStateEvent(eventName: string, event: any) {
  lastEventName.value = eventName
  // Unified contract: wrapped events carry server_seq, playlist_id, timestamp, event_id, and data
  const payload = event && typeof event === 'object' && 'data' in event ? event : { data: event }
  lastPayload.value = payload
  if ('server_seq' in payload) lastServerSeq.value = payload.server_seq || lastServerSeq.value
  if ('playlist_id' in payload) lastPlaylistId.value = payload.playlist_id || lastPlaylistId.value
  if ('timestamp' in payload) lastTimestamp.value = payload.timestamp || lastTimestamp.value
}

function setupSocketDebug() {
  socketService.setupSocketConnection()

  // Connection lifecycle
  socketService.on('connect', () => {
    isConnected.value = true
    socketId.value = socketService.getSocketId()
  })
  socketService.on('disconnect', () => {
    isConnected.value = false
    socketId.value = null
  })

  // Wrapped state events
  socketService.on(SOCKET_EVENTS.STATE_PLAYLISTS, (event) => handleStateEvent('state:playlists', event as any))
  socketService.on(SOCKET_EVENTS.STATE_PLAYLIST, (event) => handleStateEvent('state:playlist', event as any))
  socketService.on(SOCKET_EVENTS.STATE_PLAYER, (event) => handleStateEvent('state:player', event as any))

  // Join playlists room for snapshots
  socketService.emit(SOCKET_EVENTS.JOIN_PLAYLISTS, {})
}

function cleanupSocketDebug() {
  socketService.off('state:playlists')
  socketService.off('state:playlist')
  socketService.off('state:player')
  socketService.off('connect')
  socketService.off('disconnect')
}

onMounted(setupSocketDebug)
onUnmounted(cleanupSocketDebug)
</script>

<style scoped>
.settings-page {
  background: var(--color-surface);
  border-radius: 1rem;
  box-shadow: 0 2px 8px var(--color-shadow);
}
</style>
