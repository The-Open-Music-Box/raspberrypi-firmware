/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Playlist API Module
 * Handles all playlist related operations
 */

import { apiClient, ApiResponseHandler } from './apiClient'
import { API_ROUTES, API_CONFIG } from '../../constants/apiRoutes'
import { generateClientOpId } from '../../utils/operationUtils'
import { logger } from '../../utils/logger'
import { cacheService } from '../cacheService'
import { ApiResponse, PlayerState, Playlist, PaginatedData } from '../../types/contracts'

/**
 * Playlist API methods with standardized response handling
 */
export const playlistApi = {
  /**
   * Get paginated playlists - Updated to handle backend "playlists" field with caching
   */
  async getPlaylists(page = 1, limit = API_CONFIG.PLAYLISTS_FETCH_LIMIT): Promise<PaginatedData<Playlist>> {
    const cacheKey = `playlists_${page}_${limit}`;

    // Try to get from cache first
    const cached = cacheService.get<PaginatedData<Playlist>>(cacheKey);
    if (cached) {
      logger.debug(`Cache hit for playlists page ${page}`, { cacheKey });
      return cached;
    }

    const response = await apiClient.get<ApiResponse<{
      playlists: Playlist[];
      page: number;
      limit: number;
      total: number;
      total_pages: number;
    }>>(
      API_ROUTES.PLAYLISTS,
      { params: { page, limit } }
    )
    const data = ApiResponseHandler.extractData(response)

    // Validate that we have the expected data structure
    if (!data || typeof data !== 'object') {
      throw new Error(`API response.data is invalid: ${typeof data}`)
    }

    if (!Array.isArray(data.playlists)) {
      throw new Error(`API response.data.playlists is not an array: ${typeof data.playlists}`)
    }

    // Convert backend format to frontend PaginatedData format
    const result = {
      items: data.playlists,  // Backend uses "playlists", frontend expects "items"
      page: data.page,
      limit: data.limit,
      total: data.total,
      total_pages: data.total_pages
    }

    // Cache the result (short TTL since playlists can change frequently)
    cacheService.set(cacheKey, result, 10000); // 10 seconds
    logger.debug(`Cached playlists page ${page}`, { cacheKey });

    return result;
  },

  /**
   * Get specific playlist
   */
  async getPlaylist(id: string): Promise<Playlist> {
    const response = await apiClient.get<ApiResponse<{playlist: Playlist}>>(
      API_ROUTES.PLAYLIST(id)
    )
    const data = ApiResponseHandler.extractData(response)
    return data.playlist
  },

  /**
   * Create new playlist
   */
  async createPlaylist(title: string, description = '', clientOpId?: string): Promise<Playlist> {
    const response = await apiClient.post<ApiResponse<{playlist: Playlist}>>(
      API_ROUTES.PLAYLISTS,
      {
        title,
        description,
        client_op_id: clientOpId || generateClientOpId('api_operation')
      }
    )
    const data = ApiResponseHandler.extractData(response)
    return data.playlist
  },

  /**
   * Update playlist
   */
  async updatePlaylist(id: string, title?: string, description?: string, clientOpId?: string): Promise<Playlist> {
    const response = await apiClient.put<ApiResponse<Playlist>>(
      API_ROUTES.PLAYLIST(id),
      {
        ...(title && { title }),
        ...(description && { description }),
        client_op_id: clientOpId || generateClientOpId('api_operation')
      }
    )
    return ApiResponseHandler.extractData(response)
  },

  /**
   * Delete playlist
   */
  async deletePlaylist(id: string, clientOpId?: string): Promise<void> {
    const response = await apiClient.delete<ApiResponse<void>>(
      API_ROUTES.PLAYLIST(id),
      {
        data: {
          client_op_id: clientOpId || generateClientOpId('api_operation')
        }
      }
    )
    return ApiResponseHandler.extractData(response)
  },

  /**
   * Start playlist playback
   */
  async startPlaylist(id: string, clientOpId?: string): Promise<PlayerState> {
    const response = await apiClient.post<ApiResponse<PlayerState>>(
      API_ROUTES.PLAYLIST_START(id),
      { client_op_id: clientOpId || generateClientOpId('api_operation') }
    )
    return ApiResponseHandler.extractData(response)
  },

  /**
   * Reorder tracks in a playlist
   */
  async reorderTracks(playlistId: string, trackOrder: number[], clientOpId?: string): Promise<any> {
    const response = await apiClient.post(
      API_ROUTES.PLAYLIST_REORDER(playlistId),
      {
        track_order: trackOrder,
        client_op_id: clientOpId || generateClientOpId('api_operation')
      }
    )
    return ApiResponseHandler.extractData(response)
  },

  /**
   * Delete tracks from playlist
   */
  async deleteTracks(playlistId: string, trackNumbers: number[], clientOpId?: string): Promise<any> {
    const response = await apiClient.delete(
      API_ROUTES.DELETE_TRACKS(playlistId),
      {
        data: {
          track_numbers: trackNumbers,
          client_op_id: clientOpId || generateClientOpId('api_operation')
        }
      }
    )
    return ApiResponseHandler.extractData(response)
  },

  /**
   * Delete a single track from playlist
   */
  async deleteTrack(playlistId: string, trackNumber: number, clientOpId?: string): Promise<any> {
    return this.deleteTracks(playlistId, [trackNumber], clientOpId)
  },

  /**
   * Sync playlists with filesystem
   */
  async syncPlaylists(clientOpId?: string): Promise<any> {
    const response = await apiClient.post(
      API_ROUTES.PLAYLIST_SYNC,
      {
        client_op_id: clientOpId || generateClientOpId('api_operation')
      }
    )
    return ApiResponseHandler.extractData(response)
  },

  /**
   * Move a track within a playlist
   */
  async moveTrack(playlistId: string, fromPosition: number, toPosition: number, clientOpId?: string): Promise<any> {
    const response = await apiClient.post(
      API_ROUTES.PLAYLIST_MOVE_TRACK(playlistId),
      {
        from_position: fromPosition,
        to_position: toPosition,
        client_op_id: clientOpId || generateClientOpId('api_operation')
      }
    )
    return ApiResponseHandler.extractData(response)
  }
}