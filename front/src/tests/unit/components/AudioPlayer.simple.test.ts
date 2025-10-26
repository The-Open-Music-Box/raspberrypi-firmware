/**
 * Basic tests for AudioPlayer component
 */

import { describe, it, expect } from 'vitest'

describe('AudioPlayer', () => {
  it('should be importable', async () => {
    const AudioPlayer = await import('@/components/audio/AudioPlayer.vue')
    expect(AudioPlayer).toBeDefined()
    expect(AudioPlayer.default).toBeDefined()
  })
})
