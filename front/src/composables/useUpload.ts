/* eslint-disable @typescript-eslint/no-unused-vars */
/**
 * Simple Upload Composable
 * Minimal implementation for upload store compatibility
 */

import { ref } from 'vue'

export interface UploadFile {
  file: File
  status: 'pending' | 'uploading' | 'success' | 'error' | 'cancelled'
  progress: number
  sessionId?: string
  error?: string
  retryCount: number
  checksum?: string
}

export interface UploadConfig {
  chunkSize: number
  maxRetries: number
  useChunkedUpload: boolean
  validateFiles: boolean
  generateChecksums: boolean
}

export interface UploadStats {
  startTime: number
  bytesUploaded: number
  totalBytes: number
  speed: number
  filesCompleted: number
  filesTotal: number
}

export function useUpload() {
  const uploadFiles = ref<UploadFile[]>([])
  const isUploading = ref(false)
  const isCancelled = ref(false)
  const uploadErrors = ref<string[]>([])
  const overallProgress = ref(0)
  const currentFileProgress = ref(0)
  const currentFileName = ref<string | null>(null)
  const currentChunkIndex = ref(0)
  const totalChunks = ref(0)
  
  const uploadConfig = ref<UploadConfig>({
    chunkSize: 1024 * 1024,
    maxRetries: 3,
    useChunkedUpload: true,
    validateFiles: true,
    generateChecksums: false
  })

  const stats = ref<UploadStats>({
    startTime: 0,
    bytesUploaded: 0,
    totalBytes: 0,
    speed: 0,
    filesCompleted: 0,
    filesTotal: 0
  })

  const hasErrors = ref(false)
  const estimatedTimeRemaining = ref<number | null>(null)
  const uploadSpeedFormatted = ref('0 B/s')
  const completedFiles = ref(0)
  const failedFiles = ref(0)

  const validateFile = (_file: File): string | null => {
    if (!_file.type.startsWith('audio/')) {
      return 'Invalid file type'
    }
    return null
  }

  const generateChecksum = async (_file: File): Promise<string> => {
    return 'mock-checksum'
  }

  const initializeFiles = (files: File[]) => {
    uploadFiles.value = files.map(file => ({
      file,
      status: 'pending' as const,
      progress: 0,
      retryCount: 0
    }))
  }

  const startUpload = async (_playlistId: string): Promise<void> => {
    isUploading.value = true
    // Minimal implementation - actual upload handled by SimpleUploader
  }

  const cancelUpload = () => {
    isCancelled.value = true
    isUploading.value = false
  }

  const resetUpload = () => {
    uploadFiles.value = []
    isUploading.value = false
    isCancelled.value = false
    overallProgress.value = 0
  }

  return {
    uploadFiles,
    isUploading,
    isCancelled,
    uploadErrors,
    hasErrors,
    overallProgress,
    currentFileProgress,
    currentFileName,
    currentChunkIndex,
    totalChunks,
    stats,
    estimatedTimeRemaining,
    uploadSpeedFormatted,
    completedFiles,
    failedFiles,
    uploadConfig,
    validateFile,
    generateChecksum,
    initializeFiles,
    startUpload,
    cancelUpload,
    resetUpload
  }
}