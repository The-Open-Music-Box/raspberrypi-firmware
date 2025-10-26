/**
 * Basic tests for SimpleUploader component
 */

import { describe, it, expect } from 'vitest'

describe('SimpleUploader', () => {
  it('should be importable', async () => {
    const SimpleUploader = await import('@/components/upload/SimpleUploader.vue')
    expect(SimpleUploader).toBeDefined()
    expect(SimpleUploader.default).toBeDefined()
  })
})
