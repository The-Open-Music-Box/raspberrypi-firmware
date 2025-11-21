import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useUnifiedPlaylistStore } from '@/stores/unifiedPlaylistStore'
import { nextTick } from 'vue'

vi.mock('@/utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

// Mock socket service
vi.mock('@/services/socketService', () => ({
  default: {
    on: vi.fn(), off: vi.fn(), emit: vi.fn()
  }
}))

// Mock api service
vi.mock('@/services/apiService', () => ({
  default: {
    getPlaylists: vi.fn(),
    getPlaylist: vi.fn(),
    createPlaylist: vi.fn(),
    updatePlaylist: vi.fn(),
    deletePlaylist: vi.fn(),
    deleteTrack: vi.fn(),
    reorderTracks: vi.fn(),
    moveTrackBetweenPlaylists: vi.fn()
  }
}))

describe('unifiedPlaylistStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })

  const sample = () => ({ id: 'p1', title: 'T', tracks: [{ track_number: 1, title: 'a' }] })

  it('initialize loads playlists and sets initialized', async () => {
    const store = useUnifiedPlaylistStore()
    const api = (await import('@/services/apiService')).default as any
    api.getPlaylists.mockResolvedValue([sample()])
    await store.initialize()
    expect(store.isInitialized).toBeTruthy()
    expect(store.getAllPlaylists.length).toBe(1)
  })

  it('loadAllPlaylists stores playlists and tracks', async () => {
    const store = useUnifiedPlaylistStore()
    const api = (await import('@/services/apiService')).default as any
    api.getPlaylists.mockResolvedValue([
      { id: 'p1', title: 'A', tracks: [{ track_number: 1 }] },
      { id: 'p2', title: 'B', tracks: [] }
    ])
    await store.loadAllPlaylists()
    expect(store.getAllPlaylists.length).toBe(2)
    expect(store.getTracksForPlaylist('p1').length).toBe(1)
  })

  it('loadPlaylistTracks uses cache and fetches when missing', async () => {
    const store = useUnifiedPlaylistStore()
    const api = (await import('@/services/apiService')).default as any
    api.getPlaylists.mockResolvedValue([sample()])
    await store.loadAllPlaylists()
    // Should fetch fresh because getTracksForPlaylist('p1') already has 1
    api.getPlaylist.mockResolvedValue({ ...sample(), tracks: [{ track_number: 1 }, { track_number: 2 }] })
    const list = await store.loadPlaylistTracks('p1')
    expect(list.length).toBeGreaterThan(0)
  })

  it('create/update/delete playlist and delete track and reorder', async () => {
    const store = useUnifiedPlaylistStore()
    const api = (await import('@/services/apiService')).default as any
    api.getPlaylists.mockResolvedValue([{ id: 'p1', title: 'A', tracks: [{ track_number: 1 }, { track_number: 2 }] }])
    await store.loadAllPlaylists()

    // createPlaylist
    api.createPlaylist.mockResolvedValue({ id: 'p2', title: 'B' })
    const id = await store.createPlaylist('B')
    expect(id).toBe('p2')

    // updatePlaylist
    await store.updatePlaylist('p1', { title: 'Ax' })
    expect(store.getPlaylistById('p1')?.title).toBe('Ax')

    // deletePlaylist
    await store.deletePlaylist('p2')
    expect(store.getPlaylistById('p2')).toBeUndefined()

    // deleteTrack updates track_count
    api.deleteTrack.mockResolvedValue({})
    await store.deleteTrack('p1', 1)
    expect(store.getTracksForPlaylist('p1').some(t => t.track_number === 1)).toBe(false)

    // reorderTracks
    api.reorderTracks.mockResolvedValue({})
    await store.reorderTracks('p1', [2])
    expect(store.getTracksForPlaylist('p1')[0].track_number).toBe(1)
  })

  it('websocket handlers cover branches', async () => {
    const store = useUnifiedPlaylistStore()
    const api = (await import('@/services/apiService')).default as any
    const sock = (await import('@/services/socketService') as any).default

    // seed data - tracks now need IDs for reordering
    api.getPlaylists.mockResolvedValue([{
      id: 'p1',
      title: 'A',
      tracks: [
        { id: 'track-2', track_number: 2, title: 'Track 2' },
        { id: 'track-1', track_number: 1, title: 'Track 1' }
      ]
    }])
    await store.initialize()

    // capture handlers
    const onCalls = (sock.on as any).mock.calls as any[]
    const getHandler = (event: string) => {
      const call = onCalls.find(c => c[0] === event)
      expect(call, `handler for ${event}`).toBeDefined()
      return call[1]
    }

    const hPlaylist = getHandler('state:playlist')
    const hPlaylists = getHandler('state:playlists')
    const hTrackAdded = getHandler('state:track_added')
    const hTrack = getHandler('state:track')
    const hTrackDeleted = getHandler('state:track_deleted')
    const hCreated = getHandler('state:playlist_created')
    const hUpdated = getHandler('state:playlist_updated')
    const hDeleted = getHandler('state:playlist_deleted')
    const hNfc = getHandler('nfc_association_state')

    // handlePlaylistStateUpdate with and without tracks
    hPlaylist({ data: { id: 'p1', title: 'Ax' } })
    expect(store.getPlaylistById('p1')!.title).toBe('Ax')
    hPlaylist({ data: { id: 'p1', title: 'Ay', tracks: [{ track_number: 3 }] } })
    expect(store.getTracksForPlaylist('p1').some(t => t.track_number === 3)).toBe(true)

    // handlePlaylistsStateUpdate normal
    hPlaylists({ data: { playlists: [{ id: 'p1', title: 'Az', tracks: [{ track_number: 1 }, { number: 2 }] }] } })
    expect(store.getPlaylistById('p1')!.title).toBe('Az')
    // playlists update without tracks field
    hPlaylists({ data: { playlists: [{ id: 'p1', title: 'NoTracks' }] } })
    expect(store.getPlaylistById('p1')!.title).toBe('NoTracks')
    // playlists update with track missing both number fields to hit fallback 0
    hPlaylists({ data: { playlists: [{ id: 'p1', title: 'Fallback0', tracks: [{}] }] } })
    expect(store.getPlaylistById('p1')!.title).toBe('Fallback0')
    // skip branch via ongoing drag: restore valid tracks first, then start reorder without awaiting
    hPlaylists({ data: { playlists: [{
      id: 'p1',
      title: 'BeforeReorder',
      tracks: [
        { id: 'track-2', track_number: 2, title: 'Track 2' },
        { id: 'track-1', track_number: 1, title: 'Track 1' }
      ]
    }] } })
    const deferred: any = {}
    api.reorderTracks.mockImplementation(() => new Promise(resolve => (deferred.resolve = resolve)))
    store.reorderTracks('p1', [2, 1]) // don't await so ongoing flag stays
    hPlaylists({ data: { playlists: [{ id: 'p1', title: 'Skip', tracks: [{ track_number: 9 }] }] } })
    expect(store.getPlaylistById('p1')!.title).not.toBe('Skip')
    deferred.resolve({})

    // handleTrackAdded new and duplicate paths
    hTrackAdded({ playlist_id: 'p1', track: { track_number: 10 } })
    const countAfterAdd = store.getTracksForPlaylist('p1').length
    hTrackAdded({ playlist_id: 'p1', track: { track_number: 10 } }) // duplicate, no change
    expect(store.getTracksForPlaylist('p1').length).toBe(countAfterAdd)
    // add track with no number fields to hit fallback
    hTrackAdded({ playlist_id: 'p1', track: {} })

    // handleTrack update found and not found
    hTrack({ id: 'tX', track_number: 10 })
    hTrack({ id: 'nope', track_number: 999 }) // no effect

    // handleTrackDeleted present and absent playlist
    hTrackDeleted({ playlist_id: 'p1', track_numbers: [10] })
    hTrackDeleted({ playlist_id: 'absent', track_numbers: [1] })

    // playlist created/updated/deleted with/without tracks
    hCreated({ data: { playlist: { id: 'p2', title: 'B' } } })
    expect(store.getPlaylistById('p2')!.title).toBe('B')
    hUpdated({ data: { playlist: { id: 'p2', title: 'B2', tracks: [{ track_number: 1 }] } } })
    expect(store.getTracksForPlaylist('p2').length).toBe(1)
    // updated without tracks
    hUpdated({ data: { playlist: { id: 'p2', title: 'B3' } } })
    expect(store.getPlaylistById('p2')!.title).toBe('B3')
    hDeleted({ data: { playlist_id: 'p2' } })
    expect(store.getPlaylistById('p2')).toBeUndefined()
    // created with tracks
    hCreated({ data: { playlist: { id: 'p3', title: 'C', tracks: [{ track_number: 1 }] } } })
    expect(store.getTracksForPlaylist('p3').length).toBe(1)

    // NFC association success/removal branches
    hNfc({ data: { playlist_id: 'p1', state: 'success', tag_id: 'tag1' } })
    expect(store.getPlaylistById('p1')!.nfc_tag_id).toBe('tag1')
    hNfc({ data: { playlist_id: 'p1', state: 'removed' } })
    expect(store.getPlaylistById('p1')!.nfc_tag_id).toBeUndefined()

    // guard clauses
    hPlaylist({})
    hPlaylists({})
    hTrackAdded({})
    hTrack({})
    hTrackDeleted({})
    hCreated({})
    hUpdated({})
    hDeleted({})
    hNfc({})
  })

  it('getters and helpers cover both branches', async () => {
    const store = useUnifiedPlaylistStore()
    const api = (await import('@/services/apiService')).default as any
    api.getPlaylists.mockResolvedValue([{ id: 'p1', title: 'A', tracks: [] }])
    await store.loadAllPlaylists()

    expect(store.hasPlaylistData('missing')).toBe(false)
    expect(store.hasPlaylistData('p1')).toBe(true)
    expect(store.hasTracksData('p1')).toBe(false)
    const withTracks = (store.getPlaylistWithTracks as any)('p1')
    expect(withTracks.tracks.length).toBe(0)
    expect((store.getPlaylistWithTracks as any)('missing')).toBeUndefined()

    // Fallback path for getTrackByNumberOptimized (no index map yet)
    store.setTracksOptimistic('p1', [{ track_number: 7 } as any])
    expect(store.getTrackByNumberOptimized('p1', 7)!.track_number).toBe(7)
  })

  it('initialize and load error paths set error and throw', async () => {
    const store = useUnifiedPlaylistStore()
    const api = (await import('@/services/apiService')).default as any
    api.getPlaylists.mockRejectedValueOnce(new Error('fail'))
    await expect(store.initialize()).rejects.toThrow()
    // invalid data format path in loadAllPlaylists
    api.getPlaylists.mockResolvedValueOnce({ not: 'array' })
    await expect(store.loadAllPlaylists()).rejects.toThrow()
  })

  it('loadPlaylistTracks branches and error', async () => {
    const store = useUnifiedPlaylistStore()
    const api = (await import('@/services/apiService')).default as any
    api.getPlaylists.mockResolvedValue([{ id: 'p1', title: 'A', tracks: [{ track_number: 1 }] }])
    await store.loadAllPlaylists()
    // hasTracksData true: returns current
    const t1 = await store.loadPlaylistTracks('p1')
    expect(t1.length).toBe(1)
    // clear and fetch from api path
    store.clearPlaylistTracks('p1')
    api.getPlaylist.mockResolvedValue({ id: 'p1', title: 'A', tracks: [{ track_number: 2 }] })
    const t2 = await store.loadPlaylistTracks('p1')
    expect(t2[0].track_number).toBe(2)
    // error path
    store.clearPlaylistTracks('p1')
    api.getPlaylist.mockRejectedValueOnce(new Error('x'))
    await expect(store.loadPlaylistTracks('p1')).rejects.toThrow()
    // path: playlist fetch without tracks returns []
    store.clearPlaylistTracks('p1')
    api.getPlaylist.mockResolvedValueOnce({ id: 'p1', title: 'A' })
    const empty = await store.loadPlaylistTracks('p1')
    expect(empty).toEqual([])
  })

  it('reorderTracks error 404 path removes playlist and resyncs', async () => {
    vi.useFakeTimers()
    const store = useUnifiedPlaylistStore()
    const api = (await import('@/services/apiService')).default as any
    api.getPlaylists.mockResolvedValue([{ id: 'p1', title: 'A', tracks: [{ track_number: 1 }] }])
    await store.loadAllPlaylists()
    api.reorderTracks.mockRejectedValueOnce({ response: { status: 404 } })
    // make the scheduled resync fail once to hit the logger.error catch path
    api.getPlaylists.mockRejectedValueOnce(new Error('sync fail'))
    await expect(store.reorderTracks('p1', [1])).rejects.toThrow()
    // playlist deleted and resync scheduled
    vi.advanceTimersByTime(1000)
    await nextTick()
    expect(store.getPlaylistById('p1')).toBeUndefined()
    vi.useRealTimers()
  })

  it('moveTrackBetweenPlaylists success and error', async () => {
    const store = useUnifiedPlaylistStore()
    const api = (await import('@/services/apiService')).default as any
    api.moveTrackBetweenPlaylists.mockResolvedValueOnce({})
    await store.moveTrackBetweenPlaylists('a', 'b', 1)
    api.moveTrackBetweenPlaylists.mockRejectedValueOnce(new Error('oops'))
    await expect(store.moveTrackBetweenPlaylists('a', 'b', 1)).rejects.toThrow()
  })

  it('deleteTrack when no tracks present does not throw', async () => {
    const store = useUnifiedPlaylistStore()
    const api = (await import('@/services/apiService')).default as any
    api.deleteTrack.mockResolvedValueOnce({})
    await expect(store.deleteTrack('none', 1)).resolves.toBeUndefined()
  })

  it('createPlaylist error path throws and deleteTrack error path throws', async () => {
    const store = useUnifiedPlaylistStore()
    const api = (await import('@/services/apiService')).default as any
    api.createPlaylist.mockRejectedValueOnce(new Error('fail'))
    await expect(store.createPlaylist('Z')).rejects.toThrow()

    api.deleteTrack.mockRejectedValueOnce(new Error('err'))
    await expect(store.deleteTrack('pX', 1)).rejects.toThrow()
  })

  it('reorderTracks generic error path (non-404)', async () => {
    const store = useUnifiedPlaylistStore()
    const api = (await import('@/services/apiService')).default as any
    api.getPlaylists.mockResolvedValue([{ id: 'p1', title: 'A', tracks: [{ track_number: 1 }] }])
    await store.loadAllPlaylists()
    api.reorderTracks.mockRejectedValueOnce(new Error('generic'))
    await expect(store.reorderTracks('p1', [1])).rejects.toThrow()
  })

  it('reorderTracks 404 via status property (not response)', async () => {
    const store = useUnifiedPlaylistStore()
    const api = (await import('@/services/apiService')).default as any
    api.getPlaylists.mockResolvedValue([{ id: 'p1', title: 'A', tracks: [{ track_number: 1 }] }])
    await store.loadAllPlaylists()
    api.reorderTracks.mockRejectedValueOnce({ status: 404 })
    await expect(store.reorderTracks('p1', [1])).rejects.toThrow()
  })

  it('hasTracksData true and getTrackByNumber getter', async () => {
    const store = useUnifiedPlaylistStore()
    const api = (await import('@/services/apiService')).default as any
    api.getPlaylists.mockResolvedValue([{ id: 'p1', title: 'A', tracks: [{ track_number: 7 }] }])
    await store.loadAllPlaylists()
    expect(store.hasTracksData('p1')).toBe(true)
    const getByNum = (store.getTrackByNumber as any)('p1', 7)
    expect(getByNum.track_number).toBe(7)
  })

  it('getter edges: unknown playlist and legacy number field', async () => {
    const store = useUnifiedPlaylistStore()
    const api = (await import('@/services/apiService')).default as any
    api.getPlaylists.mockResolvedValue([{ id: 'p1', title: 'A', tracks: [{ number: 3 }] }])
    await store.loadAllPlaylists()
    expect(store.getTracksForPlaylist('missing')).toEqual([])
    const legacy = (store.getTrackByNumber as any)('p1', 3)
    expect(legacy.number).toBe(3)
    expect(store.getTrackByNumberOptimized('missing', 1)).toBeNull()
  })

  it('optimized getter, reorder success, and error branches for updates', async () => {
    const store = useUnifiedPlaylistStore()
    const api = (await import('@/services/apiService')).default as any
    const tracksData = [
      { id: 'track-1', track_number: 1, title: 'Track 1' },
      { id: 'track-2', track_number: 2, title: 'Track 2' }
    ]
    api.getPlaylists.mockResolvedValue([{ id: 'p1', title: 'A', tracks: tracksData }])
    await store.loadAllPlaylists()
    // build index map via loadPlaylistTracks path
    api.getPlaylist.mockResolvedValue({ id: 'p1', title: 'A', tracks: tracksData })
    await store.loadPlaylistTracks('p1')
    expect(store.getTrackByNumberOptimized('p1', 2)!.track_number).toBe(2)

    // reorder success
    api.reorderTracks.mockResolvedValueOnce({})
    await store.reorderTracks('p1', [2, 1])
    expect(store.getTracksForPlaylist('p1')[0].track_number).toBe(1)

    // reorder with unknown track number (filters undefined entries)
    api.reorderTracks.mockResolvedValueOnce({})
    await store.reorderTracks('p1', [999, 1])
    expect(store.getTracksForPlaylist('p1').length).toBeGreaterThan(0)

    // updatePlaylist error path
    api.updatePlaylist.mockRejectedValueOnce(new Error('bad'))
    await expect(store.updatePlaylist('p1', { title: 'X' })).rejects.toThrow()

    // deletePlaylist error path
    api.deletePlaylist.mockRejectedValueOnce(new Error('bad'))
    await expect(store.deletePlaylist('p1')).rejects.toThrow()

    // initialize early-return when already initialized
    api.getPlaylists.mockResolvedValueOnce([])
    await store.initialize()
    await store.initialize()
  })

  it('forceSync triggers reload of playlists', async () => {
    const store = useUnifiedPlaylistStore()
    const api = (await import('@/services/apiService')).default as any
    api.getPlaylists.mockResolvedValue([{ id: 'pf', title: 'F', tracks: [] }])
    await store.forceSync()
    expect(store.getPlaylistById('pf')!.title).toBe('F')
  })

  it('deleteTrack when tracks present but playlist metadata missing', async () => {
    const store = useUnifiedPlaylistStore()
    const api = (await import('@/services/apiService')).default as any
    api.deleteTrack.mockResolvedValueOnce({})
    store.setTracksOptimistic('px', [{ track_number: 1 } as any, { track_number: 2 } as any])
    await expect(store.deleteTrack('px', 1)).resolves.toBeUndefined()
  })

  it('forceSync calls loadAllPlaylists', async () => {
    const store = useUnifiedPlaylistStore()
    const api = (await import('@/services/apiService')).default as any
    api.getPlaylists.mockResolvedValue([sample()])
    await store.forceSync()
    expect(store.getAllPlaylists.length).toBe(1)
  })

  it('cleanup unsubscribes listeners', async () => {
    const store = useUnifiedPlaylistStore()
    store.cleanup()
    const sock = (await import('@/services/socketService') as any).default
    expect(sock.off).toHaveBeenCalled()
  })
})
