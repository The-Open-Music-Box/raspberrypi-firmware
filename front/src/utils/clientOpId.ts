/**
 * Client Operation ID Utilities
 * Manages client-side operation tracking for server-authoritative architecture
 */

interface PendingOperation {
  operation: string
  timestamp: number
  resolve: ((value: any) => void) | null
  reject: ((reason?: any) => void) | null
}

export const pendingOperations = new Map<string, PendingOperation>()

export const generateClientOpId = (operation: string): string => {
  return `${operation}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

export const trackPendingOperation = (clientOpId: string, operation: string): void => {
  pendingOperations.set(clientOpId, {
    operation,
    timestamp: Date.now(),
    resolve: null,
    reject: null
  })
}

export const resolvePendingOperation = (clientOpId: string, data: any): void => {
  const pending = pendingOperations.get(clientOpId)
  if (pending && pending.resolve) {
    pending.resolve(data)
    pendingOperations.delete(clientOpId)
  }
}

export const rejectPendingOperation = (clientOpId: string, error: any): void => {
  const pending = pendingOperations.get(clientOpId)
  if (pending && pending.reject) {
    pending.reject(error)
    pendingOperations.delete(clientOpId)
  }
}

export const cleanupExpiredOperations = (maxAge = 30000): void => {
  const now = Date.now()
  const expiredKeys: string[] = []
  
  for (const [key, operation] of pendingOperations) {
    if (now - operation.timestamp > maxAge) {
      expiredKeys.push(key)
    }
  }
  
  expiredKeys.forEach(key => {
    rejectPendingOperation(key, new Error('Operation timeout'))
  })
}

// Cleanup expired operations every 30 seconds using TimerManager to prevent memory leaks
import { timerManager } from './TimerManager'

timerManager.setInterval(() => cleanupExpiredOperations(), 30000, 'Client operation cleanup')