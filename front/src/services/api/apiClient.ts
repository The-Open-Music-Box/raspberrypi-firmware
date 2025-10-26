/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-non-null-assertion */
/**
 * Base API Client and Response Handlers
 * Shared utilities for all API modules
 */

import axios, { AxiosError, InternalAxiosRequestConfig, AxiosResponse } from 'axios'
import { logger } from '../../utils/logger'
import { apiConfig } from '../../config/environment'
import { ApiResponse, ApiError } from '../../types/contracts'

// Extend axios types to include metadata
declare module 'axios' {
  export interface InternalAxiosRequestConfig {
    metadata?: {
      start: number
    }
  }
}

/**
 * Custom error class for standardized API errors
 */
export class StandardApiError extends Error {
  constructor(
    public readonly message: string,
    public readonly errorType: string,
    public readonly statusCode: number,
    public readonly details?: Record<string, any>,
    public readonly requestId?: string
  ) {
    super(message)
    this.name = 'StandardApiError'
  }
  
  /**
   * Check if error is a specific type
   */
  isType(type: string): boolean {
    return this.errorType === type
  }
  
  /**
   * Check if error is retryable
   */
  isRetryable(): boolean {
    return this.statusCode >= 500 || this.errorType === 'rate_limit_exceeded'
  }
}

/**
 * Centralized API response handler with enhanced error handling
 */
export class ApiResponseHandler {
  /**
   * Extract data from standardized API response
   */
  static extractData<T>(response: AxiosResponse<ApiResponse<T>>): T {
    const { data: apiResponse } = response

    // Debug: Log the raw response structure
    logger.debug('extractData called', {
      url: response.config?.url || 'unknown',
      status: response.status,
      hasApiResponse: !!apiResponse,
      apiResponseType: typeof apiResponse,
      apiResponseStatus: apiResponse?.status,
      hasDataField: apiResponse ? 'data' in apiResponse : false,
      dataType: apiResponse && 'data' in apiResponse ? typeof (apiResponse as any).data : 'N/A'
    }, 'ApiResponseHandler')

    // Handle 204 No Content responses (no body)
    if (response.status === 204) {
      return undefined as T
    }

    // Handle empty/null response data (might happen with 204 or network issues)
    if (!apiResponse) {
      if (response.status >= 200 && response.status < 300) {
        return undefined as T
      }
      throw new StandardApiError(
        'Empty response from server',
        'internal_error',
        response.status
      )
    }

    // Handle standardized success response
    if (apiResponse.status === 'success') {
      if ('data' in apiResponse && apiResponse.data !== undefined) {
        logger.debug('Returning data from success response', {
          url: response.config?.url || 'unknown',
          dataType: typeof apiResponse.data
        }, 'ApiResponseHandler')
        return apiResponse.data!
      }
      // For operations like DELETE that don't return data, return undefined
      // This is normal for 200 OK responses without data payload
      logger.warn('Success response without data field', {
        url: response.config?.url || 'unknown',
        status: response.status,
        hasDataField: 'data' in apiResponse,
        dataValue: (apiResponse as any).data,
        fullResponse: apiResponse
      }, 'ApiResponseHandler')
      return undefined as T
    }

    // Handle standardized error response
    if (apiResponse.status === 'error') {
      const errorData = apiResponse as ApiError
      throw new StandardApiError(
        errorData.message || 'API Error',
        errorData.error_type || 'api_error',
        response.status,
        errorData.details,
        errorData.request_id
      )
    }

    // Handle direct data responses (legacy support)
    if (typeof apiResponse === 'object' && !('status' in apiResponse)) {
      return apiResponse as T
    }

    // Fallback for unexpected response format
    logger.warn('Unexpected API response format', { 
      status: response.status, 
      data: apiResponse 
    }, 'ApiResponseHandler')
    
    return apiResponse as T
  }

  /**
   * Handle API errors with detailed logging
   */
  static handleError(error: AxiosError): never {
    const requestInfo = {
      method: error.config?.method?.toUpperCase(),
      url: error.config?.url,
      duration: error.config?.metadata ? Date.now() - error.config.metadata.start : undefined
    }

    if (error.response) {
      // Server responded with error status
      const status = error.response.status
      const responseData = error.response.data as any

      logger.error('API Request failed with server error', {
        ...requestInfo,
        status,
        statusText: error.response.statusText,
        responseData
      }, 'ApiClient')

      // Extract standardized error message
      let message = `HTTP ${status}: ${error.response.statusText}`
      let errorType = 'api_error'
      let details = undefined
      let requestId = undefined

      if (responseData && typeof responseData === 'object') {
        if (responseData.message) {
          message = responseData.message
        }
        if (responseData.error_type) {
          errorType = responseData.error_type
        }
        if (responseData.details) {
          details = responseData.details
        }
        if (responseData.request_id) {
          requestId = responseData.request_id
        }
      }

      throw new StandardApiError(message, errorType, status, details, requestId)
    } else if (error.request) {
      // Request made but no response received
      logger.error('API Request failed - no response received', {
        ...requestInfo,
        error: error.message
      }, 'ApiClient')

      throw new StandardApiError(
        'Network error - unable to reach server',
        'network_error',
        0,
        { originalError: error.message }
      )
    } else {
      // Error in setting up the request
      logger.error('API Request setup failed', {
        ...requestInfo,
        error: error.message
      }, 'ApiClient')

      throw new StandardApiError(
        'Request configuration error',
        'config_error',
        0,
        { originalError: error.message }
      )
    }
  }
}

/**
 * Enhanced API client with standardized response handling
 */
export const apiClient = axios.create({
  baseURL: apiConfig.baseUrl,
  timeout: apiConfig.timeout,
  withCredentials: apiConfig.withCredentials,
  headers: {
    Accept: 'application/json',
    'Content-Type': 'application/json'
  }
})

// Request interceptor to add metadata and handle FormData
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  config.metadata = { start: Date.now() }

  // Handle FormData uploads - remove Content-Type to let axios set it with boundary
  if (config.data instanceof FormData) {
    delete config.headers['Content-Type']
  }

  logger.debug('API Request started', {
    method: config.method?.toUpperCase(),
    url: config.url,
    headers: config.headers,
    isFormData: config.data instanceof FormData
  }, 'ApiClient')

  return config
}, (error) => {
  logger.error('API Request interceptor error', { error: error.message }, 'ApiClient')
  return Promise.reject(error)
})

// Response interceptor for standardized error handling
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    const duration = response.config.metadata ? Date.now() - response.config.metadata.start : undefined
    
    logger.debug('API Request completed successfully', {
      method: response.config.method?.toUpperCase(),
      url: response.config.url,
      status: response.status,
      duration: duration ? `${duration}ms` : 'unknown'
    }, 'ApiClient')
    
    return response
  },
  (error: AxiosError) => {
    return Promise.reject(ApiResponseHandler.handleError(error))
  }
)