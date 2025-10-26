import { describe, it, expect, vi, beforeEach } from 'vitest'
import { playlistApi } from '@/services/api/playlistApi'
import { playerApi } from '@/services/api/playerApi'
import { uploadApi } from '@/services/api/uploadApi'
import { systemApi } from '@/services/api/systemApi'
import { nfcApi } from '@/services/api/nfcApi'
import { youtubeApi } from '@/services/api/youtubeApi'

vi.mock('@/utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

vi.mock('@/services/api/apiClient', async (orig) => {
  const actual = await (orig as any)()
  return {
    ...actual,
    apiClient: {
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      delete: vi.fn(),
      interceptors: { request: { handlers: [] }, response: { handlers: [] } }
    },
    ApiResponseHandler: {
      extractData: (res: any) => res.data.data
    }
  }
})

describe('services api modules', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('playlistApi basic flows', async () => {
    const { apiClient } = await import('@/services/api/apiClient')

    ;(apiClient.get as any).mockResolvedValue({
      status: 200,
      data: { status: 'success', data: { playlists: [{ id: 'a' }], page: 1, limit: 10, total: 1, total_pages: 1 } }
    })
    const page = await playlistApi.getPlaylists(1, 10)
    expect(page.items[0].id).toBe('a')

    ;(apiClient.get as any).mockResolvedValue({ status: 200, data: { status: 'success', data: { playlist: { id: 'p1' } } } })
    expect(await playlistApi.getPlaylist('p1')).toEqual({ id: 'p1' })

    ;(apiClient.post as any).mockResolvedValue({ status: 200, data: { status: 'success', data: { playlist: { id: 'np' } } } })
    expect(await playlistApi.createPlaylist('t')).toEqual({ id: 'np' })

    ;(apiClient.put as any).mockResolvedValue({ status: 200, data: { status: 'success', data: { id: 'up' } } })
    expect(await playlistApi.updatePlaylist('id', 'title')).toEqual({ id: 'up' })

    ;(apiClient.delete as any).mockResolvedValue({ status: 200, data: { status: 'success', data: undefined } })
    await playlistApi.deletePlaylist('id')

    ;(apiClient.post as any).mockResolvedValue({ status: 200, data: { status: 'success', data: { started: true } } })
    expect(await playlistApi.startPlaylist('id')).toEqual({ started: true })

    ;(apiClient.delete as any).mockResolvedValue({ status: 200, data: { status: 'success', data: { ok: true } } })
    expect(await playlistApi.deleteTrack('pid', 1)).toEqual({ ok: true })
  })

  it('playlistApi getPlaylists validation errors', async () => {
    const { apiClient } = await import('@/services/api/apiClient')
    // data is invalid (null)
    ;(apiClient.get as any).mockResolvedValue({ status: 200, data: { status: 'success', data: null } })
    await expect(playlistApi.getPlaylists(1, 1)).rejects.toThrow(/invalid/)

    // playlists is not array
    ;(apiClient.get as any).mockResolvedValue({ status: 200, data: { status: 'success', data: { playlists: 'nope', page: 1, limit: 1, total: 1, total_pages: 1 } } })
    await expect(playlistApi.getPlaylists(1, 1)).rejects.toThrow(/not an array/)
  })

  it('playerApi flows', async () => {
    const { apiClient } = await import('@/services/api/apiClient')
    ;(apiClient.get as any).mockResolvedValue({ status: 200, data: { status: 'success', data: { st: 1 } } })
    expect(await playerApi.getStatus()).toEqual({ st: 1 })

    ;(apiClient.post as any).mockResolvedValue({ status: 200, data: { status: 'success', data: { st: 2 } } })
    expect(await playerApi.toggle()).toEqual({ st: 2 })
    expect(await playerApi.next()).toEqual({ st: 2 })
    expect(await playerApi.previous()).toEqual({ st: 2 })
    expect(await playerApi.stop()).toEqual({ st: 2 })
    expect(await playerApi.seek(123)).toEqual({ st: 2 })
    expect(await playerApi.setVolume(50)).toEqual({ st: 2 })
  })

  it('uploadApi flows', async () => {
    const { apiClient } = await import('@/services/api/apiClient')
    ;(apiClient.post as any).mockResolvedValue({ status: 200, data: { status: 'success', data: { session_id: 's', chunk_size: 5 } } })
    expect(await uploadApi.initUpload('p', 'f', 1)).toEqual({ session_id: 's', chunk_size: 5 })

    ;(apiClient.put as any).mockResolvedValue({ status: 200, data: { status: 'success', data: { progress: 10 } } })
    expect(await uploadApi.uploadChunk('p', 's', 0, new Blob())).toEqual({ progress: 10 })

    ;(apiClient.post as any).mockResolvedValue({ status: 200, data: { status: 'success', data: { id: 't' } } })
    expect(await uploadApi.finalizeUpload('p', 's')).toEqual({ id: 't' })

    ;(apiClient.get as any).mockResolvedValue({ status: 200, data: { status: 'success', data: { state: 'ok' } } })
    expect(await uploadApi.getUploadStatus('p', 's')).toEqual({ state: 'ok' })

    ;(apiClient.get as any).mockResolvedValue({ status: 200, data: { status: 'success', data: { sessions: [1] } } })
    expect(await uploadApi.listUploadSessions()).toEqual({ sessions: [1] })

    ;(apiClient.delete as any).mockResolvedValue({ status: 200, data: { status: 'success', data: undefined } })
    await uploadApi.deleteUploadSession('s')

    ;(apiClient.post as any).mockResolvedValue({ status: 200, data: { status: 'success', data: { cleaned_files: 1, freed_bytes: 2 } } })
    expect(await uploadApi.cleanupUploads()).toEqual({ cleaned_files: 1, freed_bytes: 2 })
  })

  it('systemApi flows', async () => {
    const { apiClient } = await import('@/services/api/apiClient')
    ;(apiClient.get as any).mockResolvedValue({ status: 200, data: { status: 'success', data: { status: 'ok', uptime: 1 } } })
    expect(await systemApi.getHealth()).toEqual({ status: 'ok', uptime: 1 })
    ;(apiClient.get as any).mockResolvedValue({ status: 200, data: { status: 'success', data: { volume: 10, muted: false } } })
    expect(await systemApi.getVolume()).toEqual({ volume: 10, muted: false })
  })

  it('nfcApi flows', async () => {
    const { apiClient } = await import('@/services/api/apiClient')
    ;(apiClient.post as any).mockResolvedValue({ status: 200, data: { status: 'success', data: { association: { ok: true } } } })
    expect(await nfcApi.associateNfcTag('p', 't')).toEqual({ association: { ok: true } })

    ;(apiClient.delete as any).mockResolvedValue({ status: 200, data: { status: 'success', data: undefined } })
    await nfcApi.removeNfcAssociation('tag')

    ;(apiClient.post as any).mockResolvedValue({ status: 200, data: { status: 'success', data: { scan_id: 'sid' } } })
    expect(await nfcApi.startNfcScan()).toEqual({ scan_id: 'sid' })
    expect(await nfcApi.startNfcAssociationScan('p')).toEqual({ scan_id: 'sid' })

    ;(apiClient.get as any).mockResolvedValue({ status: 200, data: { status: 'success', data: { reader_available: true, scanning: false } } })
    expect(await nfcApi.getNfcStatus()).toEqual({ reader_available: true, scanning: false })
  })

  it('youtubeApi flows', async () => {
    const { apiClient } = await import('@/services/api/apiClient')
    ;(apiClient.get as any).mockResolvedValue({ status: 200, data: { status: 'success', data: { results: [1] } } })
    expect(await youtubeApi.searchVideos('x')).toEqual({ results: [1] })

    ;(apiClient.post as any).mockResolvedValue({ status: 200, data: { status: 'success', data: { task_id: 'id' } } })
    expect(await youtubeApi.downloadVideo('u', 'p')).toEqual({ task_id: 'id' })

    ;(apiClient.get as any).mockResolvedValue({ status: 200, data: { status: 'success', data: { task_id: 'id', status: 'ok' } } })
    expect(await youtubeApi.getDownloadStatus('id')).toEqual({ task_id: 'id', status: 'ok' })
  })
})
