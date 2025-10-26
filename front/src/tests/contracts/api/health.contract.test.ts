/**
 * Contract tests for Health API endpoint - Frontend
 *
 * Validates that frontend health check calls match the backend contract.
 *
 * Progress: 1/1 endpoints tested ✅
 */

import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { systemApi } from '../../../services/api/systemApi'

const server = setupServer()

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('Health API Contract Tests', () => {
  it('should match contract for GET /api/health - health check', async () => {
    /**
     * Contract:
     * - Response: {status: "success", data: {status: string, uptime: number}}
     * - Should be fast (<100ms)
     */
    server.use(
      http.get('/api/health', () => {
        return HttpResponse.json({
          status: 'success',
          data: {
            status: 'healthy',
            uptime: 86400
          },
          timestamp: Date.now(),
          server_seq: 1
        })
      })
    )

    const result = await systemApi.getHealth()

    expect(result).toBeDefined()
    expect(result.status).toBe('healthy')
    expect(result.uptime).toBeGreaterThan(0)
  })
})
