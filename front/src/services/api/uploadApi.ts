/**
 * Upload API Module
 * Handles file upload operations
 */

import { apiClient, ApiResponseHandler } from './apiClient'
import { API_ROUTES } from '../../constants/apiRoutes'
import { generateClientOpId } from '../../utils/operationUtils'
import { ApiResponse, Track, UploadStatus } from '../../types/contracts'

/**
 * Upload API methods with standardized response handling
 */
export const uploadApi = {
  /**
   * Initialize upload session
   */
  async initUpload(playlistId: string, filename: string, fileSize: number): Promise<{ session_id: string; chunk_size: number }> {
    const response = await apiClient.post<ApiResponse<{ session_id: string; chunk_size: number }>>(
      API_ROUTES.PLAYLIST_UPLOAD_SESSION(playlistId),
      {
        filename,
        file_size: fileSize
      }
    )
    return ApiResponseHandler.extractData(response)
  },

  /**
   * Upload file chunk
   */
  async uploadChunk(
    playlistId: string,
    sessionId: string,
    chunkIndex: number,
    chunk: Blob
  ): Promise<{ progress: number }> {
    const formData = new FormData()
    formData.append('file', chunk)

    const response = await apiClient.put<ApiResponse<{ progress: number }>>(
      API_ROUTES.PLAYLIST_UPLOAD_CHUNK(playlistId, sessionId, chunkIndex),
      formData
    )
    return ApiResponseHandler.extractData(response)
  },

  /**
   * Finalize upload
   */
  async finalizeUpload(playlistId: string, sessionId: string, clientOpId?: string): Promise<Track> {
    const response = await apiClient.post<ApiResponse<Track>>(
      API_ROUTES.PLAYLIST_UPLOAD_FINALIZE(playlistId, sessionId),
      { client_op_id: clientOpId || generateClientOpId('api_operation') }
    )
    return ApiResponseHandler.extractData(response)
  },

  /**
   * Get upload status
   */
  async getUploadStatus(playlistId: string, sessionId: string): Promise<UploadStatus> {
    const response = await apiClient.get<ApiResponse<UploadStatus>>(
      API_ROUTES.PLAYLIST_UPLOAD_STATUS(playlistId, sessionId)
    )
    return ApiResponseHandler.extractData(response)
  },

  /**
   * List all upload sessions
   */
  /* eslint-disable @typescript-eslint/no-explicit-any */
  async listUploadSessions(): Promise<{ sessions: any[] }> {
    const response = await apiClient.get<ApiResponse<{ sessions: any[] }>>(
      API_ROUTES.UPLOAD_SESSIONS_LIST
  /* eslint-enable @typescript-eslint/no-explicit-any */
    )
    return ApiResponseHandler.extractData(response)
  },

  /**
   * Cancel/delete upload session
   */
  async deleteUploadSession(sessionId: string): Promise<void> {
    const response = await apiClient.delete<ApiResponse<void>>(
      API_ROUTES.UPLOAD_SESSION_DELETE(sessionId)
    )
    return ApiResponseHandler.extractData(response)
  },

  /**
   * Clean up orphaned upload files
   */
  async cleanupUploads(): Promise<{ cleaned_files: number; freed_bytes: number }> {
    const response = await apiClient.post<ApiResponse<{ cleaned_files: number; freed_bytes: number }>>(
      API_ROUTES.UPLOAD_CLEANUP
    )
    return ApiResponseHandler.extractData(response)
  }
}