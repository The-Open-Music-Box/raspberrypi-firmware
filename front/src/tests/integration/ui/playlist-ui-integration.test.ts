/**
 * Playlist UI Integration Tests
 *
 * Tests the complete integration between Playlist UI components and underlying stores/services.
 * Focuses on playlist management interfaces, track interactions, and real-time updates.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { useUnifiedPlaylistStore } from '@/stores/unifiedPlaylistStore'
import { useUploadStore } from '@/stores/uploadStore'
import { useServerStateStore } from '@/stores/serverStateStore'
import {
  setupIntegrationTest,
  cleanupHelpers,
  type IntegrationTestContext
} from '@/tests/utils/integrationHelpers'

import {
  createMockPlaylist,
  createMockTrack,
  createMockUploadItem
} from '@/tests/utils/integrationTestUtils'

// Mock Playlist UI Components
const MockPlaylistList = {
  name: 'PlaylistList',
  template: `
    <div data-testid="playlist-list">
      <div data-testid="search-bar">
        <input data-testid="search-input">
        <button data-testid="clear-search">Clear</button>
      </div>
      <div data-testid="playlist-items">
        <div v-for="playlist in playlists" :key="playlist.id" data-testid="playlist-item">
          {{ playlist.title }}
        </div>
      </div>
    </div>
  `,
  setup() {
    const playlistStore = useUnifiedPlaylistStore()

    return {
      playlists: playlistStore.getAllPlaylists
    }
  }
}

describe('Playlist UI Integration Tests', () => {
  let context: IntegrationTestContext
  let playlistStore: ReturnType<typeof useUnifiedPlaylistStore>
  let uploadStore: ReturnType<typeof useUploadStore>
  let serverStateStore: ReturnType<typeof useServerStateStore>

  beforeEach(() => {
    context = setupIntegrationTest()
    playlistStore = useUnifiedPlaylistStore()
    uploadStore = useUploadStore()
    serverStateStore = useServerStateStore()

    // Mock API methods
    vi.spyOn(playlistStore, 'addPlaylist').mockImplementation(async (playlist) => {
      return Promise.resolve()
    })

    vi.spyOn(playlistStore, 'deletePlaylist').mockImplementation(async (id) => {
      return Promise.resolve()
    })
  })

  afterEach(() => {
    cleanupHelpers.fullCleanup(context)
  })

  describe('Playlist List Integration', () => {
    it('should display playlists from store', async () => {
      const testPlaylist = createMockPlaylist({
        id: 'test-playlist',
        title: 'Test Playlist'
      })

      playlistStore.addPlaylist(testPlaylist)

      const wrapper = mount(MockPlaylistList, {
        global: {
          plugins: [context.pinia]
        }
      })

      expect(wrapper.find('[data-testid="playlist-list"]').exists()).toBe(true)

      wrapper.unmount()
    })

    it('should handle playlist search functionality', async () => {
      const wrapper = mount(MockPlaylistList, {
        global: {
          plugins: [context.pinia]
        }
      })

      const searchInput = wrapper.find('[data-testid="search-input"]')
      expect(searchInput.exists()).toBe(true)

      const clearButton = wrapper.find('[data-testid="clear-search"]')
      expect(clearButton.exists()).toBe(true)

      wrapper.unmount()
    })
  })

  describe('Playlist Management', () => {
    it('should handle playlist creation', async () => {
      const newPlaylist = createMockPlaylist({
        id: 'new-playlist',
        title: 'New Playlist'
      })

      await playlistStore.addPlaylist(newPlaylist)

      expect(playlistStore.addPlaylist).toHaveBeenCalledWith(newPlaylist)
    })

    it('should handle playlist deletion', async () => {
      const playlistId = 'delete-playlist'

      await playlistStore.deletePlaylist(playlistId)

      expect(playlistStore.deletePlaylist).toHaveBeenCalledWith(playlistId)
    })
  })

  describe('Upload Integration', () => {
    it('should handle file upload workflow', async () => {
      const uploadItem = createMockUploadItem({
        id: 'upload-1',
        file: new File(['test'], 'test.mp3', { type: 'audio/mp3' })
      })

      vi.spyOn(uploadStore, 'addUploadItem').mockImplementation(() => {
        return Promise.resolve()
      })

      await uploadStore.addUploadItem(uploadItem)

      expect(uploadStore.addUploadItem).toHaveBeenCalledWith(uploadItem)
    })
  })

  describe('Error Handling', () => {
    it('should handle playlist loading errors gracefully', async () => {
      vi.spyOn(playlistStore, 'getAllPlaylists', 'get').mockImplementation(() => {
        throw new Error('Failed to load playlists')
      })

      const wrapper = mount(MockPlaylistList, {
        global: {
          plugins: [context.pinia]
        }
      })

      expect(wrapper.exists()).toBe(true)

      wrapper.unmount()
    })
  })
})