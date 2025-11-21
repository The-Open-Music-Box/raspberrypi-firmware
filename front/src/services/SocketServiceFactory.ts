/**
 * SocketServiceFactory - Creates SocketService instances with real dependencies
 *
 * This factory encapsulates the creation of SocketService instances,
 * injecting real production dependencies (io, logger, config, etc.)
 *
 * Benefits:
 * - Single place to configure dependencies
 * - Easy to create instances for testing with mock dependencies
 * - Clean separation between service logic and dependency wiring
 */

import { io } from 'socket.io-client'
import { logger } from '../utils/logger'
import { socketConfig } from '../config/environment'
import { NativeWebSocketClient } from './nativeWebSocket'
import {
  SocketService,
  type ISocketFactory,
  type ILogger,
  type ISocketConfig,
  type SocketServiceDependencies
} from './SocketService.class'

/**
 * Production socket factory that creates real Socket.IO and Native WebSocket connections
 */
class ProductionSocketFactory implements ISocketFactory {
  createSocketIO(url: string, options: any) {
    return io(url, options)
  }

  createNativeWebSocket(config: any) {
    return new NativeWebSocketClient(config)
  }
}

/**
 * SocketServiceFactory - Factory for creating SocketService instances
 */
export class SocketServiceFactory {
  /**
   * Create a new SocketService instance with production dependencies
   *
   * @returns SocketService instance configured with real dependencies
   */
  static create(): SocketService {
    const deps: SocketServiceDependencies = {
      socketFactory: new ProductionSocketFactory(),
      logger: logger as ILogger,
      config: socketConfig as ISocketConfig
    }

    return new SocketService(deps)
  }

  /**
   * Create a SocketService instance with custom dependencies (for testing)
   *
   * @param deps - Custom dependencies
   * @returns SocketService instance with custom dependencies
   *
   * @example
   * ```ts
   * const mockLogger = { info: vi.fn(), debug: vi.fn(), warn: vi.fn(), error: vi.fn() }
   * const mockSocketFactory = { createSocketIO: vi.fn(), createNativeWebSocket: vi.fn() }
   * const mockConfig = { url: 'http://test', options: { path: '/socket.io' } }
   *
   * const testService = SocketServiceFactory.createWithDeps({
   *   socketFactory: mockSocketFactory,
   *   logger: mockLogger,
   *   config: mockConfig
   * })
   * ```
   */
  static createWithDeps(deps: SocketServiceDependencies): SocketService {
    return new SocketService(deps)
  }
}

/**
 * Default singleton instance for backward compatibility
 *
 * This provides a global instance that can be imported and used
 * throughout the application without creating multiple instances.
 *
 * @deprecated Consider using dependency injection instead
 */
export const socketService = SocketServiceFactory.create()

/**
 * Re-export the SocketService class for type imports
 */
export { SocketService } from './SocketService.class'
export type { SocketServiceDependencies, ISocketFactory, ILogger, ISocketConfig } from './SocketService.class'
