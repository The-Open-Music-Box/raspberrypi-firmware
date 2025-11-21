<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="uploadStore.isModalOpen"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
        @click="handleOverlayClick"
      >
        <div
          class="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-hidden"
          @click.stop
        >
          <!-- Header -->
          <div class="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
            <h3 class="text-lg font-medium text-gray-900">
              {{ t('upload.title') }}
            </h3>
            <button
              type="button"
              class="text-gray-400 hover:text-gray-600"
              @click="handleClose"
            >
              <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- Content -->
          <div class="px-6 py-4 max-h-[70vh] overflow-y-auto">
            <div v-if="!uploadStore.modalPlaylistId" class="text-center text-gray-500 py-8">
              No playlist selected for upload
            </div>
            <SimpleUploader
              v-else
              :playlist-id="uploadStore.modalPlaylistId"
              @upload-complete="handleUploadComplete"
              @upload-error="handleUploadError"
            />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
/* eslint-disable @typescript-eslint/no-unused-vars */
import { useI18n } from 'vue-i18n'
import { useUploadStore } from '@/stores/uploadStore'
import { useUnifiedPlaylistStore } from '@/stores/unifiedPlaylistStore'
import { logger } from '@/utils/logger'
import SimpleUploader from './SimpleUploader.vue'

// Props
interface Props {
  playlistId: string
}

defineProps<Props>()

// i18n
const { t } = useI18n()

// Stores
const uploadStore = useUploadStore()
const unifiedStore = useUnifiedPlaylistStore()

// Methods
function handleOverlayClick() {
  if (!uploadStore.isUploading) {
    handleClose()
  }
}

function handleClose() {
  uploadStore.closeUploadModal()
}

async function handleUploadComplete() {
  try {
    logger.debug('Upload completed, forcing unified store sync')
    
    // First, force sync the unified store to refresh playlist metadata (track counts)
    await unifiedStore.forceSync()
    logger.debug('Unified store sync completed after upload')
    
    // Then, specifically reload tracks for the uploaded playlist
    if (uploadStore.modalPlaylistId) {
      try {
        logger.debug('Forcing track reload for uploaded playlist', { playlistId: uploadStore.modalPlaylistId })
        
        // Clear existing tracks first to force a fresh reload
        await unifiedStore.clearPlaylistTracks(uploadStore.modalPlaylistId)
        
        // Then reload tracks from API
        await unifiedStore.loadPlaylistTracks(uploadStore.modalPlaylistId)
        
        logger.debug('Tracks successfully reloaded for uploaded playlist')
      } catch (error) {
        logger.warn('Failed to reload tracks for uploaded playlist', {
          playlistId: uploadStore.modalPlaylistId,
          error
        })
      }
    }
  } catch (error) {
    logger.error('Failed to sync unified store after upload', { error })
  } finally {
    // Always close the modal even if sync fails
    uploadStore.closeUploadModal()
  }
}

function handleUploadError(_error: unknown) {
  // Error is already logged by SimpleUploader
}
</script>

<style scoped>
/* Modal Overlay */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(0, 0, 0, 0.8), rgba(0, 0, 0, 0.6));
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 20px;
}

/* Modal Container */
.modal-container {
  background: linear-gradient(145deg, #ffffff, #f8f9fa);
  border-radius: 20px;
  box-shadow: 
    0 25px 80px rgba(0, 0, 0, 0.15),
    0 0 0 1px rgba(255, 255, 255, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
  max-width: 650px;
  width: 100%;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.3);
}

/* Modal Header */
.modal-header {
  padding: 20px 24px;
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.5rem;
  color: var(--color-text);
}

.close-button {
  background: none;
  border: none;
  color: var(--color-text-secondary);
  font-size: 1.5rem;
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.2s;
}

.close-button:hover {
  color: var(--color-danger);
}

/* Modal Body */
.modal-body {
  padding: 24px;
  flex: 1;
  overflow-y: auto;
}

/* Upload Dropzone */
.upload-dropzone {
  border: 2px dashed #e2e8f0;
  border-radius: 16px;
  padding: 48px 24px;
  text-align: center;
  transition: all 0.3s ease;
  cursor: pointer;
  background: linear-gradient(135deg, #f8fafc, #f1f5f9);
  position: relative;
  overflow: hidden;
}

.upload-dropzone:hover {
  border-color: #3b82f6;
  background: linear-gradient(135deg, #eff6ff, #dbeafe);
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(59, 130, 246, 0.15);
}

.upload-icon {
  font-size: 3.5rem;
  color: #3b82f6;
  margin-bottom: 20px;
  filter: drop-shadow(0 4px 8px rgba(59, 130, 246, 0.2));
}

.upload-or {
  margin: 16px 0;
  color: var(--color-text-secondary);
  font-size: 0.9rem;
}

.file-input-hidden {
  display: none;
}

.file-input-label {
  cursor: pointer;
}

/* Current File */
.current-file {
  margin-bottom: 24px;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.file-icon {
  font-size: 1.5rem;
  color: var(--color-primary);
}

.file-details {
  flex: 1;
}

.file-name {
  font-weight: 500;
  color: var(--color-text);
  margin-bottom: 4px;
}

.file-meta {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

/* Progress Bar */
.progress-wrapper {
  margin-top: 12px;
}

.progress-bar-container {
  height: 24px;
  background-color: var(--color-background-secondary);
  border-radius: 12px;
  overflow: hidden;
  position: relative;
}

.progress-bar-container.small {
  height: 8px;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary), var(--color-primary-light));
  transition: width 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 40px;
}

.progress-text {
  color: white;
  font-size: 0.85rem;
  font-weight: 500;
}

.progress-stats {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

/* Overall Progress */
.overall-progress {
  padding: 16px;
  background-color: var(--color-background-secondary);
  border-radius: 8px;
  margin-top: 16px;
}

.overall-progress h4 {
  margin: 0 0 12px 0;
  font-size: 0.9rem;
  color: var(--color-text-secondary);
}

.files-status {
  margin-top: 8px;
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

/* Error List */
.error-list {
  margin-top: 16px;
  padding: 12px;
  background-color: rgba(var(--color-danger-rgb), 0.1);
  border-radius: 8px;
  border: 1px solid rgba(var(--color-danger-rgb), 0.2);
}

.error-list h4 {
  margin: 0 0 8px 0;
  color: var(--color-danger);
  font-size: 0.9rem;
}

.error-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 0.85rem;
  color: var(--color-danger);
}

.error-item:last-child {
  margin-bottom: 0;
}

/* Success Message */
.success-message {
  text-align: center;
  padding: 24px;
  color: var(--color-success);
}

.success-message i {
  font-size: 3rem;
  margin-bottom: 12px;
}

/* Modal Footer */
.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid var(--color-border);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* Buttons */
.btn {
  padding: 8px 16px;
  border-radius: 6px;
  border: none;
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background-color: var(--color-primary);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: var(--color-primary-dark);
}

.btn-secondary {
  background-color: var(--color-background-secondary);
  color: var(--color-text);
}

.btn-secondary:hover:not(:disabled) {
  background-color: var(--color-background-tertiary);
}

/* Transitions */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.3s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-active .modal-container,
.modal-fade-leave-active .modal-container {
  transition: transform 0.3s ease;
}

.modal-fade-enter-from .modal-container {
  transform: scale(0.9);
}

.modal-fade-leave-to .modal-container {
  transform: scale(0.9);
}

/* Responsive */
@media (max-width: 640px) {
  .modal-container {
    max-height: 90vh;
  }
  
  .modal-body {
    padding: 16px;
  }
}
</style>
