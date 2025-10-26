/**
 * Basic tests for useUpload composable
 */

import { describe, it, expect } from 'vitest'
import { useUpload } from '@/composables/useUpload'

describe('useUpload', () => {
  it('should be importable and return an object', () => {
    const upload = useUpload()
    expect(upload).toBeDefined()
    expect(typeof upload).toBe('object')
  })
})
