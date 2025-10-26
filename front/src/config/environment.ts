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

const createAppConfig = (): AppConfig => {
  const apiConfig = getApiConfig()
  
  return {
    api: apiConfig,
    socket: {
      url: apiConfig.baseUrl,
      options: {
        autoConnect: true,
        transports: ['websocket', 'polling']
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