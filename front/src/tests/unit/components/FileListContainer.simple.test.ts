/**
 * Basic tests for FileListContainer component
 */

import { describe, it, expect } from 'vitest'

describe('FileListContainer', () => {
  it('should be importable', async () => {
    const FileListContainer = await import('@/components/files/FileListContainer.vue')
    expect(FileListContainer).toBeDefined()
    expect(FileListContainer.default).toBeDefined()
  })
})
