/**
 * System API Module
 * Handles system-related operations
 */

import { apiClient, ApiResponseHandler } from './apiClient'
import { API_ROUTES } from '../../constants/apiRoutes'
import { ApiResponse } from '../../types/contracts'

/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * System API methods with standardized response handling
 */
export const systemApi = {
  /**
   * Get system information
   */
  async getSystemInfo(): Promise<{ platform: string; python_version?: string; uptime?: number; memory?: any }> {
    const response = await apiClient.get<ApiResponse<{ platform: string; python_version?: string; uptime?: number; memory?: any }>>(
      API_ROUTES.SYSTEM_INFO
    )
    return ApiResponseHandler.extractData(response)
  },

  /**
   * Get system logs
   */
  async getSystemLogs(lines?: number, level?: string): Promise<{ logs: any[] }> {
    const response = await apiClient.get<ApiResponse<{ logs: any[] }>>(
      API_ROUTES.SYSTEM_LOGS,
      {
        params: {
          lines: lines || 100,
          ...(level && { level })
        }
      }
    )
    return ApiResponseHandler.extractData(response)
  },

  /**
   * Restart system
   */
  async restartSystem(confirm: boolean): Promise<{ message: string }> {
    const response = await apiClient.post<ApiResponse<{ message: string }>>(
      API_ROUTES.SYSTEM_RESTART,
      { confirm }
    )
    return ApiResponseHandler.extractData(response)
  },

  /**
   * Get system health
   */
  async getHealth(): Promise<{ status: string; uptime: number }> {
    const response = await apiClient.get<ApiResponse<{ status: string; uptime: number }>>(
      API_ROUTES.HEALTH
    )
    return ApiResponseHandler.extractData(response)
  },

  /**
   * Get system volume
   */
  async getVolume(): Promise<{ volume: number; muted: boolean }> {
    const response = await apiClient.get<ApiResponse<{ volume: number; muted: boolean }>>(
      API_ROUTES.VOLUME
    )
    return ApiResponseHandler.extractData(response)
  }
}
/* eslint-enable @typescript-eslint/no-explicit-any */