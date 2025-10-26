/**
 * Contract tests for NFC API endpoints - Frontend
 *
 * Validates that frontend NFC API calls match the backend contract.
 *
 * Progress: 4/4 endpoints tested ✅
 */

import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { nfcApi } from '../../../services/api/nfcApi'

const server = setupServer()

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('NFC API Contract Tests', () => {
  it('should match contract for POST /api/nfc/associate - associate NFC tag', async () => {
    /**
     * Contract:
     * - Request: {tag_id: string, playlist_id: string, client_op_id?: string}
     * - Response: {status: "success", data: {tag_id, playlist_id}}
     */
    server.use(
      http.post('/api/nfc/associate', () => {
        return HttpResponse.json({
          status: 'success',
          data: {
            association: {
              tag_id: 'tag-123',
              playlist_id: 'playlist-456'
            }
          },
          timestamp: Date.now(),
          server_seq: 1
        })
      })
    )

    const result = await nfcApi.associateNfcTag('playlist-456', 'tag-123')

    expect(result).toBeDefined()
    expect(result.association.tag_id).toBe('tag-123')
    expect(result.association.playlist_id).toBe('playlist-456')
  })

  it('should match contract for DELETE /api/nfc/associate/{tag_id} - remove association', async () => {
    /**
     * Contract:
     * - Request: {client_op_id?: string}
     * - Response: 204 No Content or 200 with success
     */
    server.use(
      http.delete('/api/nfc/associate/:tagId', () => {
        return new HttpResponse(null, { status: 204 })
      })
    )

    await expect(nfcApi.removeNfcAssociation('tag-123')).resolves.not.toThrow()
  })

  it('should match contract for GET /api/nfc/status - get NFC reader status', async () => {
    /**
     * Contract:
     * - Response: {status: "success", data: {reader_available: bool, scanning: bool}}
     */
    server.use(
      http.get('/api/nfc/status', () => {
        return HttpResponse.json({
          status: 'success',
          data: {
            reader_available: true,
            scanning: false
          },
          timestamp: Date.now(),
          server_seq: 2
        })
      })
    )

    const result = await nfcApi.getNfcStatus()

    expect(result).toBeDefined()
    expect(result.reader_available).toBe(true)
    expect(result.scanning).toBe(false)
  })

  it('should match contract for POST /api/nfc/scan - start NFC scan', async () => {
    /**
     * Contract:
     * - Request: {timeout_ms?: number, playlist_id?: string, client_op_id?: string}
     * - Response: {status: "success", data: {scan_id, timeout_ms}}
     */
    server.use(
      http.post('/api/nfc/scan', () => {
        return HttpResponse.json({
          status: 'success',
          data: {
            scan_id: 'scan-789',
            timeout_ms: 60000
          },
          timestamp: Date.now(),
          server_seq: 3
        })
      })
    )

    const result = await nfcApi.startNfcScan()

    expect(result).toBeDefined()
    expect(result.scan_id).toBe('scan-789')
  })
})
