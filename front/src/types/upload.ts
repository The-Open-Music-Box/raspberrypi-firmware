/**
 * Upload Types and Interfaces
 * 
 * Standardized TypeScript interfaces for all upload-related functionality.
 * These interfaces ensure consistency across all upload components and composables.
 */

// Core upload file interface
export interface UploadFile {
  file: File
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'error'
  progress: number
  sessionId?: string
  error?: string
  retryCount: number
  checksum?: string
  uploadedAt?: Date
  metadata?: UploadFileMetadata
}

// File metadata interface
export interface UploadFileMetadata {
  title?: string
  artist?: string
  album?: string
  duration?: number
  bitrate?: number
  format?: string
  size: number
  lastModified: number
}

// Upload session interface
export interface UploadSession {
  sessionId: string
  playlistId: string
  filename: string
  fileSize: number
  chunkSize: number
  totalChunks: number
  uploadedChunks: number[]
  missingChunks: number[]
  status: 'initialized' | 'in_progress' | 'completed' | 'failed' | 'expired'
  createdAt: Date
  expiresAt: Date
  lastActivity: Date
  canResume: boolean
  progress: number
}

// Upload statistics interface
export interface UploadStats {
  startTime: number
  bytesUploaded: number
  totalBytes: number
  speed: number // bytes per second
  filesCompleted: number
  filesTotal: number
  averageFileSize: number
  estimatedTimeRemaining?: number
}

// Upload configuration interface
export interface UploadConfig {
  chunkSize: number
  maxRetries: number
  useChunkedUpload: boolean
  validateFiles: boolean
  generateChecksums: boolean
  maxFileSize: number
  allowedFileTypes: string[]
  concurrentUploads: number
}

// Enhanced configuration for robust uploads
export interface RobustUploadConfig extends UploadConfig {
  persistProgress: boolean
  autoRetryOnNetworkError: boolean
  maxNetworkRetries: number
  networkRetryDelay: number
  enableSessionRecovery: boolean
  exponentialBackoff: boolean
  maxBackoffDelay: number
}

// Modal-specific configuration
export interface ModalUploadConfig extends UploadConfig {
  autoCloseOnSuccess: boolean
  autoCloseDelay: number
  showProgressInTitle: boolean
  persistModalState: boolean
  allowMultipleFiles: boolean
  dragAndDropEnabled: boolean
}

// Upload error interface
export interface UploadError {
  code?: string
  message: string
  context?: string
  fileName?: string
  sessionId?: string
  chunkIndex?: number
  retryable: boolean
  timestamp: Date
}

// Upload progress event interface
export interface UploadProgressEvent {
  sessionId: string
  playlistId: string
  filename: string
  chunkIndex?: number
  progress: number
  uploadedBytes: number
  totalBytes: number
  speed: number
  estimatedTimeRemaining?: number
  complete: boolean
}

// Upload complete event interface
export interface UploadCompleteEvent {
  sessionId: string
  playlistId: string
  filename: string
  trackId: string
  fileSize: number
  processingTime: number
  metadata: UploadFileMetadata
}

// Upload validation result interface
export interface UploadValidationResult {
  isValid: boolean
  errors: string[]
  warnings: string[]
  file: File
}

// Batch upload interface
export interface BatchUpload {
  id: string
  playlistId: string
  files: UploadFile[]
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'error'
  progress: number
  startedAt?: Date
  completedAt?: Date
  stats: UploadStats
}

// Upload queue item interface
export interface UploadQueueItem {
  id: string
  playlistId: string
  files: File[]
  priority: 'low' | 'normal' | 'high'
  addedAt: Date
  config?: Partial<UploadConfig>
}

// Upload modal action interface
export interface UploadModalAction {
  label: string
  action: 'upload' | 'cancel' | 'close' | 'retry' | 'pause' | 'resume'
  variant: 'primary' | 'secondary' | 'danger'
  disabled: boolean
  loading?: boolean
}

// Upload composable return type interface
export interface UploadComposableReturn {
  // State
  uploadFiles: Ref<UploadFile[]>
  isUploading: Ref<boolean>
  isCancelled: Ref<boolean>
  uploadErrors: Ref<string[]>
  hasErrors: ComputedRef<boolean>
  
  // Progress
  overallProgress: Ref<number>
  currentFileProgress: Ref<number>
  currentFileName: Ref<string | null>
  
  // Statistics
  stats: Ref<UploadStats>
  estimatedTimeRemaining: ComputedRef<number | null>
  uploadSpeedFormatted: ComputedRef<string>
  completedFiles: ComputedRef<number>
  failedFiles: ComputedRef<number>
  
  // Methods
  initializeFiles: (files: File[]) => void
  startUpload: (playlistId: string) => Promise<void>
  cancelUpload: () => void
  resetUpload: () => void
  validateFile: (file: File) => string | null
  generateChecksum: (file: File | Blob) => Promise<string>
}

// Type guards
export function isUploadFile(obj: any): obj is UploadFile {
  return obj && 
    typeof obj === 'object' &&
    obj.file instanceof File &&
    typeof obj.status === 'string' &&
    typeof obj.progress === 'number'
}

export function isUploadError(obj: any): obj is UploadError {
  return obj &&
    typeof obj === 'object' &&
    typeof obj.message === 'string' &&
    typeof obj.retryable === 'boolean'
}

export function isUploadSession(obj: any): obj is UploadSession {
  return obj &&
    typeof obj === 'object' &&
    typeof obj.sessionId === 'string' &&
    typeof obj.playlistId === 'string' &&
    typeof obj.status === 'string'
}

// Utility types
export type UploadStatus = UploadFile['status']
export type SessionStatus = UploadSession['status']
export type UploadActionType = UploadModalAction['action']
export type UploadPriority = UploadQueueItem['priority']

// Import necessary Vue types
import type { Ref, ComputedRef } from 'vue'
