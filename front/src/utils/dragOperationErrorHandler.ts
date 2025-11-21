/* eslint-disable @typescript-eslint/no-unused-vars */
/**
 * Centralized error handling for drag & drop operations
 */

import { logger } from '@/utils/logger'

export interface DragContext {
  operation: 'reorder' | 'move' | 'delete' | 'add'
  playlistId: string
  sourcePlaylistId?: string
  trackNumber?: number
  trackNumbers?: number[]
  component: string
}

export interface DragErrorOptions {
  showUserFeedback?: boolean
  logLevel?: 'debug' | 'info' | 'warn' | 'error'
  retryable?: boolean
}

export class DragOperationError extends Error {
  constructor(
    message: string,
    public context: DragContext,
    public originalError?: Error
  ) {
    super(message)
    this.name = 'DragOperationError'
  }
}

/**
 * Unified error handler for drag operations
 */
export function handleDragError(
  error: Error | DragOperationError,
  context: DragContext,
  options: DragErrorOptions = {}
): DragOperationError {
  const {
    logLevel = 'error',
    retryable = false
  } = options

  let dragError: DragOperationError
  
  if (error instanceof DragOperationError) {
    dragError = error
  } else {
    dragError = new DragOperationError(
      `Failed to ${context.operation} tracks`,
      context,
      error
    )
  }

  // Log with appropriate level
  const logData = {
    operation: context.operation,
    playlistId: context.playlistId,
    sourcePlaylistId: context.sourcePlaylistId,
    trackNumber: context.trackNumber,
    trackNumbers: context.trackNumbers,
    retryable,
    originalError: dragError.originalError?.message,
    stack: dragError.stack
  }

  switch (logLevel) {
    case 'debug':
      logger.debug('Drag operation error', logData, context.component)
      break
    case 'info':
      logger.info('Drag operation error', logData, context.component)
      break
    case 'warn':
      logger.warn('Drag operation error', logData, context.component)
      break
    case 'error':
    default:
      logger.error('Drag operation error', logData, context.component)
      break
  }

  return dragError
}

/**
 * Get user-friendly error message for drag operations
 */
export function getDragErrorMessage(operation: DragContext['operation'], _error?: Error): string {
  const messages = {
    reorder: 'Failed to reorder tracks. Please try again.',
    move: 'Failed to move track between playlists. Please try again.',
    delete: 'Failed to delete track. Please try again.',
    add: 'Failed to add track. Please try again.'
  }
  
  return messages[operation] || 'An error occurred during the operation. Please try again.'
}

/**
 * Validate drag operation context
 */
export function validateDragContext(context: Partial<DragContext>): DragContext | null {
  if (!context.operation) {
    logger.warn('Missing operation in drag context', context)
    return null
  }
  
  if (!context.playlistId) {
    logger.warn('Missing playlistId in drag context', context)
    return null
  }
  
  if (!context.component) {
    logger.warn('Missing component in drag context', context)
    return null
  }

  // Validate operation-specific requirements
  switch (context.operation) {
    case 'move':
      if (!context.sourcePlaylistId) {
        logger.warn('Missing sourcePlaylistId for move operation', context)
        return null
      }
      if (!context.trackNumber) {
        logger.warn('Missing trackNumber for move operation', context)
        return null
      }
      break
    case 'reorder':
      if (!context.trackNumbers || context.trackNumbers.length === 0) {
        logger.warn('Missing trackNumbers for reorder operation', context)
        return null
      }
      break
  }

  return context as DragContext
}