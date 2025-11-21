/**
 * NFC API Module
 * Handles NFC tag operations
 */

import { apiClient, ApiResponseHandler } from './apiClient'
import { API_ROUTES } from '../../constants/apiRoutes'
import { generateClientOpId } from '../../utils/operationUtils'
import { ApiResponse } from '../../types/contracts'

/**
 * NFC API methods with standardized response handling
 */
export const nfcApi = {
  /**
   * Associate NFC tag with playlist
   */
/* eslint-disable @typescript-eslint/no-explicit-any */
  async associateNfcTag(playlistId: string, tagId: string, clientOpId?: string): Promise<{ association: any }> {
    const response = await apiClient.post<ApiResponse<{ association: any }>>(
      API_ROUTES.NFC_ASSOCIATE,
/* eslint-enable @typescript-eslint/no-explicit-any */
      {
        playlist_id: playlistId,
        tag_id: tagId,
        client_op_id: clientOpId || generateClientOpId('nfc_associate')
      }
    )
    return ApiResponseHandler.extractData(response)
  },

  /**
   * Remove NFC tag association
   */
  async removeNfcAssociation(tagId: string, clientOpId?: string): Promise<void> {
    const response = await apiClient.delete<ApiResponse<void>>(
      API_ROUTES.NFC_REMOVE_ASSOCIATION(tagId),
      {
        data: {
          client_op_id: clientOpId || generateClientOpId('nfc_remove')
        }
      }
    )
    return ApiResponseHandler.extractData(response)
  },

  /**
   * Start NFC scan session
   */
  async startNfcScan(timeoutMs?: number, clientOpId?: string): Promise<{ scan_id: string }> {
    const response = await apiClient.post<ApiResponse<{ scan_id: string }>>(
      API_ROUTES.NFC_SCAN,
      {
        timeout_ms: timeoutMs || 60000,
        client_op_id: clientOpId || generateClientOpId('nfc_scan')
      }
    )
    return ApiResponseHandler.extractData(response)
  },

  /**
   * Start NFC association scan session for a specific playlist
   */
  async startNfcAssociationScan(playlistId: string, timeoutMs?: number, clientOpId?: string): Promise<{ scan_id: string }> {
    const response = await apiClient.post<ApiResponse<{ scan_id: string }>>(
      API_ROUTES.NFC_SCAN,
      {
        timeout_ms: timeoutMs || 60000,
        playlist_id: playlistId,
        client_op_id: clientOpId || generateClientOpId('nfc_association_scan')
      }
    )
    return ApiResponseHandler.extractData(response)
  },

  /**
   * Get NFC reader status
   */
  async getNfcStatus(): Promise<{ reader_available: boolean; scanning: boolean }> {
    const response = await apiClient.get<ApiResponse<{ reader_available: boolean; scanning: boolean }>>(
      API_ROUTES.NFC_STATUS
    )
    return ApiResponseHandler.extractData(response)
  }
}