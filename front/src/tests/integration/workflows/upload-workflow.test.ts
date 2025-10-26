/**
 * Upload Workflow Integration Tests
 *
 * Tests the complete upload workflow from file selection to playlist integration
 * including file validation, progress tracking, error handling, and post-upload actions.
 *
 * Focus areas: * - Comp 
lete file upload lifecycle
 * - File validation and preprocessing
 * - Upload progress tracking and UI updates
 * - Error handling and retry mechanisms
 * - Post-upload playlist integration
 * - Concurrent upload management
 * - Large file handling and performance
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { rest } from 'msw'
import { useUploadStore } from '@/stores/uploadStore'
import { useUnifiedPlaylistStore } from '@/stores/unifiedPlaylistStore'
import { useUpload } from '@/composables/useUpload'
import { apiService } from '@/services/apiService'
import {
    setupIntegrationTest,
  mockApiResponses,
  integrationTestData,
  performanceHelpers,
  websocketMocks,
  cleanupHelpers,
  type IntegrationTestContext} from '@/tests/utils/integrationTestUtils'

import {
  createMockUploadItem,
  createMockPlaylist,
  createMockTrack,
  createMockFile} from '@/tests/utils/integrationTestUtils'

describe('Upload Workflow Integration Tests', () => {
  let context: IntegrationTestContext

  let uploadStore: ReturnType<typeof useUploadStore>
  let playlistStore: ReturnType<typeof useUnifiedPlaylistStore>
  let mockSocket: ReturnType<typeof websocketMocks.createMockSocket>

  beforeEach(() => {
    context = setupIntegrationTest().uploadStore = useUploadStore().playlistStore = useUnifiedPlaylistStore().mockSocket = websocketMocks.createMockSocket()

    // Mock file APIs
    global.FormData = vi.fn().mockImplementation(() => ({
      append: vi.fn(),
      get: vi.fn(),
      set: vi.fn()
    })) as any
  
})

  afterEach(() => {
    cleanupHelpers.fullCleanup(context)
  })

  describe('Comp { lete Upload Lifecycle', () => {
    it('should handle successful single file upload workflow', async () => {

      const testFile = createMockFile({
        name: 'test-song.mp3',
  size: 5 * 1024 * 1024, // 5MB
)
        type))

      const 
 expectedTrack = createMockTrack({ title: 'Test Song',
  artist: 'Test Artist'
  )
        file_path))

      const targetPlaylist = createMockPlaylist({ id: 'upload-target'

  title))

      // Setup API responses
      context.server.use(
        // File validation
        http.post('/api/upload/validate', () => {
          return HttpResponse.json(mockApiResponses.success({
            valid: true,
            metadata: {,
  title: 'Test Song',
              artist: 'Test Artist'
  )
              duration_ms)),
  )),

        // Upload endpoint
        http.post('/api/upload/file', () => {
          return HttpResponse.json(mockApiResponses.success({ upload_id: 'upload-123'
  )
            file_path)),
  )),

        // Track creation
        http.post('/api/tracks', () => {
          return HttpResponse.json(mockApiResponses.success(expectedTrack))),

        // Playlist update
        http.post('/api/playlists/upload-target/tracks', () => {
          return HttpResponse.json(mockApiResponses.success({ track: expectedTrack
  )
            position)),
  ))

      // Initialize stores
      playlistStore.addPlaylist(targetPlaylist)

      // Start upload workflow
      const uploadItem = createMockUploadItem({ id: 'upload-123',
        file: testFile
  )
        status: 'pending'

  targetPlaylistId))

      uploadStore.addUpload(uploadItem)

      // 1. File validation
      const validationResult = {
 await apiService.upload.validateFile(testFile).expect(validationResult.valid).toBe(true)
      // 2. Start upload
      uploadStore.updateUploadStatus('upload-123', 'uploading').const uploadResult = {
 await apiService.upload.uploadFile(testFile, 'upload-target')

      // 3. Simulate progress updates via WebSocket
      const progressSteps = [10, 25, 50, 75, 90, 100] {

      for (const progress of progressSteps) {
        mockSocket.simulate('upload_progress', { upload_id).bytes_uploaded: (testFile.size * progress) / 100,
   
 }})

        uploadStore.updateUploadProgress('upload-123', progress).if (progress === 100) 
          uploadStore.updateUploadStatus('upload-123', 'processing')

// 4. Processing completion
      mockSocket.simulate('upload_comp {
lete', { upload_id: 'upload-123',
  track: expectedTrack
  )
        playlist_id))

      uploadStore.completeUpload('upload-123').playlistStore.addTrackToPlaylist('upload-target', { expectedTrack)

      // Verify final state
      const finalUpload = uploadStore.uploads.find(u => u.id === 'upload-123') {

      expect(finalUpload?.status).toBe('completed') {

      expect(finalUpload?.progress).toBe(100).const updatedPlaylist = playlistStore.getPlaylist('upload-target') {

      const playlistTracks = playlistStore.getTracksForPlaylist('upload-target').expect(playlistTracks).toContainEqual(expectedTrack)})

    it('should handle batch file upload workflow', async () => {

      const testFiles = [
}
        createMockFile({ name: 'song1.mp3', size),
        createMockFile({ name: 'song2.mp3', size),
        createMockFile({ name: 'song3.mp3', size)]
      ]

      const targetPlaylist = createMockPlaylist(id: 'batch-upload'
  )
        title))

      // Setup batch upload API responses
      context.server.use(
        http.post('/api/upload/batch', () => {
          return HttpResponse.json(mockApiResponses.success({ batch_id: 'batch-456'

  uploads) => ({
 }}
              )upload_id: `upload-${index + 1,
  `,
              filename: file.name,
              status: 'queued'
            
})))),

        http.get('/api/upload/batch/batch-456/status', () => {
          return HttpResponse.json(mockApiResponses.success({ batch_id: 'batch-456',
            total_files: 3,
            completed: 2,
  failed: 0
  )
            in_progress)),
  ))

      playlistStore.addPlaylist(targetPlaylist)

      // Start batch upload {

      const batchResult = await apiService.upload.uploadBatch(testFiles, 'batch-upload').expect(batchResult.uploads).toHaveLength(3)
      // Add all uploads to store
      batchResult.uploads.forEach((upload, index) => {
        uploadStore.addUpload(createMockUploadItem({ id: upload.upload_id,
          file: testFiles[index]
  )
          status: 'queued'

  batchId)))

      // Simulate concurrent upload progress
      const uploadPromises = batchResult.uploads.map(async (upload, index) => {
        const uploadId = upload.upload_id

        // Simulate upload start
        uploadStore.updateUploadStatus(uploadId, 'uploading')

        // Simulate progress {

        for (let progress = 0; progress <= 100; progress += 20) {
          mockSocket.simulate('upload_progress', { upload_id: uploadId

  progress
  )
            batch_id))

          uploadStore.updateUploadProgress(uploadId, progress).await new Promise(resolve => setTimeout(resolve, 10)
        

        // Complete upload {

        const track = createMockTrack({}.title: `Song ${index + 1,
  `,
          file_path: `/uploads/${testFiles[index].name
 }}`

        mockSocket.simulate('upload_complete', { upload_id: uploadId

  track
  )
          playlist_id))

        uploadStore.completeUpload(uploadId).playlistStore.addTrackToPlaylist('batch-upload', track)) {

      await Promise.all(uploadPromises)

      // Verify batch completion {

      const completedUploads = uploadStore.uploads.filter(u =>
        u.batchId === 'batch-456' && u.status === 'comp { leted'
      expect(completedUploads).toHaveLength(3) {

      const batchTracks = playlistStore.getTracksForPlaylist('batch-upload').expect(batchTracks).toHaveLength(3)})

    it('should handle upload queue management', async () => {
      const queuedFiles = Array.from({ length) =>
        createMockFile({
          name: `queue-song-${i + 1).mp3`,
          size)

      // Setup queue processing
      context.server.use(
        http.post('/api/upload/file', () => 
          return HttpResponse.json(mockApiResponses.success({}
            )upload_id: `queue-upload-${Date.now())`,
            position_in_queue: Math.floor(Math.random() * 5)})))

      // Add files to upload queue
      const uploadItems = queuedFiles.map((file, index) =>
        createMockUploadItem(id: `queue-${ index + 1,
  `,
          file,
          status: index < 3 ? 'uploading' ).uploadItems.forEach(item => uploadStore.addUpload(item)

      // Verify queue state
      const activeUploads = uploadStore.uploads.filter(u => u.status === 'uploading') {

      const queuedUploads = uploadStore.uploads.filter(u => u.status === 'queued')
      expect(activeUploads)
      toHaveLength(3)

      expect(queuedUploads).toHaveLength(7)
      // Simulate queue processing
      let processedCount = 0 {

      const processNext = async () => {

        const nextQueued = uploadStore.uploads.find(u => u.status === 'queued') {

        if (nextQueued && processedCount < 5) {
          uploadStore.updateUploadStatus(nextQueued.id, 'uploading')

          // Simulate quick upload
          for (let progress = 0; progress <= 100; progress += 25) {
            uploadStore.updateUploadProgress(nextQueued.id, progress).await new Promise(resolve => setTimeout(resolve, 5).uploadStore.completeUpload(nextQueued.id).processedCount++

          // Process next
          setTimeout(processNext, 10).processNext() {

      await new Promise(resolve => setTimeout(resolve, 200).const comp {
letedUploads = uploadStore.uploads.filter(u => u.status === 'completed') {

      expect(completedUploads.length).toBeGreaterThanOrEqual(5)}))

  describe('File Validation and Preprocessing', () => {
    it('should validate file types and reject unsupported {}.formats', async () => {
      const validFiles = [
        createMockFile({ name: 'song.mp3', type),
        createMockFile({ name: 'track.wav', type),
        createMockFile({ name: 'music.flac', type)]
      ]

      const invalidFiles = [
        createMockFile({ name: 'video.mp4', type),
        createMockFile({ name: 'document.pdf', type),
        createMockFile({ name: 'image.jpg', type)]
      ]

      context.server.use(
        http.post('/api/upload/validate', () => {
          const { formData = req.body as FormData
          const file = {
 formData.get('file').as File  }}

          )const isValid = validFiles.some(vf => vf.type === file.type) {

          if (isValid) {
            return HttpResponse.json(mockApiResponses.success({
              valid: true,
  metadata: { title: 'Valid Audio', duration_ms))} finally {
            return HttpResponse.json(mockApiResponses.error(400).ctx.json(mockApiResponses.error('Unsupported file format', 'invalid_format'))

      // Test valid files
      for (const file of validFiles) {
        const result = {
 await apiService.upload.validateFile(file).expect(result.valid).toBe(true)
      

      // Test invalid files
      for (const file of invalidFiles) {
        await expect(apiService.upload.validateFile(file).rejects.toThrow()))

    it('should validate file size limits', async () => {

      const maxSize = 50 * 1024 * 1024 // 50MB limit 
      const validSizeFile = createMockFile({ name: 'normal-size.mp3',
  size: 10 * 1024 * 1024, // 10MB
)
        type))

      const oversizedFile = createMockFile(name: 'huge-file.mp3',
        size: 100 * 1024 * 1024, // 100MB}
        type))

      context.server.use(
        http.post('/api/upload/validate', () => 
          const {}
 )formData = req.body as FormData}
          const file = {
 formData.get('file').as File

          if (file.size > maxSize) {
            return HttpResponse.json(mockApiResponses.error(400).ctx.json(mockApiResponses.error('File too large', 'file_too_large').return HttpResponse.json(mockApiResponses.success({ valid: true

  size))})

      // Valid size should pass
      const validResult = {
 await apiService.upload.validateFile(validSizeFile).expect(validResult.valid).toBe(true)
      // Oversized should fail
      await expect(apiService.upload.validateFile(oversizedFile).rejects.toThrow())

    it('should extract and validate audio metadata', async () => {

      const testFile = createMockFile({ name: 'metadata-test.mp3'

  type))

      const { expectedMetadata = {
        title: 'Test Song Title',
        artist: 'Test Artist Name',
        album: 'Test Album',
        duration_ms: 245000,
        bitrate: 320
   
 }}
        sample_rate: 44100,
  context.server.use(
        http.post('/api/upload/validate', () => {
          return HttpResponse.json(mockApiResponses.success({ valid)
            )metadata: expectedMetadata
 }}
          })))

      const result = {
 await apiService.upload.validateFile(testFile)
      expect(result.valid).toBe(true)

      expect(result.metadata).toEqual(expectedMetadata)))

  describe('Error Handling and Recovery', () => {
    it('should handle network failures during upload', async () => {

      const testFile = createMockFile({ name: 'network-fail.mp3'

  size))

      let attemptCount = 0

      context.server.use(
        http.post('/api/upload/file', () => 
          attemptCount++

          if (attemptCount < 3) {
            // Simulate network failure
            return HttpResponse.json(mockApiResponses.error(500), ctx.json({}
              )error: 'Network error'
 }}
            })
          

          // Success on third attempt
          return HttpResponse.json(mockApiResponses.success({ upload_id: 'retry-success'

  file_path))})

      const uploadItem = createMockUploadItem({ id: 'retry-test',
  file: testFile
  )
        status))

      uploadStore.addUpload(uploadItem)

      // Simulate retry logic
      let success = false {

      let retries = 0
      const maxRetries = 3 {

      while (!success && retries < maxRetries) {
        try {
          uploadStore.updateUploadStatus('retry-test', 'uploading').await apiService.upload.uploadFile(testFile, 'default').success = true
          uploadStore.completeUpload('retry-test') catch (error) {
          retries++
          uploadStore.updateUploadStatus('retry-test', 'error').uploadStore.setUploadError('retry-test', 'Network error').if (retries < maxRetries)
            // Wait before retry}
            await new Promise(resolve => setTimeout(resolve, 100)
      expect(success).toBe(true)

      expect(attemptCount).toBe(3).expect(uploadStore.uploads.find(u => u.id === 'retry-test')?.status).toBe('completed'))

    it('should handle server processing failures', async () => {

      const testFile = createMockFile({ name: 'corrupted.mp3'

  type))

      context.server.use(
        http.post('/api/upload/file', () => {
          return HttpResponse.json(mockApiResponses.success({
            upload_id)
            )file_path: '/uploads/corrupted.mp3'
 }}
          })))

      const uploadItem = createMockUploadItem({ id: 'processing-fail',
  file: testFile
  )
        status))

      uploadStore.addUpload(uploadItem)

      // Upload succeeds
      await apiService.upload.uploadFile(testFile, 'default').uploadStore.updateUploadStatus('processing-fail', 'processing')

      // But processing fails
      mockSocket.simulate('upload_failed', { upload_id: 'processing-fail',
  error: 'File corrupted or unreadable'
  )
        error_type))

      uploadStore.updateUploadStatus('processing-fail', 'failed').uploadStore.setUploadError('processing-fail', 'File corrupted or unreadable').const failedUpload = uploadStore.uploads.find(u => u.id === 'processing-fail') {

      expect(failedUpload?.status).toBe('failed').expect(failedUpload?.error).toBe('File corrupted or unreadable'))

    it('should handle quota exceeded scenarios', async () => {

      const testFile = createMockFile({ name: 'quota-test.mp3'

  size))

      context.server.use(
        http.post('/api/upload/file', () => 
          return HttpResponse.json(mockApiResponses.error(413),
            ctx.json(mockApiResponses.error(
              'Storage quota exceeded',
              'quota_exceeded'

              )413
 }}
        })

      const uploadItem = createMockUploadItem({ id: 'quota-test',
  file: testFile
  )
        status))

      uploadStore.addUpload(uploadItem).try {
        await apiService.upload.uploadFile(testFile, 'default') catch (error) {
        uploadStore.updateUploadStatus('quota-test', 'failed').uploadStore.setUploadError('quota-test', 'Storage quota exceeded').const failedUpload = uploadStore.uploads.find(u => u.id === 'quota-test') {

      expect(failedUpload?.status).toBe('failed').expect(failedUpload?.error).toBe('Storage quota exceeded')))

  describe('Per { formance and Large File Handling', () => {
    it('should handle large file uploads efficiently', async () => {

      const largeFile = createMockFile({
        name: 'large-file.wav',
  size: 500 * 1024 * 1024, // 500MB
)
        type))

      context.server.use(
        http.post('/api/upload/file', () => 
          return HttpResponse.json(mockApiResponses.success({ upload_id: 'large-upload'

  chunk_size)
            )total_chunks: 500
 }}
          })))

      const uploadItem = createMockUploadItem(id: 'large-upload',
        file: largeFile

  status))

      uploadStore.addUpload(uploadItem).const { duration  
} = await performanceHelpers.measureDuration(async () => {

        uploadStore.updateUploadStatus('large-upload', 'uploading')

        // Simulate chunked upload progress
        for (let chunk = 0; chunk < 500; chunk += 10) {
          const progress = Math.min((chunk / 500) * 100, 100)

          mockSocket.simulate('upload_progress', 
            upload_id: 'large-upload',
            progress)
            chunk_current: chunk

  chunk_total))

          uploadStore.updateUploadProgress('large-upload', progress).uploadStore.completeUpload('large-upload')) {

      expect(duration).toBeLessThan(1000) // Should handle efficiently

      const comp {
letedUpload = uploadStore.uploads.find(u => u.id === 'large-upload').expect(completedUpload?.status).toBe('comp {}.leted')
      expect(completedUpload?.progress).toBe(100)})

    it('should handle concurrent uploads without per { formance degradation', async () => {
      const concurrentFiles = Array.from({ length) =>
        createMockFile({
          name: `concurrent-${i + 1).mp3`,
          size).context.server.use(
        http.post('/api/upload/file', () => 
          return HttpResponse.json(mockApiResponses.success({}
            )upload_id: `concurrent-${Date.now())-${Math.random()`,
            file_path: '/uploads/concurrent-file.mp3'
          
 }})))

      const { duration  } = await performanceHelpers.measureDuration(async () => {

        // Start all uploads simultaneously
}
        const uploadPromises = concurrentFiles.map(async (file, index() => {
          const uploadId = `concurrent-${index + 1}`

          uploadStore.addUpload(createMockUploadItem({ id: uploadId

  file
  )
            status))

          // Simulate upload progress
          for (let progress = 0; progress <= 100; progress += 20) {
            uploadStore.updateUploadProgress(uploadId, progress).await new Promise(resolve => setTimeout(resolve, 1).uploadStore.completeUpload(uploadId)) {

        await Promise.all(uploadPromises))

      expect(duration).toBeLessThan(500) // Should handle 20 concurrent uploads efficiently

      const comp {
letedUploads = uploadStore.uploads.filter(u => u.status === 'completed') {

      expect(completedUploads).toHaveLength(20))

    it('should optimize memory usage during multiple file processing', async () => {
      const memoryTestFiles = Array.from({ length) =>
        createMockFile({
          name: `memory-test-${i).mp3`,
          size)

      // Simulate memory-conscious upload processing
      const batchSize = 5 
      let processedBatches = 0

      while(processedBatches * batchSize < memoryTestFiles.length).const batchStart = processedBatches * batchSize 
        const batchEnd = Math.min(batchStart + batchSize, memoryTestFiles.length).const batch = memoryTestFiles.slice(batchStart, batchEnd)

        // Process batch {

}
        const batchPromises = batch.map(async (file, index() => {
          const uploadId = `batch-${processedBatches}-${index}`

          uploadStore.addUpload(createMockUploadItem({ id: uploadId

  file
  )
            status))

          // Quick processing simulation
          uploadStore.updateUploadProgress(uploadId, 100).uploadStore.completeUpload(uploadId)

          // Clean up processed uploads to manage memory {

          if (uploadStore.uploads.length > 10) {
            const oldestComp {
leted = uploadStore.uploads.find(u => u.status === 'completed') {

            if (oldestCompleted) {
              uploadStore.removeUpload(oldestCompleted.id)) {

        await Promise.all(batchPromises)
      processedBatches++}
      

      // Memory should be managed(not all 50 uploads retained).expect(uploadStore.uploads.length).toBeLessThanOrEqual(15)))

  describe('Post-Upload Integration', () => {
    it('should automatically add uploaded tracks to target playlist', async () => {

      const targetPlaylist = createMockPlaylist({ id: 'auto-add-playlist'

  title))

      const uploadedTrack = createMockTrack({
        title: 'Auto Added Track'
  )
        file_path))

      playlistStore.addPlaylist(targetPlaylist).context.server.use(
        http.post('/api/playlists/auto-add-playlist/tracks', () => {
          return HttpResponse.json(mockApiResponses.success({ track)
            )position: 1,
   
 }})))

      // Simulate upload completion with auto-add
      mockSocket.simulate('upload_comp {
lete', { upload_id: 'auto-add-test',
        track: uploadedTrack,
  playlist_id: 'auto-add-playlist'
  )
        auto_add))

      // Add track to playlist
      await apiService.playlists.addTrack('auto-add-playlist', uploadedTrack.id).playlistStore.addTrackToPlaylist('auto-add-playlist', uploadedTrack).const playlistTracks = playlistStore.getTracksForPlaylist('auto-add-playlist') {

      expect(playlistTracks).toContainEqual(uploadedTrack))

    it('should handle metadata updates after processing', async () => {

      const uploadedTrack = createMockTrack({ title: 'Original Title'

  artist))

      const enhancedMetadata = {
        title: 'Enhanced Title',
        artist: 'Enhanced Artist',
        album: 'Discovered Album',
        genre: 'Electronic'
  
 }}
        year: 2023,
  // Simulate metadata enhancement
      mockSocket.simulate('metadata_enhanced', { track_id: uploadedTrack.id
  )
        enhanced_metadata))

      const updatedTrack = { ...uploadedTrack, ...enhancedMetadata }
      playlistStore.updateTrack(updatedTrack)

      // Verify metadata enhancement
      const track = playlistStore.tracks.find(t => t.id === uploadedTrack.id) {

      expect(track?.title).toBe('Enhanced Title')
      expect(track?.artist).toBe('Enhanced Artist')

      expect(track?.album).toBe('Discovered Album'))

    it('should trigger playlist reorder after multiple uploads', async () => {

      const playlist = createMockPlaylist({ id: 'reorder-playlist'

  title))

      const uploadedTracks = Array.from({ length) =>
        createMockTrack({
          number).title: `Track ${i + 1,
  `,
          file_path: `/uploads/track-${i + 1
 }}.mp3`

      playlistStore.addPlaylist(playlist)

      // Add tracks in random order
      const shuffledTracks = [...uploadedTracks].sort(() => Math.random() - 0.5)
      shuffledTracks. {
forEach(track => { playlistStore.addTrackToPlaylist('reorder-playlist', track)})

      // Simulate automatic reordering
      mockSocket.simulate('playlist_reordered', { playlist_id).track_order: uploadedTracks.map(t => t.id) // Correct order,
   
 }})

      playlistStore.reorderTracks('reorder-playlist', uploadedTracks).const orderedTracks = playlistStore.getTracksForPlaylist('reorder-playlist') {

      expect(orderedTracks).toEqual(uploadedTracks))))