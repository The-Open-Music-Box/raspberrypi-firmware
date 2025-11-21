import { describe, it, expect, vi, beforeEach } from 'vitest'
import { nextTick } from 'vue'
import { setActivePinia, createPinia } from 'pinia'
import { ref } from 'vue'
import { useUploadStore } from '@/stores/uploadStore'

// Mock composable
const mockComposable = {
  uploadFiles: ref([] as any[]),
  isUploading: ref(false),
  isCancelled: ref(false),
  uploadErrors: ref([] as any[]),
  hasErrors: ref(false),
  overallProgress: ref(0),
  currentFileProgress: ref(0),
  currentFileName: ref(''),
  currentChunkIndex: ref(0),
  totalChunks: ref(0),
  stats: ref({}),
  estimatedTimeRemaining: ref(0),
  uploadSpeedFormatted: ref('0KB/s'),
  completedFiles: ref(0),
  failedFiles: ref(0),
  uploadConfig: ref({ chunkSize: 1 }),
  initializeFiles: vi.fn((files: any[]) => {
    mockComposable.uploadFiles.value = files.map((f, i) => ({ file: f, status: 'pending', index: i }))
  }),
  startUpload: vi.fn(async () => {
    mockComposable.uploadFiles.value.forEach((f: any) => (f.status = 'success'))
    mockComposable.completedFiles.value = mockComposable.uploadFiles.value.length
  }),
  cancelUpload: vi.fn(),
  resetUpload: vi.fn(),
  validateFile: vi.fn(),
  generateChecksum: vi.fn()
}

vi.mock('@/composables/useUpload', () => ({
  useUpload: () => mockComposable
}))

describe('uploadStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockComposable.uploadFiles.value = []
    mockComposable.completedFiles.value = 0
  })

  it('modal open/close updates state', () => {
    const store = useUploadStore()
    store.openUploadModal('p1')
    expect(store.isModalOpen).toBe(true)
    expect(store.modalPlaylistId).toBe('p1')
    store.closeUploadModal()
    expect(store.isModalOpen).toBe(false)
    expect(store.modalPlaylistId).toBeNull()
  })

  it('queue operations: add, remove, clear', () => {
    const store = useUploadStore()
    const f1 = new File(['a'], 'a.txt')
    store.addFilesToQueue('p1', [f1])
    // adding again to same playlist triggers existingFiles branch
    const f2 = new File(['b'], 'b.txt')
    store.addFilesToQueue('p1', [f2])
    expect(store.globalUploadQueue.get('p1')!.length).toBe(2)
    // computed helpers
    expect(store.totalPendingFiles).toBe(2)
    expect(store.globalUploadProgress).toBe(0)
    // simulate some completed files to exercise progress path
    store.globalUploadQueue.set('p1', [{ file: f1, status: 'success' } as any])
    expect(store.globalUploadProgress).toBe(100)
    // test removal branches on a fresh playlist
    const f3 = new File(['c'], 'c.txt')
    const f4 = new File(['d'], 'd.txt')
    store.addFilesToQueue('p4', [f3])
    store.addFilesToQueue('p4', [f4])
    store.removeFileFromQueue('p4', 0)
    expect(store.globalUploadQueue.get('p4')!.length).toBe(1)
    store.removeFileFromQueue('p4', 0)
    expect(store.globalUploadQueue.get('p4')).toBeUndefined()
    store.addFilesToQueue('p2', [f1])
    // remove with out-of-bounds index keeps list unchanged
    store.removeFileFromQueue('p2', 99)
    expect(store.globalUploadQueue.get('p2')!.length).toBe(1)
    store.clearQueue('p2')
    expect(store.globalUploadQueue.get('p2')).toBeUndefined()
    // clear all
    store.addFilesToQueue('p3', [f1])
    store.clearQueue()
    expect(store.globalUploadQueue.size).toBe(0)

    // hit branch: size>0 but totalFiles==0
    store.globalUploadQueue.set('empty', [] as any)
    expect(store.globalUploadProgress).toBe(0)
  })

  it('startUpload runs composable and updates history/queue', async () => {
    const store = useUploadStore()
    const f1 = new File(['a'], 'a.txt')
    store.addFilesToQueue('p1', [f1])
    // simulate active uploads
    mockComposable.isUploading.value = true
    expect(store.hasActiveUploads).toBe(true)
    await store.startUpload('p1')
    expect(store.uploadHistory.length).toBe(1)
    expect(store.globalUploadQueue.get('p1')).toBeUndefined()
    // computed after success
    expect(store.globalUploadProgress).toBe(0)
    // toggle back to inactive to exercise false branch
    mockComposable.isUploading.value = false
    await nextTick()
    expect(store.hasActiveUploads).toBe(false)
  })

  it('startUpload handles error path', async () => {
    const store = useUploadStore()
    const f1 = new File(['a'], 'a.txt')
    store.addFilesToQueue('p1', [f1])
    mockComposable.startUpload.mockRejectedValueOnce(new Error('x'))
    await expect(store.startUpload('p1')).rejects.toThrow()
    expect(store.uploadHistory[0].success).toBe(false)
  })

  it('startUpload records partial success when not all complete', async () => {
    const store = useUploadStore()
    const f1 = new File(['a'], 'a.txt')
    const f2 = new File(['b'], 'b.txt')
    store.addFilesToQueue('p1', [f1, f2])
    mockComposable.startUpload.mockImplementationOnce(async () => {
      // mark only one success
      mockComposable.uploadFiles.value.forEach((f: any, i: number) => (f.status = i === 0 ? 'success' : 'pending'))
      mockComposable.completedFiles.value = 1
    })
    await store.startUpload('p1')
    expect(store.uploadHistory[0].success).toBe(false)
  })

  it('cancel, reset, updateConfig, history utils', () => {
    const store = useUploadStore()
    store.cancelUpload()
    expect(mockComposable.cancelUpload).toHaveBeenCalled()
    // Update config mutates the ref object
    store.updateConfig({ chunkSize: 2 } as any)
    expect(mockComposable.uploadConfig.value.chunkSize).toBe(2)
    store.resetUpload()
    expect(mockComposable.resetUpload).toHaveBeenCalled()
    store.clearHistory()
    expect(store.uploadHistory.length).toBe(0)
    expect(store.getHistoryForPlaylist('x')).toEqual([])

    // branch: removeFileFromQueue when no files present
    store.removeFileFromQueue('missing', 0)
  })

  it('startUpload no-op when no files', async () => {
    const store = useUploadStore()
    await store.startUpload('none')
  })
})
