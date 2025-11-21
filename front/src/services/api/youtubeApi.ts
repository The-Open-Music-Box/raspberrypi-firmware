/**
 * YouTube API Module
 * Handles YouTube search and download operations
 */

import { apiClient, ApiResponseHandler } from './apiClient'
import { API_ROUTES } from '../../constants/apiRoutes'
import { generateClientOpId } from '../../utils/operationUtils'
import { ApiResponse } from '../../types/contracts'

/**
 * YouTube API methods with standardized response handling
 */
export const youtubeApi = {
  /**
   * Search YouTube videos
   */
/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars */
  async searchVideos(query: string, maxResults?: number, _clientOpId?: string): Promise<{ results: any[] }> {
    const response = await apiClient.get<ApiResponse<{ results: any[] }>>(
      API_ROUTES.YOUTUBE_SEARCH,
      {
        params: {
          query,
          max_results: maxResults || 10
        }
      }
    )
    return ApiResponseHandler.extractData(response)
  },

  /**
   * Download video from YouTube URL
   */
  async downloadVideo(url: string, playlistId: string, clientOpId?: string): Promise<{ task_id: string }> {
    const response = await apiClient.post<ApiResponse<{ task_id: string }>>(
      API_ROUTES.YOUTUBE_DOWNLOAD,
      {
        url,
        playlist_id: playlistId,
        client_op_id: clientOpId || generateClientOpId('youtube_download')
      }
    )
    return ApiResponseHandler.extractData(response)
  },

  /**
   * Get YouTube download status
   */
  async getDownloadStatus(taskId: string): Promise<{ task_id: string; status: string; progress_percent?: number; current_step?: string; error_message?: string; result?: any }> {
    const response = await apiClient.get<ApiResponse<{ task_id: string; status: string; progress_percent?: number; current_step?: string; error_message?: string; result?: any }>>(
      API_ROUTES.YOUTUBE_STATUS(taskId)
/* eslint-enable @typescript-eslint/no-explicit-any */
    )
    return ApiResponseHandler.extractData(response)
  }
}