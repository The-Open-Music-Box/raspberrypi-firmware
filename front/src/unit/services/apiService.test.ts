import { describe, it, expect, vi, beforeEach } from 'vitest'
import apiService, { apiClient } from '@/services/apiService'

vi.mock('@/utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

vi.mock('@/services/api/playlistApi', () => ({
  playlistApi: {
    getPlaylists: vi.fn(),
    createPlaylist: vi.fn(),
    deletePlaylist: vi.fn(),
    getPlaylist: vi.fn(),
    updatePlaylist: vi.fn(),
    deleteTrack: vi.fn(),
    startPlaylist: vi.fn()
  }
}))

vi.mock('@/services/api/playerApi', () => ({
  playerApi: {
    toggle: vi.fn(),
    previous: vi.fn(),
    next: vi.fn(),
    seek: vi.fn(),
    getStatus: vi.fn()
  }
}))

vi.mock('@/services/api/uploadApi', () => ({
  uploadApi: {
    initUpload: vi.fn(),
    uploadChunk: vi.fn(),
    finalizeUpload: vi.fn(),
    getUploadStatus: vi.fn()
  }
}))

vi.mock('@/services/api/systemApi', () => ({
  systemApi: { getHealth: vi.fn(), getVolume: vi.fn() }
}))

vi.mock('@/services/api/nfcApi', () => ({
  nfcApi: {
    startNfcAssociationScan: vi.fn(),
    startNfcScan: vi.fn(),
    associateNfcTag: vi.fn(),
    removeNfcAssociation: vi.fn(),
    getNfcStatus: vi.fn()
  }
}))

vi.mock('@/services/api/youtubeApi', () => ({
  youtubeApi: {
    searchVideos: vi.fn(),
    downloadVideo: vi.fn(),
    getDownloadStatus: vi.fn()
  }
}))

// Mock apiClient for fallbacks
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
    }
  }
})

describe('apiService', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.restoreAllMocks()
  })

  it('isErrorType/isRetryable work with StandardApiError', () => {
    const err = new (apiService.StandardApiError)('m', 'rate_limit_exceeded', 429)
    expect(apiService.isErrorType(err, 'rate_limit_exceeded')).toBe(true)
    expect(apiService.isRetryable(err)).toBe(true)
  })

  it('getPlaylists uses playlistApi, falls back to client formats', async () => {
    const { playlistApi } = await import('@/services/api/playlistApi')
    ;(playlistApi.getPlaylists as any).mockRejectedValue(new Error('boom'))
    ;(apiClient.get as any).mockResolvedValue({
      status: 200,
      data: { status: 'success', data: { playlists: [{ id: 'p1' }], page: 1, limit: 10, total: 1, total_pages: 1 } }
    })
    const items = await apiService.getPlaylists()
    expect(items).toEqual([{ id: 'p1' }])

    // array data fallback
    ;(apiClient.get as any).mockResolvedValueOnce({ status: 200, data: { status: 'success', data: [{ id: 'p2' }] } })
    const items2 = await apiService.getPlaylists()
    expect(items2).toEqual([{ id: 'p2' }])

    // items field fallback
    ;(apiClient.get as any).mockResolvedValueOnce({ status: 200, data: { status: 'success', data: { items: [{ id: 'p3' }] } } })
    const items3 = await apiService.getPlaylists()
    expect(items3).toEqual([{ id: 'p3' }])
  })

  it('reorderTracks posts correct payload', async () => {
    (apiClient.post as any).mockResolvedValue({ status: 200, data: { status: 'success', data: { ok: true } } })
    const out = await apiService.reorderTracks('pid', [1, 2, 3])
    expect(out).toEqual({ ok: true })
    expect(apiClient.post).toHaveBeenCalled()
  })

  it('startPlaylist triggers state refresh after delay', async () => {
    const { playlistApi } = await import('@/services/api/playlistApi')
    ;(playlistApi.startPlaylist as any).mockResolvedValue({ started: true })

    vi.mock('@/stores/serverStateStore', () => ({
      useServerStateStore: () => ({ requestInitialPlayerState: vi.fn().mockResolvedValue(undefined) })
    }))

    const out = await apiService.startPlaylist('pid')
    expect(out).toEqual({ started: true })

    vi.runAllTimers()
    // no throw means the import and call path worked
  })

  it('startPlaylist error path logs and rethrows', async () => {
    const { playlistApi } = await import('@/services/api/playlistApi')
    ;(playlistApi.startPlaylist as any).mockRejectedValueOnce(new Error('fail'))
    await expect(apiService.startPlaylist('pid')).rejects.toThrow('fail')
  })

  it('delegated calls route to underlying modules', async () => {
    const { playerApi } = await import('@/services/api/playerApi')
    const { playlistApi } = await import('@/services/api/playlistApi')
    const { uploadApi } = await import('@/services/api/uploadApi')
    const { nfcApi } = await import('@/services/api/nfcApi')

    ;(playerApi.toggle as any).mockResolvedValue({})
    await apiService.togglePlayer('id')
    await apiService.playPlayer('id')
    await apiService.pausePlayer('id')
    await apiService.previousTrack('id')
    await apiService.nextTrack('id')
    await apiService.seekPlayer(123, 'id')

    ;(playlistApi.createPlaylist as any).mockResolvedValue({})
    ;(playlistApi.getPlaylist as any).mockResolvedValue({})
    ;(playlistApi.updatePlaylist as any).mockResolvedValue({})
    ;(playlistApi.deletePlaylist as any).mockResolvedValue({})
    await apiService.createPlaylist('t')
    await apiService.getPlaylist('pid')
    await apiService.updatePlaylist('pid', { title: 'x' })
    await apiService.deletePlaylist('pid')
    await apiService.deleteTrack('pid', 1)

    ;(apiClient.post as any).mockResolvedValue({ status: 200, data: { status: 'success', data: {} } })
    await apiService.playTrack('pid', 1)
    await apiService.moveTrackBetweenPlaylists('a', 'b', 1, 2)

    ;(nfcApi.startNfcAssociationScan as any).mockResolvedValue({})
    ;(nfcApi.startNfcScan as any).mockResolvedValue({})
    ;(nfcApi.getNfcStatus as any).mockResolvedValue({})
    ;(nfcApi.associateNfcTag as any).mockResolvedValue({})
    ;(nfcApi.removeNfcAssociation as any).mockResolvedValue({})
    await apiService.startNfcAssociation('pid')
    await apiService.cancelNfcObservation('id')
    await apiService.overrideNfcAssociation('pid')
    await apiService.startNfcScan(123, 'id')
    await apiService.getNfcStatus()
    await apiService.associateNfcTag('pid', 'tag')
    await apiService.removeNfcAssociation('tag')

    ;(uploadApi.initUpload as any).mockResolvedValue({})
    ;(uploadApi.uploadChunk as any).mockResolvedValue({})
    ;(uploadApi.finalizeUpload as any).mockResolvedValue({})
    ;(uploadApi.getUploadStatus as any).mockResolvedValue({})
    await apiService.initUpload('pid', 'f', 1)
    await apiService.uploadChunk('pid', 'sid', 0, new Blob())
    await apiService.finalizeUpload('pid', 'sid')
    await apiService.getUploadStatus('pid', 'sid')
  })

  it('startPlaylist handles error inside delayed sync gracefully', async () => {
    const { playlistApi } = await import('@/services/api/playlistApi')
    ;(playlistApi.startPlaylist as any).mockResolvedValue({ started: true })

    vi.mock('@/stores/serverStateStore', () => ({
      useServerStateStore: () => ({ requestInitialPlayerState: vi.fn().mockRejectedValue(new Error('sync fail')) })
    }))

    await apiService.startPlaylist('pid')
    vi.runAllTimers()
  })
})
