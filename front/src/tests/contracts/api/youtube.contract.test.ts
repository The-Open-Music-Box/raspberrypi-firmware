/**
 * Contract tests for YouTube API endpoints - Frontend
 *
 * Validates that frontend YouTube API calls match the backend contract.
 *
 * Progress: 3/3 endpoints tested ✅
 */

import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { youtubeApi } from '../../../services/api/youtubeApi'

const server = setupServer()

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('YouTube API Contract Tests', () => {
  it('should match contract for POST /api/youtube/download - download video', async () => {
    /**
     * Contract:
     * - Request: {url: string, playlist_id: string, client_op_id?: string}
     * - Response: {status: "success", data: {task_id, url, playlist_id?}}
     */
    server.use(
      http.post('/api/youtube/download', () => {
        return HttpResponse.json({
          status: 'success',
          data: {
            task_id: 'yt-task-123',
            url: 'https://youtube.com/watch?v=abc123',
            playlist_id: 'playlist-1'
          },
          timestamp: Date.now(),
          server_seq: 1
        })
      })
    )

    const result = await youtubeApi.downloadVideo('https://youtube.com/watch?v=abc123', 'playlist-1')

    expect(result).toBeDefined()
    expect(result.task_id).toBe('yt-task-123')
  })

  it('should match contract for GET /api/youtube/status/{task_id} - get download status', async () => {
    /**
     * Contract:
     * - Response: {status: "success", data: {task_id, status, progress_percent?, current_step?, error_message?}}
     */
    server.use(
      http.get('/api/youtube/status/:taskId', () => {
        return HttpResponse.json({
          status: 'success',
          data: {
            task_id: 'yt-task-123',
            status: 'downloading',
            progress_percent: 45.5,
            current_step: 'Downloading video'
          },
          timestamp: Date.now(),
          server_seq: 2
        })
      })
    )

    const result = await youtubeApi.getDownloadStatus('yt-task-123')

    expect(result).toBeDefined()
    expect(result.task_id).toBe('yt-task-123')
    expect(result.status).toBe('downloading')
  })

  it('should match contract for GET /api/youtube/search - search videos', async () => {
    /**
     * Contract:
     * - Query params: query: string, max_results?: number
     * - Response: {status: "success", data: {results: [{id, title, duration?, thumbnail?}]}}
     */
    server.use(
      http.get('/api/youtube/search', () => {
        return HttpResponse.json({
          status: 'success',
          data: {
            results: [
              {
                id: 'video-1',
                title: 'Test Video 1',
                duration: 180,
                thumbnail: 'https://example.com/thumb1.jpg'
              },
              {
                id: 'video-2',
                title: 'Test Video 2',
                duration: 240,
                thumbnail: 'https://example.com/thumb2.jpg'
              }
            ]
          },
          timestamp: Date.now(),
          server_seq: 3
        })
      })
    )

    const result = await youtubeApi.searchVideos('test query')

    expect(result).toBeDefined()
    expect(result.results).toBeInstanceOf(Array)
    expect(result.results).toHaveLength(2)
  })
})
