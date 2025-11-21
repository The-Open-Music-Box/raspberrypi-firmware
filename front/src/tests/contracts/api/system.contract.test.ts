/**
 * Contract tests for System API endpoints - Frontend
 *
 * Validates that frontend system API calls match the backend contract.
 *
 * Progress: 3/3 endpoints tested ✅
 */

import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { systemApi } from '../../../services/api/systemApi'

const server = setupServer()

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('System API Contract Tests', () => {
  it('should match contract for GET /api/system/info - get system information', async () => {
    /**
     * Contract:
     * - Response: {status: "success", data: {platform, python_version?, uptime?, memory?}}
     */
    server.use(
      http.get('/api/system/info', () => {
        return HttpResponse.json({
          status: 'success',
          data: {
            platform: 'Linux',
            python_version: '3.11.0',
            uptime: 86400,
            memory: { total: 8192, available: 4096 }
          },
          timestamp: Date.now(),
          server_seq: 1
        })
      })
    )

    const result = await systemApi.getSystemInfo()

    expect(result).toBeDefined()
    expect(result.platform).toBe('Linux')
  })

  it('should match contract for GET /api/system/logs - get system logs', async () => {
    /**
     * Contract:
     * - Query params: lines?: number, level?: string
     * - Response: {status: "success", data: {logs: []}}
     */
    server.use(
      http.get('/api/system/logs', () => {
        return HttpResponse.json({
          status: 'success',
          data: {
            logs: [
              { timestamp: '2025-10-02T10:00:00Z', level: 'INFO', message: 'Log entry 1' },
              { timestamp: '2025-10-02T10:01:00Z', level: 'ERROR', message: 'Log entry 2' }
            ]
          },
          timestamp: Date.now(),
          server_seq: 2
        })
      })
    )

    const result = await systemApi.getSystemLogs(100)

    expect(result).toBeDefined()
    expect(result.logs).toBeInstanceOf(Array)
  })

  it('should match contract for POST /api/system/restart - restart system', async () => {
    /**
     * Contract:
     * - Request: {confirm: boolean}
     * - Response: {status: "success", message: "System restart initiated"}
     */
    server.use(
      http.post('/api/system/restart', () => {
        return HttpResponse.json({
          status: 'success',
          data: {
            message: 'System restart initiated'
          },
          timestamp: Date.now(),
          server_seq: 3
        })
      })
    )

    const result = await systemApi.restartSystem(true)

    expect(result).toBeDefined()
    expect(result.message).toBe('System restart initiated')
  })
})
