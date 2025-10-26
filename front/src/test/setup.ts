/**
 * Vitest global setup for frontend tests
 */

import { vi } from 'vitest'
import { config } from '@vue/test-utils'

// Mock socketService to prevent WebSocket connection attempts during tests
vi.mock('@/services/socketService', () => ({
  socketService: {
    on: vi.fn(),
    off: vi.fn(),
    once: vi.fn(),
    emit: vi.fn(),
    joinRoom: vi.fn().mockResolvedValue(undefined),
    leaveRoom: vi.fn().mockResolvedValue(undefined),
    sendOperation: vi.fn().mockResolvedValue({ success: true }),
    requestSync: vi.fn(),
    isConnected: vi.fn().mockReturnValue(false),
    isReady: vi.fn().mockReturnValue(false),
    getLastServerSeq: vi.fn().mockReturnValue(0),
    getSubscribedRooms: vi.fn().mockReturnValue([]),
    destroy: vi.fn()
  },
  default: {
    on: vi.fn(),
    off: vi.fn(),
    once: vi.fn(),
    emit: vi.fn(),
    joinRoom: vi.fn().mockResolvedValue(undefined),
    leaveRoom: vi.fn().mockResolvedValue(undefined),
    sendOperation: vi.fn().mockResolvedValue({ success: true }),
    requestSync: vi.fn(),
    isConnected: vi.fn().mockReturnValue(false),
    isReady: vi.fn().mockReturnValue(false),
    getLastServerSeq: vi.fn().mockReturnValue(0),
    getSubscribedRooms: vi.fn().mockReturnValue([]),
    destroy: vi.fn()
  }
}))

// Mock Socket.IO client to prevent actual connection attempts
vi.mock('socket.io-client', () => ({
  io: vi.fn(() => ({
    on: vi.fn(),
    off: vi.fn(),
    emit: vi.fn(),
    connect: vi.fn(),
    disconnect: vi.fn(),
    connected: false,
    id: 'mock-socket-id'
  }))
}))

// Mock console methods to reduce test noise
global.console = {
  ...console,
  // Uncomment to silence logs during tests
  // log: vi.fn(),
  // debug: vi.fn(),
  // info: vi.fn(),
  // warn: vi.fn(),
  error: console.error // Keep errors visible
}

// Mock localStorage
Object.defineProperty(window, 'localStorage', {
  value: {
    getItem: vi.fn(),
    setItem: vi.fn(),
    removeItem: vi.fn(),
    clear: vi.fn(),
    length: 0,
    key: vi.fn()
  },
  writable: true
})

// Mock sessionStorage
Object.defineProperty(window, 'sessionStorage', {
  value: {
    getItem: vi.fn(),
    setItem: vi.fn(),
    removeItem: vi.fn(),
    clear: vi.fn(),
    length: 0,
    key: vi.fn()
  },
  writable: true
})

// Setup jsdom environment
Object.defineProperty(window, 'location', {
  value: {
    href: 'http://localhost:3000',
    origin: 'http://localhost:3000',
    protocol: 'http:',
    host: 'localhost:3000',
    hostname: 'localhost',
    port: '3000',
    pathname: '/',
    search: '',
    hash: ''
  },
  writable: true
})

// Mock window.matchMedia for responsive components
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock IntersectionObserver for components using it
global.IntersectionObserver = vi.fn(() => ({
  disconnect: vi.fn(),
  observe: vi.fn(),
  unobserve: vi.fn(),
}))

// Mock ResizeObserver
global.ResizeObserver = vi.fn(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Global Vue Test Utils configuration
config.global.mocks = {
  $t: (key: string, params?: any) => {
    if (params) {
      return `${key} ${JSON.stringify(params)}`
    }
    return key
  },
  $route: {
    path: '/',
    params: {},
    query: {},
    name: 'home'
  },
  $router: {
    push: vi.fn(),
    replace: vi.fn(),
    go: vi.fn(),
    back: vi.fn(),
    forward: vi.fn()
  }
}

// Mock file APIs for upload tests
global.File = class MockFile {
  constructor(
    public bits: BlobPart[],
    public name: string,
    public options: FilePropertyBag = {}
  ) {}

  get type() { return this.options.type || '' }
  get size() { return this.bits.reduce((size, bit) => size + (typeof bit === 'string' ? bit.length : bit.byteLength || 0), 0) }
  get lastModified() { return this.options.lastModified || Date.now() }
}

global.FileList = class MockFileList extends Array {
  item(index: number) { return this[index] || null }
}

// Mock drag and drop APIs
Object.defineProperty(window, 'DataTransfer', {
  value: class MockDataTransfer {
    constructor() {
      this.items = []
      this.files = []
      this.types = []
    }
    items: any[]
    files: File[]
    types: string[]
    effectAllowed = 'all'
    dropEffect = 'none'

    setData(type: string, data: string) {
      this.types.push(type)
    }

    getData(type: string) {
      return ''
    }
  }
})

// Mock URL.createObjectURL for file handling
global.URL.createObjectURL = vi.fn(() => 'mock-object-url')
global.URL.revokeObjectURL = vi.fn()