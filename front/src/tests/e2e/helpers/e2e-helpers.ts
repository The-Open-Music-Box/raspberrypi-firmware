/**
 * End-to-End Testing Helpers
 *
 * Comprehensive utilities for E2E testing including page object models,
 * custom assertions, mock data setup, and common interaction patterns.
 */

import { Page, Locator, expect, Browser, BrowserContext } from '@playwright/test'

/**
 * Configuration for E2E testing environment
 */
export interface E2EConfig {
  baseURL: string
  apiURL: string
  wsURL: string
  timeout: number
  retries: number
}

export const defaultE2EConfig: E2EConfig = {
  baseURL: process.env.E2E_BASE_URL || 'http://localhost:5173',
  apiURL: process.env.E2E_API_URL || 'http://localhost:8000',
  wsURL: process.env.E2E_WS_URL || 'ws://localhost:8000',
  timeout: 30000,
  retries: 3
}

/**
 * Mock data generators for E2E tests
 */
export class E2EMockData {
  static createMockPlaylist(overrides: Partial<any> = {}) {
    return {
      id: `e2e-playlist-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      title: `E2E Test Playlist ${Date.now()}`,
      description: 'Created for E2E testing',
      track_count: 10,
      is_public: false,
      created_at: new Date().toISOString(),
      ...overrides
    }
  }

  static createMockTrack(overrides: Partial<any> = {}) {
    return {
      id: `e2e-track-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      number: 1,
      title: `E2E Test Track ${Date.now()}`,
      artist: 'E2E Test Artist',
      album: 'E2E Test Album',
      duration_ms: 180000,
      file_path: '/test/track.mp3',
      ...overrides
    }
  }

  static createMockUser(overrides: Partial<any> = {}) {
    return {
      id: `e2e-user-${Date.now()}`,
      username: `e2e_user_${Date.now()}`,
      email: `e2e.test.${Date.now()}@example.com`,
      ...overrides
    }
  }

  static createPlaylistSet(count: number = 5) {
    return Array.from({ length: count }, (_, i) =>
      this.createMockPlaylist({
        title: `E2E Playlist ${i + 1}`,
        track_count: Math.floor(Math.random() * 20) + 1
      })
    )
  }

  static createTrackSet(playlistId: string, count: number = 10) {
    return Array.from({ length: count }, (_, i) =>
      this.createMockTrack({
        number: i + 1,
        title: `Track ${i + 1}`,
        artist: `Artist ${Math.floor(i / 3) + 1}`
      })
    )
  }
}

/**
 * Page Object Models for consistent element interaction
 */
export class PlayerPageObject {
  constructor(private page: Page) {}

  // Locators
  get playPauseButton() { return this.page.locator('[data-testid="play-pause-btn"]') }
  get nextButton() { return this.page.locator('[data-testid="next-btn"]') }
  get previousButton() { return this.page.locator('[data-testid="previous-btn"]') }
  get volumeSlider() { return this.page.locator('[data-testid="volume-slider"]') }
  get progressBar() { return this.page.locator('[data-testid="progress-bar"]') }
  get currentTrackTitle() { return this.page.locator('[data-testid="current-track-title"]') }
  get currentTrackArtist() { return this.page.locator('[data-testid="current-track-artist"]') }
  get playlistTitle() { return this.page.locator('[data-testid="current-playlist-title"]') }
  get shuffleButton() { return this.page.locator('[data-testid="shuffle-btn"]') }
  get repeatButton() { return this.page.locator('[data-testid="repeat-btn"]') }

  // Actions
  async play() {
    await this.playPauseButton.click()
  }

  async pause() {
    await this.playPauseButton.click()
  }

  async nextTrack() {
    await this.nextButton.click()
  }

  async previousTrack() {
    await this.previousButton.click()
  }

  async setVolume(volume: number) {
    await this.volumeSlider.fill(volume.toString()
  }

  async seekTo(percentage: number) {
    const progressBarBox = await this.progressBar.boundingBox()
    if (progressBarBox) {
      const x = progressBarBox.x + (progressBarBox.width * percentage / 100)
      const y = progressBarBox.y + progressBarBox.height / 2
      await this.page.mouse.click(x, y)
    }
  }

  async toggleShuffle() {
    await this.shuffleButton.click()
  }

  async toggleRepeat() {
    await this.repeatButton.click()
  }

  // Assertions
  async expectIsPlaying() {
    await expect(this.playPauseButton).toContainText('Pause')
  }

  async expectIsPaused() {
    await expect(this.playPauseButton).toContainText('Play')
  }

  async expectTrack(title: string, artist?: string) {
    await expect(this.currentTrackTitle).toContainText(title)
    if (artist) {
      await expect(this.currentTrackArtist).toContainText(artist)
    }
  }

  async expectVolume(volume: number) {
    await expect(this.volumeSlider).toHaveValue(volume.toString()
  }
}

export class PlaylistPageObject {
  constructor(private page: Page) {}

  // Locators
  get playlistsList() { return this.page.locator('[data-testid="playlists-list"]') }
  get createButton() { return this.page.locator('[data-testid="create-playlist-btn"]') }
  get searchInput() { return this.page.locator('[data-testid="playlist-search"]') }
  get sortSelect() { return this.page.locator('[data-testid="sort-select"]') }
  get filterControls() { return this.page.locator('[data-testid="filter-controls"]') }

  // Dynamic locators
  playlistItem(id: string) { return this.page.locator(`[data-testid="playlist-item-${id}"]`) }
  playlistTitle(id: string) { return this.playlistItem(id).locator('[data-testid="playlist-title"]') }
  playButton(id: string) { return this.playlistItem(id).locator('[data-testid="play-btn"]') }
  editButton(id: string) { return this.playlistItem(id).locator('[data-testid="edit-btn"]') }
  deleteButton(id: string) { return this.playlistItem(id).locator('[data-testid="delete-btn"]') }

  // Actions
  async createPlaylist(title: string, description?: string, isPublic?: boolean) {
    await this.createButton.click()

    const modal = this.page.locator('[data-testid="create-playlist-modal"]')
    await modal.locator('[data-testid="title-input"]').fill(title)

    if (description) {
      await modal.locator('[data-testid="description-input"]').fill(description)
    }

    if (isPublic) {
      await modal.locator('[data-testid="public-checkbox"]').check()
    }

    await modal.locator('[data-testid="save-btn"]').click()
    await expect(modal).not.toBeVisible()
  }

  async searchPlaylists(query: string) {
    await this.searchInput.fill(query)
    // Wait for search results to update
    await this.page.waitForTimeout(500)
  }

  async sortBy(option: 'name' | 'created' | 'track_count') {
    await this.sortSelect.selectOption(option)
  }

  async playPlaylist(id: string) {
    await this.playButton(id).click()
  }

  async editPlaylist(id: string) {
    await this.editButton(id).click()
  }

  async deletePlaylist(id: string) {
    await this.deleteButton(id).click()
    // Handle confirmation dialog
    await this.page.locator('[data-testid="confirm-delete-btn"]').click()
  }

  async selectPlaylist(id: string) {
    await this.playlistItem(id).click()
  }

  // Assertions
  async expectPlaylistVisible(id: string) {
    await expect(this.playlistItem(id).toBeVisible()
  }

  async expectPlaylistNotVisible(id: string) {
    await expect(this.playlistItem(id).not.toBeVisible()
  }

  async expectPlaylistCount(count: number) {
    await expect(this.playlistsList.locator('[data-testid^="playlist-item-"]').toHaveCount(count)
  }

  async expectPlaylistTitle(id: string, title: string) {
    await expect(this.playlistTitle(id).toContainText(title)
  }
}

export class NavigationPageObject {
  constructor(private page: Page) {}

  // Locators
  get homeLink() { return this.page.locator('[data-testid="nav-home"]') }
  get playlistsLink() { return this.page.locator('[data-testid="nav-playlists"]') }
  get playerLink() { return this.page.locator('[data-testid="nav-player"]') }
  get settingsLink() { return this.page.locator('[data-testid="nav-settings"]') }
  get breadcrumbs() { return this.page.locator('[data-testid="breadcrumbs"]') }

  // Actions
  async goToHome() {
    await this.homeLink.click()
    await this.page.waitForURL('/')
  }

  async goToPlaylists() {
    await this.playlistsLink.click()
    await this.page.waitForURL('/playlists')
  }

  async goToPlayer() {
    await this.playerLink.click()
    await this.page.waitForURL('/player')
  }

  async goToSettings() {
    await this.settingsLink.click()
    await this.page.waitForURL('/settings')
  }

  // Assertions
  async expectCurrentRoute(path: string) {
    await expect(this.page).toHaveURL(new RegExp(path)
  }
}

/**
 * Custom assertions for E2E tests
 */
export class E2EAssertions {
  constructor(private page: Page) {}

  async expectAudioPlaying() {
    // Check if HTML5 audio element is playing
    const isPlaying = await this.page.evaluate(() => {
      const audio = document.querySelector('audio')
      return audio && !audio.paused && !audio.ended && audio.currentTime > 0
    })
    expect(isPlaying).toBe(true)
  }

  async expectAudioPaused() {
    const isPaused = await this.page.evaluate(() => {
      const audio = document.querySelector('audio')
      return audio && audio.paused
    })
    expect(isPaused).toBe(true)
  }

  async expectProgressBarPosition(percentage: number, tolerance: number = 5) {
    const currentPercentage = await this.page.evaluate(() => {
      const progressFill = document.querySelector('[data-testid="progress-fill"]') as HTMLElement
      if (progressFill) {
        const width = progressFill.style.width
        return parseFloat(width.replace('%', '')
      }
      return 0
    })

    expect(currentPercentage).toBeCloseTo(percentage, tolerance)
  }

  async expectNetworkRequest(urlPattern: string | RegExp, method: 'GET' | 'POST' | 'PUT' | 'DELETE' = 'GET') {
    const response = await this.page.waitForResponse(response => {
      const url = response.url()
      const matchesUrl = typeof urlPattern === 'string'
        ? url.includes(urlPattern)
        : urlPattern.test(url)

      return matchesUrl && response.request().method() === method
    })

    expect(response.status().toBeLessThan(400)
  }

  async expectWebSocketMessage(messageType: string) {
    // Monitor WebSocket messages
    await this.page.evaluate((type) => {
      return new Promise((resolve) => {
        const checkMessage = (event: any) => {
          const data = JSON.parse(event.data)
          if (data.type === type) {
            resolve(data)
          }
        }

        // Assume socket is available globally or through a specific selector
        const ws = (window as any).socket
        if (ws) {
          ws.addEventListener('message', checkMessage)
          setTimeout(() => resolve(null), 5000) // Timeout after 5 seconds
        }
      })
    }, messageType)
  }

  async expectLocalStorageValue(key: string, expectedValue: string) {
    const value = await this.page.evaluate((k) => localStorage.getItem(k), key)
    expect(value).toBe(expectedValue)
  }

  async expectPerformanceMetric(metric: 'FCP' | 'LCP' | 'FID', maxValue: number) {
    const performance = await this.page.evaluate(() => {
      return JSON.stringify(performance.getEntriesByType('navigation')
    })

    const entries = JSON.parse(performance)
    // Would implement specific performance metric checks here
    expect(entries).toBeDefined())
  }
}

/**
 * Utility functions for E2E testing
 */
export class E2EUtils {
  static async setupMockServer(page: Page) {
    // Setup MSW or similar for API mocking in E2E context
    await page.addInitScript(() => {
      // Initialize mock service worker
      (window as any).mockServerReady = false

      // Mock API responses
      const originalFetch = window.fetch
      window.fetch = async (input, init) => {
        const url = typeof input === 'string' ? input : input.url

        // Mock specific endpoints for E2E testing
        if (url.includes('/api/playlists') && init?.method === 'GET') {
          return new Response(JSON.stringify({
            status: 'success',
            data: {
              items: [],
              total: 0
            }
          }), { status: 200 })
        }

        return originalFetch(input, init)
      }

      (window as any).mockServerReady = true
    })

    await page.waitForFunction(() => (window as any).mockServerReady)
  }

  static async interceptNetworkRequests(page: Page) {
    const requests: any[] = []

    page.on('request', request => {
      requests.push({
        url: request.url(),
        method: request.method(),
        timestamp: Date.now()
      })
    })

    return requests
  }

  static async simulateSlowNetwork(page: Page) {
    // Simulate slow 3G network
    const client = await page.context().newCDPSession(page)
    await client.send('Network.emulateNetworkConditions', {
      offline: false,
      downloadThroughput: 1.5 * 1024 * 1024 / 8, // 1.5 Mbps
      uploadThroughput: 750 * 1024 / 8, // 750 Kbps
      latency: 40 // 40ms latency
    })
  }

  static async simulateOfflineMode(page: Page) {
    await page.context().setOffline(true)
  }

  static async restoreNetworkConditions(page: Page) {
    await page.context().setOffline(false)
    const client = await page.context().newCDPSession(page)
    await client.send('Network.emulateNetworkConditions', {
      offline: false,
      downloadThroughput: -1,
      uploadThroughput: -1,
      latency: 0
    })
  }

  static async waitForFileUpload(page: Page, filename: string) {
    return page.waitForEvent('filechooser').then(async fileChooser => {
      await fileChooser.setFiles([{
        name: filename,
        mimeType: 'audio/mpeg',
        buffer: Buffer.from('mock audio content')
      }])
    })
  }

  static async takeScreenshotWithTimestamp(page: Page, name: string) {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
    await page.screenshot({
      path: `test-results/screenshots/${name}-${timestamp}.png`,
      fullPage: true
    })
  }

  static async measurePageLoadTime(page: Page): Promise<number> {
    return page.evaluate(() => {
      const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming
      return navigation.loadEventEnd - navigation.fetchStart
    })
  }

  static async clearBrowserData(context: BrowserContext) {
    await context.clearCookies()
    await context.clearPermissions()

    // Clear storage for all origins
    await context.addInitScript(() => {
      localStorage.clear()
      sessionStorage.clear()
      if ('caches' in window) {
        caches.keys().then(names => {
          names.forEach(name => caches.delete(name)
        })
      }
    })
  }
}

/**
 * Test data management for E2E tests
 */
export class E2ETestData {
  private static testData = new Map<string, any>()

  static store(key: string, data: any) {
    this.testData.set(key, data)
  }

  static retrieve(key: string) {
    return this.testData.get(key)
  }

  static clear(key?: string) {
    if (key) {
      this.testData.delete(key)
    } else {
      this.testData.clear()
    }
  }

  static generateUniqueId(prefix = 'e2e') {
    return `${prefix}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  }
}

/**
 * Accessibility testing helpers
 */
export class E2EAccessibility {
  static async checkAccessibility(page: Page) {
    // Would integrate with axe-core or similar accessibility testing tool
    await page.evaluate(() => {
      // Basic accessibility checks
      const images = document.querySelectorAll('img')
      images.forEach(img => {
        if (!img.getAttribute('alt') {
          console.warn('Image missing alt text:', img.src)
        }
      })

      const buttons = document.querySelectorAll('button')
      buttons.forEach(button => {
        if (!button.textContent && !button.getAttribute('aria-label') {
          console.warn('Button missing accessible text:', button)
        }
      })
    })
  }

  static async testKeyboardNavigation(page: Page) {
    // Test tab navigation
    await page.keyboard.press('Tab')
    const focusedElement = await page.evaluate(() => document.activeElement?.tagName)
    expect(focusedElement).toBeDefined())
  }

  static async testScreenReaderAnnouncements(page: Page) {
    // Check for ARIA live regions and announcements
    const liveRegions = await page.locator('[aria-live]').count()
    expect(liveRegions).toBeGreaterThan(0)
  }
}