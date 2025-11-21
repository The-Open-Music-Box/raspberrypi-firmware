<template>
  <div v-if="visible" class="nfc-associate-dialog-overlay" @click="handleBackdropClick">
    <div class="nfc-associate-dialog" @click.stop>
      <div class="dialog-header">
        <h3>{{ $t('nfc.associate.title') }}</h3>
        <button class="close-btn" @click="handleClose" :aria-label="$t('common.close')">
          <i class="fas fa-times"></i>
        </button>
      </div>

      <div class="dialog-content">
        <!-- Idle State -->
        <div v-if="state === 'idle'" class="state-content">
          <div class="nfc-icon">
            <i class="fas fa-wifi"></i>
          </div>
          <p>{{ $t('nfc.associate.ready') }}</p>
          <button class="btn btn-primary" @click="startAssociation">
            {{ $t('nfc.associate.start') }}
          </button>
        </div>

        <!-- Waiting State -->
        <div v-else-if="state === 'waiting'" class="state-content">
          <div class="nfc-icon scanning">
            <i class="fas fa-wifi"></i>
          </div>
          <p>{{ $t('nfc.associate.waiting') }}</p>
          <div v-if="playlistTitle" class="playlist-info">
            <strong>{{ $t('nfc.associate.forPlaylist') }}:</strong>
            <div class="playlist-title">{{ playlistTitle }}</div>
          </div>
          <div v-if="countdown > 0" class="countdown">
            {{ $t('nfc.associate.timeout', { seconds: countdown }) }}
          </div>
          <button class="btn btn-secondary" @click="cancelAssociation">
            {{ $t('common.cancel') }}
          </button>
        </div>

        <!-- Success State -->
        <div v-else-if="state === 'success'" class="state-content">
          <div class="nfc-icon success">
            <i class="fas fa-check-circle"></i>
          </div>
          <p>{{ $t('nfc.associate.success') }}</p>
          <button class="btn btn-primary" @click="handleClose">
            {{ $t('common.close') }}
          </button>
        </div>

        <!-- Already Associated (Duplicate) State -->
        <div v-else-if="state === 'already_associated'" class="state-content">
          <div class="nfc-icon warning">
            <i class="fas fa-exclamation-triangle"></i>
          </div>
          <p>{{ $t('nfc.associate.duplicate') }}</p>
          <div v-if="existingPlaylistInfo" class="existing-playlist-info">
            <p><strong>{{ $t('nfc.associate.existingPlaylist') }}:</strong> {{ existingPlaylistInfo.title }}</p>
          </div>
          <div class="button-group">
            <button class="btn btn-secondary" @click="handleClose">
              {{ $t('common.cancel') }}
            </button>
            <button class="btn btn-warning" @click="replaceAssociation">
              {{ $t('nfc.associate.replace') }}
            </button>
          </div>
        </div>

        <!-- Error States -->
        <div v-else-if="state === 'error' || state === 'hardware_error'" class="state-content">
          <div class="nfc-icon error">
            <i class="fas fa-exclamation-circle"></i>
          </div>
          <p>{{ message || $t('nfc.associate.error') }}</p>
          <div class="button-group">
            <button class="btn btn-secondary" @click="handleClose">
              {{ $t('common.close') }}
            </button>
            <button class="btn btn-primary" @click="retryAssociation">
              {{ $t('common.retry') }}
            </button>
          </div>
        </div>

        <!-- Cancelled State -->
        <div v-else-if="state === 'cancelled'" class="state-content">
          <div class="nfc-icon">
            <i class="fas fa-ban"></i>
          </div>
          <p>{{ $t('nfc.associate.cancelled') }}</p>
          <button class="btn btn-primary" @click="handleClose">
            {{ $t('common.close') }}
          </button>
        </div>

        <!-- Timeout State -->
        <div v-else-if="state === 'timeout'" class="state-content">
          <div class="nfc-icon warning">
            <i class="fas fa-clock"></i>
          </div>
          <p>{{ $t('nfc.associate.timedOut') }}</p>
          <div class="button-group">
            <button class="btn btn-secondary" @click="handleClose">
              {{ $t('common.close') }}
            </button>
            <button class="btn btn-primary" @click="retryAssociation">
              {{ $t('common.retry') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import socketService from '@/services/socketService'
import apiService from '@/services/apiService'
import { SOCKET_EVENTS } from '@/constants/apiRoutes'
import { NfcAssociationStateData, NfcTagDuplicateData } from '@/types/socket'

// Props and emits
interface Props {
  visible: boolean
  playlistId: string
  playlistTitle?: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:visible': [value: boolean]
  'success': [playlistId: string]
}>()

const { t } = useI18n()

// State management
type NfcState = 'idle' | 'waiting' | 'success' | 'already_associated' | 'error' | 'hardware_error' | 'cancelled' | 'timeout'

const state = ref<NfcState>('idle')
const message = ref('')
const countdown = ref(0)
const isOverrideMode = ref(false)
const existingPlaylistInfo = ref<{ id: string; title: string } | null>(null)
const detectedTagId = ref<string | null>(null)  // Store the tag_id when duplicate is detected

// Countdown timer
let countdownInterval: ReturnType<typeof setInterval> | null = null


// Countdown management
function startCountdown(expiresAt: number) {
  stopCountdown()

  const updateCountdown = () => {
    const now = Date.now() / 1000
    const remaining = Math.max(0, Math.ceil(expiresAt - now))
    countdown.value = remaining

    if (remaining <= 0) {
      stopCountdown()
    }
  }

  updateCountdown()
  countdownInterval = setInterval(updateCountdown, 1000)
}

function stopCountdown() {
  if (countdownInterval) {
    clearInterval(countdownInterval)
    countdownInterval = null
  }
  countdown.value = 0
}

// Socket.IO event handlers
function setupSocketHandlers() {
  socketService.on(SOCKET_EVENTS.NFC_ASSOCIATION_STATE, (data: unknown) => {
    const stateData = data as NfcAssociationStateData

    // Only process events for our current playlist
    if (stateData.playlist_id !== props.playlistId) {
      return
    }

    switch (stateData.state) {
      case 'activated':
      case 'waiting': // Handle both 'activated' and 'waiting' states the same way
        state.value = 'waiting'
        emit('update:visible', true) // Open dialog when NFC association is active
        if (stateData.expires_at) {
          startCountdown(stateData.expires_at)
        }
        break
      case 'success':
        state.value = 'success'
        message.value = stateData.message || t('nfc.associate.success')
        stopCountdown()
        stopAssociationPolling()
        // Emit success event to parent for playlist update
        emit('success', props.playlistId)
        // Auto-close dialog after showing success for 3 seconds
        setTimeout(() => {
          handleClose()
        }, 3000)
        break
      case 'duplicate':
        state.value = 'already_associated'
        existingPlaylistInfo.value = stateData.existing_playlist || null
        detectedTagId.value = stateData.tag_id || null  // Store tag_id for override
        message.value = stateData.message || t('nfc.associate.duplicate')
        break
      case 'timeout':
        state.value = 'timeout'
        message.value = stateData.message || t('nfc.associate.timedOut')
        stopCountdown()
        break
      case 'cancelled':
        state.value = 'cancelled'
        message.value = stateData.message || t('nfc.associate.cancelled')
        stopCountdown()
        break
      case 'error':
        state.value = 'error'
        message.value = stateData.message || t('nfc.associate.error')
        stopCountdown()
        break
    }
  })

  socketService.on('nfc_tag_duplicate', (data: unknown) => {
    const duplicateData = data as NfcTagDuplicateData
    existingPlaylistInfo.value = duplicateData.existing_playlist
  })

}

function cleanupSocketHandlers() {
  socketService.off(SOCKET_EVENTS.NFC_ASSOCIATION_STATE)
  socketService.off('nfc_tag_duplicate')
}

// Polling mechanism as fallback for socket issues
let associationPollInterval: ReturnType<typeof setInterval> | null = null

function startAssociationPolling() {
  if (associationPollInterval) return
  
  associationPollInterval = setInterval(async () => {
    try {
      const status = await apiService.getNfcStatus()
      
      // Check if there's an active session for our playlist
      if (status.active_sessions && status.active_sessions.length > 0) {
        const ourSession = status.active_sessions.find(s => s.playlist_id === props.playlistId)
        if (ourSession) {
          
          if (ourSession.state === 'success' && state.value === 'waiting') {
            state.value = 'success'
            message.value = t('nfc.associate.success')
            stopAssociationPolling()
            // Emit success event to parent for playlist update
            emit('success', props.playlistId)
            setTimeout(() => {
              handleClose()
            }, 3000)
          } else if (ourSession.state === 'duplicate' && state.value === 'waiting') {
            state.value = 'already_associated'
            stopAssociationPolling()
          }
        }
      }
    } catch (error) {
    // Error handled silently
    }
  }, 1000)
}

function stopAssociationPolling() {
  if (associationPollInterval) {
    clearInterval(associationPollInterval)
    associationPollInterval = null
  }
}

// User actions
async function startAssociation() {
  state.value = 'waiting'
  try {
    // Use proper REST API call instead of Socket.IO event
    // Note: nfc_association_state events are emitted globally, so no room joining needed
    const result = await apiService.startNfcAssociation(props.playlistId)
    
    // Set up timeout countdown if we have expiration info
    if (result && result.timeout_ms) {
      const expiresAt = Date.now() / 1000 + (result.timeout_ms / 1000)
      startCountdown(expiresAt)
    }
    
    // Start polling as fallback if socket events don't work
    startAssociationPolling()
    
  } catch (error) {
    // Error handled silently
    state.value = 'error'
  }
}

async function cancelAssociation() {
  try {
    // Use proper REST API call instead of Socket.IO event
    await apiService.cancelNfcObservation()
  } catch (error) {
    // Error handled silently
  }
  state.value = 'cancelled'
}

function retryAssociation() {
  state.value = 'idle'
  message.value = ''
  existingPlaylistInfo.value = null
  detectedTagId.value = null
  isOverrideMode.value = false
}

function replaceAssociation() {
  isOverrideMode.value = true
  socketService.emit('override_nfc_tag', {
    playlist_id: props.playlistId,
    tag_id: detectedTagId.value  // Send the stored tag_id for immediate processing
  })
  state.value = 'waiting'
}

function handleBackdropClick() {
  if (state.value !== 'waiting') {
    handleClose()
  }
}

async function handleClose() {

  // Stop any ongoing association
  if (state.value === 'waiting') {
    try {
      await apiService.cancelNfcObservation()
    } catch (error) {
    // Error handled silently
    }
  }

  // Stop polling
  stopAssociationPolling()

  // Reset state
  state.value = 'idle'
  message.value = ''
  isOverrideMode.value = false
  existingPlaylistInfo.value = null
  detectedTagId.value = null
  stopCountdown()

  emit('update:visible', false)
}

// Check current association state when dialog opens
async function checkAssociationState() {
  try {
    socketService.emit(SOCKET_EVENTS.SYNC_REQUEST, {
      playlist_id: props.playlistId
    })
  } catch (error) {
    // Error handled silently
  }
}

// Lifecycle hooks
onMounted(() => {
  setupSocketHandlers()
  if (props.visible) {
    checkAssociationState()
  }
})

onUnmounted(() => {
  cleanupSocketHandlers()
  stopCountdown()
})

// Watch for visibility changes
watch(() => props.visible, (newVisible) => {
  if (newVisible) {
    // Reset state when dialog opens
    state.value = 'idle'
    message.value = ''
    isOverrideMode.value = false
    existingPlaylistInfo.value = null
    checkAssociationState()
  } else {
    // Clean up when dialog closes
    stopCountdown()
  }
})
</script>

<style scoped>
.nfc-associate-dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.nfc-associate-dialog {
  background: white;
  border-radius: 8px;
  padding: 24px;
  max-width: 400px;
  width: 90%;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.dialog-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: #666;
}

.close-btn:hover {
  color: #333;
}

.state-content {
  text-align: center;
}

.nfc-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.nfc-icon.scanning {
  animation: pulse 2s infinite;
}

.nfc-icon.success {
  color: #10b981;
}

.nfc-icon.warning {
  color: #f59e0b;
}

.nfc-icon.error {
  color: #ef4444;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.countdown {
  font-size: 14px;
  color: #666;
  margin: 8px 0;
}

.playlist-info {
  background: #e0f2fe;
  padding: 12px;
  border-radius: 6px;
  margin: 16px 0;
  font-size: 14px;
  text-align: center;
}

.playlist-title {
  font-size: 16px;
  font-weight: 600;
  margin-top: 8px;
  color: #0369a1;
}

.existing-playlist-info {
  background: #f3f4f6;
  padding: 12px;
  border-radius: 6px;
  margin: 12px 0;
  font-size: 14px;
}

.button-group {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  flex: 1;
}

.btn-primary {
  background: #3b82f6;
  color: white;
}

.btn-primary:hover {
  background: #2563eb;
}

.btn-secondary {
  background: #6b7280;
  color: white;
}

.btn-secondary:hover {
  background: #4b5563;
}

.btn-warning {
  background: #f59e0b;
  color: white;
}

.btn-warning:hover {
  background: #d97706;
}
</style>
