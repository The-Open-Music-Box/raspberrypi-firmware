/**
 * SocketService - Backward compatibility export
 *
 * This file maintains backward compatibility for existing imports.
 * All functionality has been refactored into SocketService.class.ts
 * with dependency injection for better testability.
 *
 * For new code, consider using SocketServiceFactory.create() or
 * dependency injection patterns instead of the singleton.
 */

export { socketService, SocketService, SocketServiceFactory } from './SocketServiceFactory'
export type {
  SocketEventType,
  EventHandlers,
  SocketServiceDependencies,
  ISocketFactory,
  ILogger,
  ISocketConfig
} from './SocketService.class'

// Default export for backward compatibility
export { socketService as default } from './SocketServiceFactory'
