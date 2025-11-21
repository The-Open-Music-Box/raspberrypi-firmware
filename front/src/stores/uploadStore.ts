/**
 * Unified Upload Store (Pinia)
 * 
 * Centralized state management for all upload-related functionality.
 * Replaces multiple upload stores with a single, comprehensive solution.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useUpload, type UploadFile, type UploadConfig } from '@/composables/useUpload'

export const useUploadStore = defineStore('upload', () => {
  // Upload composable instance
  const uploadComposable = useUpload()

  // Modal state
  const isModalOpen = ref(false)
  const modalPlaylistId = ref<string | null>(null)

  // Global upload queue (for multiple playlists)
  const globalUploadQueue = ref<Map<string, UploadFile[]>>(new Map())

  // Upload history
  const uploadHistory = ref<{
    timestamp: number
    playlistId: string
    files: UploadFile[]
    success: boolean
  }[]>([])

  // Computed properties
  const hasActiveUploads = computed(() => uploadComposable.isUploading.value)
  
  const totalPendingFiles = computed(() => {
    let total = 0
    globalUploadQueue.value.forEach(files => {
      total += files.filter(f => f.status === 'pending').length
    })
    return total
  })

  const globalUploadProgress = computed(() => {
    if (globalUploadQueue.value.size === 0) return 0
    
    let totalFiles = 0
    let completedFiles = 0
    
    globalUploadQueue.value.forEach(files => {
      totalFiles += files.length
      completedFiles += files.filter(f => f.status === 'success').length
    })
    
    return totalFiles > 0 ? Math.round((completedFiles / totalFiles) * 100) : 0
  })

  // Modal management
  const openUploadModal = (playlistId: string) => {
    modalPlaylistId.value = playlistId
    isModalOpen.value = true
  }

  const closeUploadModal = () => {
    isModalOpen.value = false
    modalPlaylistId.value = null
  }

  // File management
  const addFilesToQueue = (playlistId: string, files: File[]) => {
    uploadComposable.initializeFiles(files)
    
    // Add to global queue
    const existingFiles = globalUploadQueue.value.get(playlistId) || []
    const newUploadFiles = uploadComposable.uploadFiles.value
    globalUploadQueue.value.set(playlistId, [...existingFiles, ...newUploadFiles])
  }

  const removeFileFromQueue = (playlistId: string, fileIndex: number) => {
    const files = globalUploadQueue.value.get(playlistId)
    if (files && files[fileIndex]) {
      files.splice(fileIndex, 1)
      if (files.length === 0) {
        globalUploadQueue.value.delete(playlistId)
      }
    }
  }

  const clearQueue = (playlistId?: string) => {
    if (playlistId) {
      globalUploadQueue.value.delete(playlistId)
    } else {
      globalUploadQueue.value.clear()
    }
  }

  // Upload operations
  const startUpload = async (playlistId: string) => {
    const files = globalUploadQueue.value.get(playlistId)
    if (!files || files.length === 0) return

    try {
      // Initialize composable with queued files
      uploadComposable.initializeFiles(files.map(f => f.file))
      
      // Start upload
      await uploadComposable.startUpload(playlistId)
      
      // Add to history
      uploadHistory.value.unshift({
        timestamp: Date.now(),
        playlistId,
        files: [...uploadComposable.uploadFiles.value],
        success: uploadComposable.completedFiles.value === files.length
      })
      
      // Clear queue for this playlist
      globalUploadQueue.value.delete(playlistId)
      
    } catch (error) {
      // Add to history with error state
      uploadHistory.value.unshift({
        timestamp: Date.now(),
        playlistId,
        files: [...uploadComposable.uploadFiles.value],
        success: false
      })
      throw error
    }
  }

  const cancelUpload = () => {
    uploadComposable.cancelUpload()
  }

  const resetUpload = () => {
    uploadComposable.resetUpload()
    globalUploadQueue.value.clear()
  }

  // Configuration management
  const updateConfig = (newConfig: Partial<UploadConfig>) => {
    Object.assign(uploadComposable.uploadConfig.value, newConfig)
  }

  // History management
  const clearHistory = () => {
    uploadHistory.value = []
  }

  const getHistoryForPlaylist = (playlistId: string) => {
    return uploadHistory.value.filter(entry => entry.playlistId === playlistId)
  }

  // Expose composable properties and methods
  return {
    // Modal state
    isModalOpen,
    modalPlaylistId,
    openUploadModal,
    closeUploadModal,

    // Upload state (from composable)
    uploadFiles: uploadComposable.uploadFiles,
    isUploading: uploadComposable.isUploading,
    isCancelled: uploadComposable.isCancelled,
    uploadErrors: uploadComposable.uploadErrors,
    hasErrors: uploadComposable.hasErrors,

    // Progress (from composable)
    overallProgress: uploadComposable.overallProgress,
    currentFileProgress: uploadComposable.currentFileProgress,
    currentFileName: uploadComposable.currentFileName,
    currentChunkIndex: uploadComposable.currentChunkIndex,
    totalChunks: uploadComposable.totalChunks,

    // Statistics (from composable)
    stats: uploadComposable.stats,
    estimatedTimeRemaining: uploadComposable.estimatedTimeRemaining,
    uploadSpeedFormatted: uploadComposable.uploadSpeedFormatted,
    completedFiles: uploadComposable.completedFiles,
    failedFiles: uploadComposable.failedFiles,

    // Configuration
    uploadConfig: uploadComposable.uploadConfig,
    updateConfig,

    // Global state
    globalUploadQueue,
    uploadHistory,
    hasActiveUploads,
    totalPendingFiles,
    globalUploadProgress,

    // Queue management
    addFilesToQueue,
    removeFileFromQueue,
    clearQueue,

    // Upload operations
    startUpload,
    cancelUpload,
    resetUpload,

    // History
    clearHistory,
    getHistoryForPlaylist,

    // Utility methods (from composable)
    validateFile: uploadComposable.validateFile,
    generateChecksum: uploadComposable.generateChecksum
  }
})
