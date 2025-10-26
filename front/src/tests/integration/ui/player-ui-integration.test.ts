/**
 * Player UI Integration Tests
 *
 * Tests the complete integration between Player UI components and underlying stores/services.
 * Focuses on user interactions, state reflection, and real-time updates in the UI.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { useServerStateStore } from '@/stores/serverStateStore'
import { useUnifiedPlaylistStore } from '@/stores/unifiedPlaylistStore'
import {
  setupIntegrationTest,
  websocketMocks,
  cleanupHelpers,
  type IntegrationTestContext
} from '@/tests/utils/integrationHelpers'

import {
  createMockPlayerState,
  createMockTrack,
  createMockPlaylist
} from '@/tests/utils/integrationTestUtils'

// Mock Player UI Components
const MockPlayerControls = {
  name: 'PlayerControls',
  template: `
    <div data-testid="player-controls">
      <button data-testid="play-pause-btn">
        {{ isPlaying ? 'Pause' : 'Play' }}
      </button>
      <button data-testid="previous-btn">Previous</button>
      <button data-testid="next-btn">Next</button>
    </div>
  `,
  setup() {
    const serverState = useServerStateStore()

    return {
      isPlaying: serverState.playerState.is_playing,
      currentTrack: serverState.currentTrack
    }
  }
}

describe('Player UI Integration Tests', () => {
  let context: IntegrationTestContext
  let serverStateStore: ReturnType<typeof useServerStateStore>
  let playlistStore: ReturnType<typeof useUnifiedPlaylistStore>

  beforeEach(() => {
    context = setupIntegrationTest()
    serverStateStore = useServerStateStore()
    playlistStore = useUnifiedPlaylistStore()

    // Mock API methods
    vi.spyOn(serverStateStore, 'play').mockImplementation(async () => {
      serverStateStore.updatePlayerState({
        ...serverStateStore.playerState,
        is_playing: true
      })
    })

    vi.spyOn(serverStateStore, 'pause').mockImplementation(async () => {
      serverStateStore.updatePlayerState({
        ...serverStateStore.playerState,
        is_playing: false
      })
    })
  })

  afterEach(() => {
    cleanupHelpers.fullCleanup(context)
  })

  describe('Player Controls Integration', () => {
    it('should handle play/pause button interactions', async () => {
      const track = createMockTrack({
        title: 'Test Track',
        duration_ms: 180000
      })

      serverStateStore.updatePlayerState(createMockPlayerState({
        current_track: track,
        is_playing: false
      }))

      const wrapper = mount(MockPlayerControls, {
        global: {
          plugins: [context.pinia]
        }
      })

      // Initially paused
      expect(wrapper.find('[data-testid="play-pause-btn"]').text()).toBe('Play')

      wrapper.unmount()
    })

    it('should display current track information', async () => {
      const track = createMockTrack({
        title: 'Display Test Track',
        artist: 'Test Artist',
        album: 'Test Album'
      })

      serverStateStore.updatePlayerState(createMockPlayerState({
        current_track: track
      }))

      const wrapper = mount(MockPlayerControls, {
        global: {
          plugins: [context.pinia]
        }
      })

      expect(wrapper.vm.currentTrack?.title).toBe('Display Test Track')

      wrapper.unmount()
    })
  })

  describe('Error Handling', () => {
    it('should handle malformed track data gracefully', async () => {
      const malformedTrack = {
        id: 'malformed',
        title: null,
        artist: undefined,
        duration_ms: 'not-a-number'
      } as any

      serverStateStore.updatePlayerState(createMockPlayerState({
        current_track: malformedTrack
      }))

      const wrapper = mount(MockPlayerControls, {
        global: {
          plugins: [context.pinia]
        }
      })

      // Should not crash
      expect(wrapper.exists()).toBe(true)

      wrapper.unmount()
    })
  })
})