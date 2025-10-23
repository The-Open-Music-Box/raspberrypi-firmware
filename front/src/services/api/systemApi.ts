/**
 * System API Module
 * Handles system-related operations
 */

import { apiClient, ApiResponseHandler } from './apiClient'
import { API_ROUTES } from '../../constants/apiRoutes'
import { ApiResponse, HealthStatus, SystemInfo } from '../../types/contracts'

/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * System API methods with standardized response handling
 */
export const systemApi = {
  /**
   * Get system information
   */
  async getSystemInfo(): Promise<SystemInfo> {
    const response = await apiClient.get<ApiResponse<SystemInfo>>(
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
  async getHealth(): Promise<HealthStatus> {
    const response = await apiClient.get<ApiResponse<HealthStatus>>(
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