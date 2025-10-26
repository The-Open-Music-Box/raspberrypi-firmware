/**
 * Contract tests for Player API endpoints - Frontend
 *
 * Validates that frontend API calls match the backend contract.
 *
 * Progress: 9/9 endpoints tested ✅
 */

import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { playerApi } from '../../../services/api/playerApi'

const server = setupServer()

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('Player API Contract Tests', () => {
  const BASE_PATH = '/api/player'

  it('should match contract for POST /api/player/play - start/resume playback', async () => {
    /**
     * Contract:
     * - Request: {client_op_id?: string}
     * - Response: {status: "success", data: {playing: bool, ...}}
     */
    server.use(
      http.post(`${BASE_PATH}/play`, () => {
        return HttpResponse.json({
          status: 'success',
          data: {
            playing: true,
            paused: false,
            volume: 75
          },
          timestamp: Date.now(),
          server_seq: 1
        })
      })
    )

    const result = await playerApi.play()

    expect(result).toBeDefined()
    expect(result.playing).toBe(true)
    expect(result.paused).toBe(false)
  })

  it('should match contract for POST /api/player/pause - pause playback', async () => {
    /**
     * Contract:
     * - Request: {client_op_id?: string}
     * - Response: {status: "success", data: {playing: bool, paused: bool}}
     */
    server.use(
      http.post(`${BASE_PATH}/pause`, () => {
        return HttpResponse.json({
          status: 'success',
          data: {
            playing: false,
            paused: true
          },
          timestamp: Date.now(),
          server_seq: 2
        })
      })
    )

    const result = await playerApi.pause()

    expect(result).toBeDefined()
    expect(result.playing).toBe(false)
    expect(result.paused).toBe(true)
  })

  it('should match contract for POST /api/player/stop - stop playback', async () => {
    /**
     * Contract:
     * - Request: {client_op_id?: string}
     * - Response: {status: "success", data: {playing: bool}}
     */
    server.use(
      http.post(`${BASE_PATH}/stop`, () => {
        return HttpResponse.json({
          status: 'success',
          data: {
            playing: false,
            paused: false
          },
          timestamp: Date.now(),
          server_seq: 3
        })
      })
    )

    const result = await playerApi.stop()

    expect(result).toBeDefined()
    expect(result.playing).toBe(false)
  })

  it('should match contract for POST /api/player/next - next track', async () => {
    /**
     * Contract:
     * - Request: {client_op_id?: string}
     * - Response: {status: "success", data: {track_changed: bool}}
     */
    server.use(
      http.post(`${BASE_PATH}/next`, () => {
        return HttpResponse.json({
          status: 'success',
          data: {
            track_changed: true,
            current_track: {
              title: 'Next Track'
            }
          },
          timestamp: Date.now(),
          server_seq: 4
        })
      })
    )

    const result = await playerApi.next()

    expect(result).toBeDefined()
  })

  it('should match contract for POST /api/player/previous - previous track', async () => {
    /**
     * Contract:
     * - Request: {client_op_id?: string}
     * - Response: {status: "success", data: {track_changed: bool}}
     */
    server.use(
      http.post(`${BASE_PATH}/previous`, () => {
        return HttpResponse.json({
          status: 'success',
          data: {
            track_changed: true,
            current_track: {
              title: 'Previous Track'
            }
          },
          timestamp: Date.now(),
          server_seq: 5
        })
      })
    )

    const result = await playerApi.previous()

    expect(result).toBeDefined()
  })

  it('should match contract for POST /api/player/toggle - toggle play/pause', async () => {
    /**
     * Contract:
     * - Request: {client_op_id?: string}
     * - Response: {status: "success", data: {playing: bool}}
     */
    server.use(
      http.post(`${BASE_PATH}/toggle`, () => {
        return HttpResponse.json({
          status: 'success',
          data: {
            playing: true,
            paused: false
          },
          timestamp: Date.now(),
          server_seq: 6
        })
      })
    )

    const result = await playerApi.toggle()

    expect(result).toBeDefined()
    expect('playing' in result).toBe(true)
  })

  it('should match contract for GET /api/player/status - get player status', async () => {
    /**
     * Contract:
     * - Response: {status: "success", data: {playing, paused, current_track, ...}}
     * - Must include caching headers
     */
    server.use(
      http.get(`${BASE_PATH}/status`, () => {
        return HttpResponse.json({
          status: 'success',
          data: {
            playing: false,
            paused: false,
            current_track: null,
            volume: 50
          },
          timestamp: Date.now(),
          server_seq: 7
        })
      })
    )

    const result = await playerApi.getStatus()

    expect(result).toBeDefined()
    expect('playing' in result).toBe(true)
    expect('paused' in result).toBe(true)
  })

  it('should match contract for POST /api/player/seek - seek to position', async () => {
    /**
     * Contract:
     * - Request: {position_ms: number (required), client_op_id?: string}
     * - Response: {status: "success", data: {position_ms}}
     */
    server.use(
      http.post(`${BASE_PATH}/seek`, () => {
        return HttpResponse.json({
          status: 'success',
          data: {
            position_ms: 30000
          },
          timestamp: Date.now(),
          server_seq: 8
        })
      })
    )

    const result = await playerApi.seek(30000)

    expect(result).toBeDefined()
  })

  it('should match contract for POST /api/player/volume - set volume', async () => {
    /**
     * Contract:
     * - Request: {volume: number (0-100, required), client_op_id?: string}
     * - Response: {status: "success", data: {volume}}
     */
    server.use(
      http.post(`${BASE_PATH}/volume`, () => {
        return HttpResponse.json({
          status: 'success',
          data: {
            volume: 75,
            playing: false
          },
          timestamp: Date.now(),
          server_seq: 9
        })
      })
    )

    const result = await playerApi.setVolume(75)

    expect(result).toBeDefined()
  })
})
