/**
 * Contract tests for Playlist API endpoints - Frontend
 *
 * Validates that frontend API calls match the backend contract.
 *
 * Progress: 10/10 endpoints tested ✅
 */

import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { playlistApi } from '../../../services/api/playlistApi'

const server = setupServer()

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('Playlist API Contract Tests', () => {
  const BASE_PATH = '/api/playlists'

  it('should match contract for GET /api/playlists - list playlists', async () => {
    /**
     * Contract:
     * - Query params: page?: number, limit?: number
     * - Response: {status: "success", data: {playlists: [], page, limit, total, total_pages}}
     * - Status code: 200
     */
    server.use(
      http.get(`${BASE_PATH}/`, () => {
        return HttpResponse.json({
          status: 'success',
          data: {
            playlists: [
              { id: 'playlist-1', title: 'Test Playlist 1', tracks: [] },
              { id: 'playlist-2', title: 'Test Playlist 2', tracks: [] }
            ],
            page: 1,
            limit: 50,
            total: 2,
            total_pages: 1
          },
          timestamp: Date.now(),
          server_seq: 1
        })
      })
    )

    const result = await playlistApi.getPlaylists(1, 50)

    expect(result).toBeDefined()
    expect(result.items).toBeInstanceOf(Array)
    expect(result.page).toBe(1)
    expect(result.limit).toBe(50)
    expect(result.total).toBe(2)
    expect(result.total_pages).toBe(1)
  })

  it('should match contract for POST /api/playlists - create playlist', async () => {
    /**
     * Contract:
     * - Request: {title: string, description?: string, client_op_id?: string}
     * - Response: {status: "success", data: {playlist}}
     * - Status code: 201
     */
    server.use(
      http.post(`${BASE_PATH}/`, async () => {
        return HttpResponse.json({
          status: 'success',
          data: {
            playlist: {
              id: 'new-playlist-123',
              title: 'New Playlist',
              description: 'Test description',
              tracks: []
            }
          },
          timestamp: Date.now(),
          server_seq: 2
        }, { status: 201 })
      })
    )

    const result = await playlistApi.createPlaylist('New Playlist', 'Test description')

    expect(result).toBeDefined()
    expect(result.id).toBe('new-playlist-123')
    expect(result.title).toBe('New Playlist')
  })

  it('should match contract for GET /api/playlists/{id} - get playlist', async () => {
    /**
     * Contract:
     * - Path param: playlist_id
     * - Response: {status: "success", data: {playlist with tracks}}
     */
    server.use(
      http.get(`${BASE_PATH}/:id`, () => {
        return HttpResponse.json({
          status: 'success',
          data: {
            playlist: {
              id: 'playlist-456',
              title: 'Test Playlist',
              tracks: [
                { id: 'track-1', title: 'Track 1', number: 1 }
              ]
            }
          },
          timestamp: Date.now(),
          server_seq: 3
        })
      })
    )

    const result = await playlistApi.getPlaylist('playlist-456')

    expect(result).toBeDefined()
    expect(result.id).toBe('playlist-456')
    expect(result.tracks).toBeInstanceOf(Array)
  })

  it('should match contract for PUT /api/playlists/{id} - update playlist', async () => {
    /**
     * Contract:
     * - Request: {title?: string, description?: string, client_op_id?: string}
     * - Response: {status: "success", data: {client_op_id}}
     */
    server.use(
      http.put(`${BASE_PATH}/:id`, () => {
        return HttpResponse.json({
          status: 'success',
          data: {
            client_op_id: 'client-op-123'
          },
          timestamp: Date.now(),
          server_seq: 4
        })
      })
    )

    const result = await playlistApi.updatePlaylist('playlist-789', { title: 'Updated Title' })

    expect(result).toBeDefined()
  })

  it('should match contract for DELETE /api/playlists/{id} - delete playlist', async () => {
    /**
     * Contract:
     * - Request: {client_op_id?: string}
     * - Response: 204 No Content or 200 with success
     */
    server.use(
      http.delete(`${BASE_PATH}/:id`, () => {
        return new HttpResponse(null, { status: 204 })
      })
    )

    await expect(playlistApi.deletePlaylist('playlist-delete')).resolves.not.toThrow()
  })

  it('should match contract for POST /api/playlists/{id}/reorder', async () => {
    /**
     * Contract:
     * - Request: {track_order: number[], client_op_id?: string}
     * - Response: {status: "success", data: {playlist_id, client_op_id}}
     */
    server.use(
      http.post(`${BASE_PATH}/:id/reorder`, () => {
        return HttpResponse.json({
          status: 'success',
          data: {
            playlist_id: 'playlist-reorder',
            client_op_id: 'client-op-reorder'
          },
          timestamp: Date.now(),
          server_seq: 5
        })
      })
    )

    const result = await playlistApi.reorderTracks('playlist-reorder', [2, 1, 3])

    expect(result).toBeDefined()
  })

  it('should match contract for DELETE /api/playlists/{id}/tracks', async () => {
    /**
     * Contract:
     * - Request: {track_numbers: number[], client_op_id?: string}
     * - Response: {status: "success", data: {client_op_id}}
     */
    server.use(
      http.delete(`${BASE_PATH}/:id/tracks`, () => {
        return HttpResponse.json({
          status: 'success',
          data: {
            client_op_id: 'client-op-delete-tracks'
          },
          timestamp: Date.now(),
          server_seq: 6
        })
      })
    )

    const result = await playlistApi.deleteTracks('playlist-tracks', [1, 2])

    expect(result).toBeDefined()
  })

  it('should match contract for POST /api/playlists/{id}/start', async () => {
    /**
     * Contract:
     * - Request: {track_number?: number, client_op_id?: string}
     * - Response: {status: "success", data: {client_op_id}}
     */
    server.use(
      http.post(`${BASE_PATH}/:id/start`, () => {
        return HttpResponse.json({
          status: 'success',
          data: {
            client_op_id: 'client-op-start'
          },
          timestamp: Date.now(),
          server_seq: 7
        })
      })
    )

    const result = await playlistApi.startPlaylist('playlist-start', 1)

    expect(result).toBeDefined()
  })

  it('should match contract for POST /api/playlists/sync', async () => {
    /**
     * Contract:
     * - Request: {client_op_id?: string}
     * - Response: {status: "success", data: {synced_count}}
     */
    server.use(
      http.post(`${BASE_PATH}/sync`, () => {
        return HttpResponse.json({
          status: 'success',
          data: {
            synced_count: 5
          },
          timestamp: Date.now(),
          server_seq: 8
        })
      })
    )

    const result = await playlistApi.syncPlaylists()

    expect(result).toBeDefined()
  })

  it('should match contract for POST /api/playlists/{id}/move-track', async () => {
    /**
     * Contract:
     * - Request: {from_position: number, to_position: number, client_op_id?: string}
     * - Response: {status: "success", data: {client_op_id}}
     */
    server.use(
      http.post(`${BASE_PATH}/:id/move-track`, () => {
        return HttpResponse.json({
          status: 'success',
          data: {
            client_op_id: 'client-op-move'
          },
          timestamp: Date.now(),
          server_seq: 9
        })
      })
    )

    const result = await playlistApi.moveTrack('playlist-move', 1, 3)

    expect(result).toBeDefined()
  })
})
