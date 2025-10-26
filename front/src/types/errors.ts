/**
 * Standardized Error Handling Types
 * Provides consistent error interfaces across the application
 */

export interface AppError {
  message: string;
  code?: string;
  context?: string;
  originalError?: unknown;
  timestamp?: Date;
}

export interface UploadError extends AppError {
  sessionId?: string;
  fileName?: string;
  chunkIndex?: number;
  retryCount?: number;
}

export interface ApiError extends AppError {
  status?: number;
  endpoint?: string;
  method?: string;
  responseData?: unknown;
}

export interface SocketError extends AppError {
  event?: string;
  connectionState?: 'connected' | 'disconnected' | 'reconnecting';
}

/**
 * Error normalization utility
 */
export function normalizeError(error: unknown, context: string): AppError {
  if (error instanceof Error) {
    return {
      message: error.message,
      context,
      originalError: error,
      timestamp: new Date()
    };
  }
  
  if (typeof error === 'string') {
    return {
      message: error,
      context,
      timestamp: new Date()
    };
  }
  
  if (error && typeof error === 'object' && 'message' in error) {
    return {
      message: String((error as { message: unknown }).message),
      context,
      originalError: error,
      timestamp: new Date()
    };
  }
  
  return {
    message: 'Unknown error occurred',
    context,
    originalError: error,
    timestamp: new Date()
  };
}

/**
 * API Error normalization utility
 */
export function normalizeApiError(error: unknown, endpoint: string, method: string): ApiError {
  const baseError = normalizeError(error, 'ApiService');
  
  if (error && typeof error === 'object' && 'response' in error) {
    const axiosError = error as {
      response?: {
        status?: number;
        data?: unknown;
      };
    };
    
    return {
      ...baseError,
      status: axiosError.response?.status,
      endpoint,
      method,
      responseData: axiosError.response?.data
    };
  }
  
  return {
    ...baseError,
    endpoint,
    method
  };
}
