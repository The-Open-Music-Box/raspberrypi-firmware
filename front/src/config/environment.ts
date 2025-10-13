/**
 * Environment Configuration
 * Provides dynamic configuration based on environment and deployment context
 */

interface ApiConfig {
  baseUrl: string
  timeout: number
  withCredentials: boolean
}

interface AppConfig {
  api: ApiConfig
  socket: {
    url: string
    options: {
      autoConnect: boolean
      transports: string[]
      path?: string
    }
  }
  features: {
    uploadChunkSize: number
    maxFileSize: number
    supportedFormats: string[]
  }
  ui: {
    defaultPageSize: number
    maxRetryAttempts: number
  }
}

const getApiConfig = (): ApiConfig => {
  const isDevelopment = process.env.NODE_ENV === 'development'
  
  if (isDevelopment) {
    // Try multiple common development URLs
    const devUrls = [
      process.env.VUE_APP_API_URL,
      'http://localhost:5004',
      'http://theopenmusicbox.local:5004',
      `http://${window.location.hostname}:5004`
    ].filter(Boolean) as string[]
    
    return {
      baseUrl: devUrls[0],
      timeout: 60000,
      withCredentials: false
    }
  }
  
  return {
    baseUrl: window.location.origin,
    timeout: 30000,
    withCredentials: true
  }
}

/**
 * Detects if the target is an ESP32 device based on URL patterns.
 * ESP32 typically uses port 80 or direct IP addresses like 10.0.0.x
 * RPI Backend uses port 5004 or standard web ports (3000, 8080, etc.)
 */
const isESP32Target = (baseUrl: string): boolean => {
  // Check for explicit ESP32 indicator via environment variable
  if (process.env.VUE_APP_TARGET === 'esp32') {
    return true
  }
  if (process.env.VUE_APP_TARGET === 'rpi') {
    return false
  }

  // Auto-detect based on URL patterns
  const url = baseUrl.toLowerCase()

  // ESP32 indicators:
  // - Port 80 (default ESP32 web server port)
  // - Direct IP addresses in 10.0.0.x range (common local network)
  // - Direct IP addresses in 192.168.x.x range
  const isPort80 = url.includes(':80/') || url.endsWith(':80')
  const isLocalIP = /https?:\/\/(10\.0\.0\.|192\.168\.)/.test(url)

  // RPI Backend indicators:
  // - Port 5004 (RPI Backend default)
  // - localhost or theopenmusicbox.local hostname
  const isRPIPort = url.includes(':5004') || url.includes(':3000') || url.includes(':8080')
  const isRPIHostname = url.includes('localhost') || url.includes('theopenmusicbox.local')

  // If explicitly RPI indicators, return false
  if (isRPIPort || isRPIHostname) {
    return false
  }

  // If ESP32 indicators, return true
  if (isPort80 || isLocalIP) {
    return true
  }

  // Default: assume RPI Backend (safer default for backward compatibility)
  return false
}

const createAppConfig = (): AppConfig => {
  const apiConfig = getApiConfig()
  const targetIsESP32 = isESP32Target(apiConfig.baseUrl)

  // Log detected target for debugging
  console.log(`[Config] Detected target: ${targetIsESP32 ? 'ESP32' : 'RPI Backend'}`, {
    baseUrl: apiConfig.baseUrl,
    socketPath: targetIsESP32 ? '/ws' : '/socket.io/ (default)'
  })

  return {
    api: apiConfig,
    socket: {
      url: apiConfig.baseUrl,
      options: {
        autoConnect: true,
        transports: ['websocket', 'polling'],
        // Only add custom path for ESP32 (RPI uses default /socket.io/)
        ...(targetIsESP32 ? { path: '/ws' } : {})
      }
    },
    features: {
      uploadChunkSize: 1024 * 1024, // 1MB chunks
      maxFileSize: 100 * 1024 * 1024, // 100MB max file size
      supportedFormats: ['.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg']
    },
    ui: {
      defaultPageSize: 50,
      maxRetryAttempts: 3
    }
  }
}

export const appConfig = createAppConfig()

// Backwards compatibility exports
export const apiConfig = appConfig.api
export const socketConfig = appConfig.socket