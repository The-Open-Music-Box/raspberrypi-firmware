<template>
  <div class="simple-uploader">
    <!-- Upload Zone -->
    <div
      @dragover.prevent="handleDragOver"
      @dragleave.prevent="handleDragLeave"
      @drop.prevent="handleDrop"
      :class="[
        'border-2 border-dashed rounded-lg p-6 text-center transition-all duration-200',
        isDragging ? 'border-primary bg-primary bg-opacity-5' : 'border-gray-300',
        isUploading ? 'opacity-50 cursor-not-allowed' : 'hover:border-primary hover:bg-gray-50 cursor-pointer'
      ]"
      @click="triggerFileInput"
    >
      <div class="flex flex-col items-center justify-center space-y-4">
        <!-- Upload Icon -->
        <div class="w-12 h-12 text-gray-400">
          <svg fill="none" stroke="currentColor" viewBox="0 0 48 48">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
            />
          </svg>
        </div>

        <!-- Upload Text -->
        <div class="text-center">
          <p class="text-lg font-medium text-gray-900">
            {{ t('upload.dragDropFiles') }}
          </p>
          <p class="text-sm text-gray-500 mt-1">
            {{ t('upload.orClickToBrowse') }}
          </p>
          <p class="text-xs text-gray-400 mt-2">
            Formats supportés: MP3, WAV, FLAC, OGG, M4A
          </p>
        </div>

        <!-- Browse Button -->
        <button
          type="button"
          :disabled="isUploading"
          class="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary-dark disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {{ t('upload.browseFiles') }}
        </button>
      </div>

      <!-- Hidden File Input -->
      <input
        ref="fileInput"
        type="file"
        multiple
        accept="audio/*"
        class="hidden"
        @change="handleFileSelect"
        :disabled="isUploading"
      />
    </div>

    <!-- Upload Progress -->
    <div v-if="isUploading || overallProgress > 0" class="mt-4">
      <div class="flex justify-between items-center mb-2">
        <span class="text-sm font-medium text-gray-900">
          {{ t('upload.uploading') }} {{ uploadFiles.length }} {{ t('upload.files') }}
        </span>
        <span class="text-sm text-gray-600">
          {{ Math.round(overallProgress) }}%
        </span>
      </div>
      
      <!-- Progress bar -->
      <div class="w-full bg-gray-200 rounded-full h-2 mb-2">
        <div 
          class="bg-blue-600 h-2 rounded-full transition-all duration-300"
          :style="{ width: `${overallProgress}%` }"
        ></div>
      </div>
      
      <!-- Cancel button -->
      <button
        v-if="isUploading"
        @click="cancelUpload"
        class="mt-2 px-3 py-1 bg-red-600 text-white rounded text-xs hover:bg-red-700"
      >
        {{ t('common.cancel') }}
      </button>
    </div>

    <!-- Upload Errors -->
    <div v-if="uploadErrors.length > 0" class="mt-4">
      <div class="bg-red-50 border border-red-200 rounded-md p-3">
        <h4 class="text-sm font-medium text-red-800 mb-2">{{ t('upload.errors') }}</h4>
        <ul class="text-xs text-red-700 space-y-1">
          <li v-for="(error, index) in uploadErrors" :key="index">{{ error }}</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import apiService from '@/services/apiService'
import { socketService } from '@/services/socketService'
import { logger } from '@/utils/logger'

const { t } = useI18n()

// Props
const props = defineProps<{
  playlistId: string
}>()

// Emits
const emit = defineEmits<{
  'upload-complete': []
  'upload-error': [error: unknown]
}>()

// Local state
const fileInput = ref<HTMLInputElement>()
const isDragging = ref(false)
const isUploading = ref(false)
const uploadFiles = ref<Array<{ file: File; progress: number; status: string; sessionId?: string }>>([])
const overallProgress = ref(0)
const uploadErrors = ref<string[]>([])

// Methods
const triggerFileInput = () => {
  if (!isUploading.value) {
    fileInput.value?.click()
  }
}

const handleDragOver = () => {
  isDragging.value = true
}

const handleDragLeave = () => {
  isDragging.value = false
}

const handleDrop = (event: DragEvent) => {
  isDragging.value = false
  
  if (!event.dataTransfer || isUploading.value) return
  
  const files = Array.from(event.dataTransfer.files)
  processFiles(files)
}

const handleFileSelect = (event: Event) => {
  const input = event.target as HTMLInputElement
  
  if (!input.files || input.files.length === 0) {
    return
  }
  
  const files = Array.from(input.files)
  processFiles(files)
  
  // Reset input
  input.value = ''
}

const validateFile = (file: File): string | null => {
  if (!file.type.startsWith('audio/')) {
    return `${file.name}: Type de fichier non supporté`
  }
  
  // Check file size (max 100MB)
  const maxSize = 100 * 1024 * 1024
  if (file.size > maxSize) {
    return `${file.name}: Fichier trop volumineux (max 100MB)`
  }
  
  return null
}

const processFiles = async (files: File[]) => {
  // Validate files
  uploadErrors.value = []
  const validFiles: File[] = []
  
  for (const file of files) {
    const error = validateFile(file)
    if (error) {
      uploadErrors.value.push(error)
    } else {
      validFiles.push(file)
    }
  }
  
  if (validFiles.length === 0) {
    return
  }
  
  // Initialize upload files
  uploadFiles.value = validFiles.map(file => ({
    file,
    progress: 0,
    status: 'pending'
  }))
  
  // Start upload automatically
  await startUpload(validFiles)
}

const startUpload = async (files: File[]) => {
  if (isUploading.value) return
  
  try {
    isUploading.value = true
    overallProgress.value = 0
    
    logger.info(`Starting upload of ${files.length} files to playlist ${props.playlistId}`, {}, 'SimpleUploader')
    
    // Calculate total chunks for all files
    const chunkSize = 1024 * 1024 // 1MB chunks
    const totalChunksAllFiles = files.reduce((total, file) => {
      return total + Math.ceil(file.size / chunkSize)
    }, 0)
    
    let completedChunks = 0
    
    // Upload files sequentially
    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      const uploadFile = uploadFiles.value[i]
      
      try {
        uploadFile.status = 'uploading'
        await uploadSingleFile(file, uploadFile, (completedChunksInFile) => {
          // Update overall progress based on actual chunk completion
          const totalCompletedChunks = completedChunks + completedChunksInFile
          overallProgress.value = Math.round((totalCompletedChunks / totalChunksAllFiles) * 100)
        })
        
        uploadFile.status = 'success'
        uploadFile.progress = 100
        
        // Add completed chunks for this file to the total
        completedChunks += Math.ceil(file.size / chunkSize)
        
        logger.info(`File ${file.name} uploaded successfully`, {}, 'SimpleUploader')
        
      } catch (error) {
        uploadFile.status = 'error'
        const errorMessage = `${file.name}: ${error instanceof Error ? error.message : 'Upload failed'}`
        uploadErrors.value.push(errorMessage)
        logger.error(`File ${file.name} upload failed`, { error }, 'SimpleUploader')
      }
    }
    
    // Ensure progress reaches 100%
    overallProgress.value = 100
    
    // Emit completion
    emit('upload-complete')
    logger.info('All uploads completed', {}, 'SimpleUploader')
    
  } catch (error) {
    logger.error('Upload process failed', { error }, 'SimpleUploader')
    emit('upload-error', error)
  } finally {
    isUploading.value = false
  }
}

const uploadSingleFile = async (
  file: File, 
  uploadFile: { progress: number; status: string }, 
  onProgress?: (completedChunks: number) => void
) => {
  // 1. Initialize upload session
  const initResponse = await apiService.initUpload(props.playlistId, file.name, file.size)
  
  const sessionId = initResponse.session_id
  const chunkSize = 1024 * 1024 // 1MB chunks
  const totalChunks = Math.ceil(file.size / chunkSize)
  
  // Store session ID for Socket.IO progress tracking
  uploadFile.sessionId = sessionId
  
  // 2. Upload chunks
  for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
    const start = chunkIndex * chunkSize
    const end = Math.min(start + chunkSize, file.size)
    const chunk = file.slice(start, end)
    
    // Upload chunk directly (API handles FormData internally)
    await apiService.uploadChunk(props.playlistId, sessionId, chunkIndex, chunk)
    
    // Update file progress
    const fileProgress = Math.round(((chunkIndex + 1) / totalChunks) * 100)
    uploadFile.progress = fileProgress
    
    // Notify overall progress callback if provided
    if (onProgress) {
      onProgress(chunkIndex + 1) // Pass number of completed chunks for this file
    }
  }
  
  // 3. Finalize upload
  logger.info(`Finalizing upload for session ${sessionId}`, {}, 'SimpleUploader')
  
  try {
    const finalizeResult = await apiService.finalizeUpload(props.playlistId, sessionId)
    logger.info(`Upload finalized successfully for session ${sessionId}`, { result: finalizeResult }, 'SimpleUploader')
  } catch (error) {
    logger.error(`Failed to finalize upload for session ${sessionId}`, { error }, 'SimpleUploader')
    throw error // Re-throw to be caught by the outer try-catch
  }
}

const cancelUpload = () => {
  isUploading.value = false
  uploadFiles.value.forEach(file => {
    if (file.status === 'uploading') {
      file.status = 'cancelled'
    }
  })
  logger.info('Upload cancelled by user', {}, 'SimpleUploader')
}

// Socket.IO event handlers for real-time upload progress
    /* eslint-disable @typescript-eslint/no-explicit-any */
const handleUploadProgress = (data: any) => {
  if (data.playlist_id !== props.playlistId) return
  
  // Find the upload file by session ID
  const uploadFile = uploadFiles.value.find(f => f.sessionId === data.session_id)
  if (uploadFile) {
    uploadFile.progress = data.progress
    if (data.complete) {
      uploadFile.status = 'processing'
    } else {
      uploadFile.status = 'uploading'
    }
    
    // Update overall progress
    const totalProgress = uploadFiles.value.reduce((sum, file) => sum + file.progress, 0)
    overallProgress.value = Math.round(totalProgress / uploadFiles.value.length)
    
    logger.debug(`Upload progress: ${data.progress}% for session ${data.session_id}`, {}, 'SimpleUploader')
  }
}

const handleUploadComplete = (data: any) => {
  if (data.playlist_id !== props.playlistId) return
  
  // Find the upload file by session ID
  const uploadFile = uploadFiles.value.find(f => f.sessionId === data.session_id)
  if (uploadFile) {
    uploadFile.status = 'completed'
    uploadFile.progress = 100
    
    logger.info(`Upload completed for file ${data.filename}`, {}, 'SimpleUploader')
    
    // Check if all uploads are complete
    const allComplete = uploadFiles.value.every(f => f.status === 'completed')
    if (allComplete) {
      isUploading.value = false
      emit('upload-complete')
    }
  }
}

const handleUploadError = (data: any) => {
  if (data.playlist_id !== props.playlistId) return
  
    /* eslint-enable @typescript-eslint/no-explicit-any */
  // Find the upload file by session ID
  const uploadFile = uploadFiles.value.find(f => f.sessionId === data.session_id)
  if (uploadFile) {
    uploadFile.status = 'error'
    uploadErrors.value.push(data.error || 'Upload failed')
    
    logger.error(`Upload error for session ${data.session_id}: ${data.error}`, {}, 'SimpleUploader')
    emit('upload-error', data.error)
  }
}

// Setup Socket.IO listeners on mount
onMounted(() => {
  socketService.on('upload:progress', handleUploadProgress)
  socketService.on('upload:complete', handleUploadComplete)
  socketService.on('upload:error', handleUploadError)
})

// Cleanup on unmount
onUnmounted(() => {
  if (isUploading.value) {
    cancelUpload()
  }
  
  // Remove Socket.IO listeners
  socketService.off('upload:progress', handleUploadProgress)
  socketService.off('upload:complete', handleUploadComplete)
  socketService.off('upload:error', handleUploadError)
})
</script>