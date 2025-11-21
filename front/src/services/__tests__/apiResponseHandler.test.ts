/**
 * Unit tests for ApiResponseHandler to prevent 204 No Content parsing errors
 * This test suite specifically addresses the bug where deletePlaylist() failed
 * because ApiResponseHandler.extractData() couldn't parse empty 204 responses.
 */

import { describe, it, expect } from 'vitest'
import type { AxiosResponse } from 'axios'
import { ApiResponseHandler, StandardApiError } from '../apiService'

describe('ApiResponseHandler', () => {
  describe('extractData', () => {
    it('should handle 204 No Content responses correctly', () => {
      // Simulate axios response for HTTP 204 No Content
      const mockResponse: AxiosResponse<any> = {
        status: 204,
        statusText: 'No Content',
        data: '', // Empty string for 204 responses
        headers: {},
        config: {} as any
      }

      // This should NOT throw an error
      const result = ApiResponseHandler.extractData(mockResponse)
      expect(result).toBeUndefined()
    })

    it('should handle 204 No Content with null data', () => {
      // Some axios configurations return null for 204 responses
      const mockResponse: AxiosResponse<any> = {
        status: 204,
        statusText: 'No Content',
        data: null,
        headers: {},
        config: {} as any
      }

      const result = ApiResponseHandler.extractData(mockResponse)
      expect(result).toBeUndefined()
    })

    it('should handle successful JSON responses', () => {
      const mockData = { id: '123', title: 'Test Playlist' }
      const mockResponse: AxiosResponse<any> = {
        status: 200,
        statusText: 'OK',
        data: {
          status: 'success',
          data: mockData
        },
        headers: { 'content-type': 'application/json' },
        config: {} as any
      }

      const result = ApiResponseHandler.extractData(mockResponse)
      expect(result).toEqual(mockData)
    })

    it('should handle success response without data field by returning undefined', () => {
      const mockResponse: AxiosResponse<any> = {
        status: 200,
        statusText: 'OK',
        data: {
          status: 'success'
          // Missing data field - this is normal for operations like DELETE
        },
        headers: { 'content-type': 'application/json' },
        config: {} as any
      }

      // Should not throw an error, but return undefined for operations like DELETE
      const result = ApiResponseHandler.extractData(mockResponse)
      expect(result).toBeUndefined()
    })

    it('should handle error responses correctly', () => {
      const mockResponse: AxiosResponse<any> = {
        status: 400,
        statusText: 'Bad Request',
        data: {
          status: 'error',
          message: 'Invalid playlist ID',
          error_type: 'validation_error',
          details: { field: 'playlist_id' }
        },
        headers: { 'content-type': 'application/json' },
        config: {} as any
      }

      expect(() => ApiResponseHandler.extractData(mockResponse)).toThrow(StandardApiError)
      
      try {
        ApiResponseHandler.extractData(mockResponse)
      } catch (error) {
        expect(error).toBeInstanceOf(StandardApiError)
        const apiError = error as StandardApiError
        expect(apiError.message).toBe('Invalid playlist ID')
        expect(apiError.errorType).toBe('validation_error')
        expect(apiError.statusCode).toBe(400)
        expect(apiError.details).toEqual({ field: 'playlist_id' })
      }
    })

    it('should handle malformed response data', () => {
      // Test the original bug scenario: empty/null response parsed as object
      const mockResponse: AxiosResponse<any> = {
        status: 200,
        statusText: 'OK',
        data: '', // Empty string that might be mistaken for JSON
        headers: {},
        config: {} as any
      }

      // This should now handle gracefully and return undefined for successful status codes
      const result = ApiResponseHandler.extractData(mockResponse)
      expect(result).toBeUndefined()
    })

    it('should preserve original behavior for standard DELETE operations that return JSON', () => {
      // Some DELETE operations might return JSON with confirmation
      const mockResponse: AxiosResponse<any> = {
        status: 200,
        statusText: 'OK',
        data: {
          status: 'success',
          data: { deleted: true, id: '123' }
        },
        headers: { 'content-type': 'application/json' },
        config: {} as any
      }

      const result = ApiResponseHandler.extractData(mockResponse)
      expect(result).toEqual({ deleted: true, id: '123' })
    })

    it('should handle edge case: 204 with unexpected JSON structure', () => {
      // Edge case: server incorrectly returns JSON body with 204
      const mockResponse: AxiosResponse<any> = {
        status: 204,
        statusText: 'No Content',
        data: { some: 'unexpected data' },
        headers: { 'content-type': 'application/json' },
        config: {} as any
      }

      // Should still return undefined for 204, ignoring any body content
      const result = ApiResponseHandler.extractData(mockResponse)
      expect(result).toBeUndefined()
    })
  })

  describe('handleError', () => {
    it('should convert axios error to StandardApiError', () => {
      const axiosError: any = {
        response: {
          status: 404,
          data: {
            status: 'error',
            message: 'Playlist not found',
            error_type: 'not_found',
            request_id: 'req-123'
          }
        },
        message: 'Request failed with status code 404'
      }

      expect(() => ApiResponseHandler.handleError(axiosError)).toThrow(StandardApiError)
      
      try {
        ApiResponseHandler.handleError(axiosError)
      } catch (error) {
        const apiError = error as StandardApiError
        expect(apiError.message).toBe('Playlist not found')
        expect(apiError.errorType).toBe('not_found')
        expect(apiError.statusCode).toBe(404)
        expect(apiError.requestId).toBe('req-123')
      }
    })

    it('should handle network errors without response', () => {
      const axiosError: any = {
        request: {},
        message: 'Network Error'
      }

      expect(() => ApiResponseHandler.handleError(axiosError)).toThrow(StandardApiError)
      
      try {
        ApiResponseHandler.handleError(axiosError)
      } catch (error) {
        const apiError = error as StandardApiError
        expect(apiError.message).toBe('Network error - unable to reach server')
        expect(apiError.errorType).toBe('network_error')
        expect(apiError.statusCode).toBe(0)
      }
    })
  })
})

/**
 * Integration test simulating the exact playlist deletion scenario
 */
describe('Playlist Deletion API Integration', () => {
  it('should handle the exact deletePlaylist scenario that caused the bug', () => {
    // This simulates the exact axios response for a successful DELETE request
    // that returns HTTP 204 No Content
    const deletePlaylistResponse: AxiosResponse<any> = {
      status: 204,
      statusText: 'No Content',
      data: '', // This is what axios provides for 204 responses
      headers: {},
      config: {
        method: 'delete',
        url: '/api/playlists/916fc416-d50d-42c6-8e5d-f3bb60087c86',
        data: { client_op_id: 'delete_playlist_123' }
      } as any
    }

    // Before the fix, this would throw:
    // "Cannot read property 'status' of undefined" or similar
    // After the fix, this should work without errors
    expect(() => {
      const result = ApiResponseHandler.extractData(deletePlaylistResponse)
      expect(result).toBeUndefined() // void return type becomes undefined
    }).not.toThrow()
  })

  it('should maintain backward compatibility with JSON-returning DELETE endpoints', () => {
    // Some DELETE operations might still return JSON confirmation
    const deleteWithConfirmationResponse: AxiosResponse<any> = {
      status: 200,
      statusText: 'OK',
      data: {
        status: 'success',
        data: {
          deleted: true,
          playlist_id: '123',
          message: 'Playlist deleted successfully'
        }
      },
      headers: { 'content-type': 'application/json' },
      config: {} as any
    }

    const result = ApiResponseHandler.extractData(deleteWithConfirmationResponse)
    expect(result).toEqual({
      deleted: true,
      playlist_id: '123',
      message: 'Playlist deleted successfully'
    })
  })
})