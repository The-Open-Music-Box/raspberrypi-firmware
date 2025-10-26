/* eslint-disable @typescript-eslint/no-non-null-assertion */
/**
 * Player API Module
 * Handles all audio player related operations
 */

import { API_ROUTES } from '../../constants/apiRoutes'
import { generateClientOpId } from '../../utils/operationUtils'
import { ApiResponse, PlayerState } from '../../types/contracts'
import { apiClient, ApiResponseHandler } from './apiClient'

/**
 * Player API methods with standardized response handling
 */
export const playerApi = {
  /**
   * Get current player status
   */
  async getStatus(): Promise<PlayerState> {
    const response = await apiClient.get<ApiResponse<PlayerState>>(API_ROUTES.PLAYER_STATUS)
    return ApiResponseHandler.extractData(response)
  },

  /**
   * Start/resume playback
   */
  async play(clientOpId?: string): Promise<PlayerState> {
    const response = await apiClient.post<ApiResponse<PlayerState>>(
      API_ROUTES.PLAYER_PLAY,
      { client_op_id: clientOpId || generateClientOpId('api_operation') }
    )
    return ApiResponseHandler.extractData(response)
  },

  /**
   * Pause playback
   */
  async pause(clientOpId?: string): Promise<PlayerState> {
    const response = await apiClient.post<ApiResponse<PlayerState>>(
      API_ROUTES.PLAYER_PAUSE,
      { client_op_id: clientOpId || generateClientOpId('api_operation') }
    )
    return ApiResponseHandler.extractData(response)
  },

  /**
   * Stop playback
   */
  async stop(clientOpId?: string): Promise<PlayerState> {
    const response = await apiClient.post<ApiResponse<PlayerState>>(
      API_ROUTES.PLAYER_STOP,
      { client_op_id: clientOpId || generateClientOpId('api_operation') }
    )
    return ApiResponseHandler.extractData(response)
  },

  /**
   * Skip to next track
   */
  async next(clientOpId?: string): Promise<PlayerState> {
    const response = await apiClient.post<ApiResponse<PlayerState>>(
      API_ROUTES.PLAYER_NEXT,
      { client_op_id: clientOpId || generateClientOpId('api_operation') }
    )
    return ApiResponseHandler.extractData(response)
  },

  /**
   * Skip to previous track
   */
  async previous(clientOpId?: string): Promise<PlayerState> {
    const response = await apiClient.post<ApiResponse<PlayerState>>(
      API_ROUTES.PLAYER_PREVIOUS,
      { client_op_id: clientOpId || generateClientOpId('api_operation') }
    )
    return ApiResponseHandler.extractData(response)
  },

  /**
   * Toggle play/pause
   */
  async toggle(clientOpId?: string): Promise<PlayerState> {
    const response = await apiClient.post<ApiResponse<PlayerState>>(
      API_ROUTES.PLAYER_TOGGLE,
      { client_op_id: clientOpId || generateClientOpId('api_operation') }
    )
    return ApiResponseHandler.extractData(response)
  },

  /**
   * Seek to position
   */
  async seek(positionMs: number, clientOpId?: string): Promise<PlayerState> {
    const payload = {
      position_ms: positionMs,
      client_op_id: clientOpId || generateClientOpId('api_operation')
    }

    const response = await apiClient.post<ApiResponse<PlayerState>>(
      API_ROUTES.PLAYER_SEEK,
      payload
    )
    return ApiResponseHandler.extractData(response)
  },

  /**
   * Set volume
   */
  async setVolume(volume: number, clientOpId?: string): Promise<PlayerState> {
    const response = await apiClient.post<ApiResponse<PlayerState>>(
      API_ROUTES.VOLUME,
      {
        volume,
        client_op_id: clientOpId || generateClientOpId('api_operation')
      }
    )
    return ApiResponseHandler.extractData(response)
  }
}