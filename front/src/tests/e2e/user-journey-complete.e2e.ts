/**
 * Complete User Journey E2E Tests
 *
 * Tests comprehensive user workflows from start to finish, simulating
 * real user behavior and validating the complete application experience.
 */

import { test, expect, Page } from '@playwright/test'
import {
  PlayerPageObject,
  PlaylistPageObject,
  NavigationPageObject,
  E2EAssertions,
  E2EUtils,
  E2EMockData,
  E2ETestData
} from './helpers/e2e-helpers'

// Test configuration
test.describe.configure({ mode: 'serial' })

test.describe('Complete User Journey E2E Tests', () => {
  let playerPage: PlayerPageObject
  let playlistPage: PlaylistPageObject
  let navigationPage: NavigationPageObject
  let assertions: E2EAssertions

  test.beforeEach(async ({ page }) => {
    // Initialize page objects
    playerPage = new PlayerPageObject(page)
    playlistPage = new PlaylistPageObject(page)
    navigationPage = new NavigationPageObject(page)
    assertions = new E2EAssertions(page)

    // Setup mock server for consistent test data
    await E2EUtils.setupMockServer(page)

    // Navigate to application
    await page.goto('/')
    await page.waitForSelector('[data-testid="app-root"]')
  })

  test.afterEach(async ({ page }) => {
    // Clean up test data
    await E2EUtils.clearBrowserData(page.context()
  })

  test('Complete Music Listening Journey', async ({ page }) => {
    /**
     * User Journey: Discover → Browse → Play → Control
     * 1. User arrives at home page
     * 2. Browses available playlists
     * 3. Selects a playlist to explore
     * 4. Plays music and controls playback
     * 5. Navigates between tracks
     * 6. Adjusts settings and preferences
     */

    test.step('User arrives at home page', async () => {
      // Verify home page loads correctly
      await expect(page.locator('[data-testid="home-view"]').toBeVisible()
      await expect(page.locator('[data-testid="welcome-message"]').toBeVisible()

      // Check for featured content
      const featuredPlaylists = page.locator('[data-testid="featured-playlists"]')
      if (await featuredPlaylists.count() > 0) {
        await expect(featuredPlaylists).toBeVisible()
      }

      // Verify navigation is available
      await expect(navigationPage.playlistsLink).toBeVisible()
      await expect(navigationPage.playerLink).toBeVisible()
    })

    test.step('User browses available playlists', async () => {
      // Navigate to playlists
      await navigationPage.goToPlaylists()
      await expect(page.locator('[data-testid="playlists-view"]').toBeVisible()

      // Verify playlists are loaded
      await expect(playlistPage.playlistsList).toBeVisible()
      const playlistCount = await playlistPage.playlistsList
        .locator('[data-testid^="playlist-item-"]')
        .count()

      expect(playlistCount).toBeGreaterThan(0)

      // Test search functionality
      await playlistPage.searchPlaylists('E2E Test')
      await page.waitForTimeout(1000) // Wait for search results

      // Verify search results
      const searchResults = await playlistPage.playlistsList
        .locator('[data-testid^="playlist-item-"]')
        .count()

      expect(searchResults).toBeGreaterThanOrEqual(1)
    })

    test.step('User selects and explores a playlist', async () => {
      // Select first playlist
      const firstPlaylist = playlistPage.playlistsList
        .locator('[data-testid^="playlist-item-"]')
        .first()

      const playlistTitle = await firstPlaylist
        .locator('[data-testid="playlist-title"]')
        .textContent()

      await firstPlaylist.click()

      // Verify playlist detail view
      await expect(page.locator('[data-testid="playlist-detail-view"]').toBeVisible()
      await expect(page.locator('[data-testid="playlist-title"]')
        .toContainText(playlistTitle || '')

      // Verify tracks are visible
      const tracksSection = page.locator('[data-testid="tracks-section"]')
      await expect(tracksSection).toBeVisible()

      const trackCount = await tracksSection
        .locator('[data-testid^="track-"]')
        .count()

      expect(trackCount).toBeGreaterThan(0)

      // Store playlist ID for later use
      const playlistId = await page.locator('[data-testid="playlist-detail-view"]')
        .getAttribute('data-playlist-id')

      if (playlistId) {
        E2ETestData.store('selectedPlaylistId', playlistId)
      }
    })

    test.step('User starts playback', async () => {
      // Click play playlist button
      await page.locator('[data-testid="play-playlist-btn"]').click()

      // Wait for player to load
      await page.waitForTimeout(2000)

      // Navigate to player view
      await navigationPage.goToPlayer()
      await expect(page.locator('[data-testid="player-view"]').toBeVisible()

      // Verify playback started
      await playerPage.expectIsPlaying()
      await expect(playerPage.currentTrackTitle).toBeVisible()
      await expect(playerPage.currentTrackArtist).toBeVisible()

      // Verify audio is actually playing
      await assertions.expectAudioPlaying()

      // Take screenshot of playing state
      await E2EUtils.takeScreenshotWithTimestamp(page, 'playback-started')
    })

    test.step('User controls playback', async () => {
      // Test pause/resume
      await playerPage.pause()
      await playerPage.expectIsPaused()
      await assertions.expectAudioPaused()

      await playerPage.play()
      await playerPage.expectIsPlaying()
      await assertions.expectAudioPlaying()

      // Test volume control
      await playerPage.setVolume(75)
      await playerPage.expectVolume(75)

      await playerPage.setVolume(25)
      await playerPage.expectVolume(25)

      // Test seek functionality
      await playerPage.seekTo(50) // Seek to 50%
      await page.waitForTimeout(1000)

      // Verify position changed
      await assertions.expectProgressBarPosition(50, 10) // 10% tolerance
    })

    test.step('User navigates between tracks', async () => {
      const initialTrackTitle = await playerPage.currentTrackTitle.textContent()

      // Go to next track
      await playerPage.nextTrack()
      await page.waitForTimeout(1000)

      const nextTrackTitle = await playerPage.currentTrackTitle.textContent()
      expect(nextTrackTitle).not.toBe(initialTrackTitle)

      // Verify new track is playing
      await playerPage.expectIsPlaying()
      await assertions.expectAudioPlaying()

      // Go to previous track
      await playerPage.previousTrack()
      await page.waitForTimeout(1000)

      const previousTrackTitle = await playerPage.currentTrackTitle.textContent()
      expect(previousTrackTitle).toBe(initialTrackTitle)
    })

    test.step('User explores advanced features', async () => {
      // Test shuffle mode
      await playerPage.toggleShuffle()
      await expect(playerPage.shuffleButton).toHaveClass(/active/)

      // Test repeat mode
      await playerPage.toggleRepeat()
      await expect(playerPage.repeatButton).toHaveClass(/active/)

      // Test playlist navigation from player
      const playlistLink = page.locator('[data-testid="view-playlist-btn"]')
      if (await playlistLink.count() > 0) {
        await playlistLink.click()
        await expect(page.locator('[data-testid="playlist-detail-view"]').toBeVisible()
      }
    })
  })

  test('Playlist Management Journey', async ({ page }) => {
    /**
     * User Journey: Create → Edit → Organize → Share
     * 1. User creates a new playlist
     * 2. Adds tracks to the playlist
     * 3. Organizes and reorders tracks
     * 4. Edits playlist metadata
     * 5. Manages playlist visibility
     */

    const testPlaylistTitle = `E2E Created Playlist ${Date.now()}`

    test.step('User creates a new playlist', async () => {
      await navigationPage.goToPlaylists()

      // Create new playlist
      await playlistPage.createPlaylist(
        testPlaylistTitle,
        'Created during E2E testing',
        false // Private playlist
      )

      // Verify playlist appears in list
      await page.waitForTimeout(1000)
      await playlistPage.expectPlaylistVisible(testPlaylistTitle)
    })

    test.step('User adds tracks to playlist', async () => {
      // Navigate to playlist detail
      await page.locator(`[data-testid*="${testPlaylistTitle}"]`).click()
      await expect(page.locator('[data-testid="playlist-detail-view"]').toBeVisible()

      // Open track addition interface
      const addTracksBtn = page.locator('[data-testid="add-tracks-btn"]')
      if (await addTracksBtn.count() > 0) {
        await addTracksBtn.click()

        // Search for tracks to add
        await page.locator('[data-testid="track-search"]').fill('E2E Test')
        await page.waitForTimeout(1000)

        // Add first search result
        const firstTrackResult = page.locator('[data-testid^="search-track-"]').first()
        if (await firstTrackResult.count() > 0) {
          await firstTrackResult.locator('[data-testid="add-track-btn"]').click()
        }

        // Close add tracks interface
        await page.locator('[data-testid="close-add-tracks"]').click()
      }
    })

    test.step('User organizes track order', async () => {
      const tracksSection = page.locator('[data-testid="tracks-section"]')
      const trackItems = tracksSection.locator('[data-testid^="track-"]')

      if (await trackItems.count() > 1) {
        // Test drag and drop reordering
        const firstTrack = trackItems.first()
        const secondTrack = trackItems.nth(1)

        // Get initial order
        const firstTrackTitle = await firstTrack
          .locator('[data-testid="track-title"]')
          .textContent()

        // Perform drag and drop
        await firstTrack.dragTo(secondTrack)
        await page.waitForTimeout(1000)

        // Verify order changed
        const newFirstTrackTitle = await trackItems.first()
          .locator('[data-testid="track-title"]')
          .textContent()

        expect(newFirstTrackTitle).not.toBe(firstTrackTitle)
      }
    })

    test.step('User edits playlist metadata', async () => {
      // Open edit mode
      await page.locator('[data-testid="edit-playlist-btn"]').click()
      await expect(page.locator('[data-testid="playlist-edit-view"]').toBeVisible()

      // Update playlist information
      const updatedTitle = `${testPlaylistTitle} - Updated`
      await page.locator('[data-testid="title-input"]').fill(updatedTitle)
      await page.locator('[data-testid="description-input"]').fill('Updated description')
      await page.locator('[data-testid="public-checkbox"]').check()

      // Save changes
      await page.locator('[data-testid="save-btn"]').click()

      // Verify changes applied
      await expect(page.locator('[data-testid="playlist-title"]')
        .toContainText(updatedTitle)

      await expect(page.locator('[data-testid="public-badge"]').toBeVisible()
    })

    test.step('User manages playlist sharing', async () => {
      // Test share functionality
      const shareBtn = page.locator('[data-testid="share-playlist-btn"]')
      if (await shareBtn.count() > 0) {
        await shareBtn.click()

        const shareModal = page.locator('[data-testid="share-modal"]')
        await expect(shareModal).toBeVisible()

        // Copy share link
        const shareLink = shareModal.locator('[data-testid="share-link"]')
        await expect(shareLink).toBeVisible()

        // Close share modal
        await shareModal.locator('[data-testid="close-modal"]').click()
      }
    })
  })

  test('Upload and Library Management Journey', async ({ page }) => {
    /**
     * User Journey: Upload → Process → Organize → Play
     * 1. User uploads music files
     * 2. Monitors upload progress
     * 3. Organizes uploaded content
     * 4. Plays newly added music
     */

    test.step('User uploads music files', async () => {
      await navigationPage.goToPlaylists()

      // Create playlist for uploads
      const uploadPlaylistTitle = `Upload Test ${Date.now()}`
      await playlistPage.createPlaylist(uploadPlaylistTitle, 'For testing uploads')

      // Navigate to playlist
      await page.locator(`[data-testid*="${uploadPlaylistTitle}"]`).click()

      // Test file upload
      const uploadBtn = page.locator('[data-testid="upload-btn"]')
      if (await uploadBtn.count() > 0) {
        await uploadBtn.click()

        // Simulate file selection
        const fileInput = page.locator('[data-testid="file-input"]')
        await fileInput.setInputFiles([{
          name: 'test-song.mp3',
          mimeType: 'audio/mpeg',
          buffer: Buffer.from('mock mp3 content')
        }])

        // Monitor upload progress
        const progressSection = page.locator('[data-testid="upload-progress"]')
        if (await progressSection.count() > 0) {
          await expect(progressSection).toBeVisible()

          // Wait for upload completion
          await page.waitForSelector('[data-testid="upload-complete"]', {
            timeout: 10000
          })
        }
      }
    })

    test.step('User organizes uploaded content', async () => {
      // Verify uploaded track appears
      const tracksSection = page.locator('[data-testid="tracks-section"]')
      const uploadedTrack = tracksSection.locator('[data-testid*="test-song"]')

      if (await uploadedTrack.count() > 0) {
        await expect(uploadedTrack).toBeVisible()

        // Edit track metadata
        const editTrackBtn = uploadedTrack.locator('[data-testid="edit-track-btn"]')
        if (await editTrackBtn.count() > 0) {
          await editTrackBtn.click()

          const editModal = page.locator('[data-testid="edit-track-modal"]')
          await editModal.locator('[data-testid="title-input"]').fill('Uploaded Test Song')
          await editModal.locator('[data-testid="artist-input"]').fill('E2E Test Artist')
          await editModal.locator('[data-testid="save-btn"]').click()
        }
      }
    })

    test.step('User plays newly uploaded music', async () => {
      // Play the uploaded track
      const uploadedTrack = page.locator('[data-testid*="test-song"]')
      if (await uploadedTrack.count() > 0) {
        await uploadedTrack.locator('[data-testid="play-track-btn"]').click()

        // Navigate to player and verify
        await navigationPage.goToPlayer()
        await expect(playerPage.currentTrackTitle).toContainText('Uploaded Test Song')
        await playerPage.expectIsPlaying()
      }
    })
  })

  test('Mobile-Responsive User Journey', async ({ page, browserName }) => {
    /**
     * User Journey: Mobile Optimization Validation
     * 1. Test touch interactions
     * 2. Verify responsive design
     * 3. Test mobile-specific features
     */

    // Skip for desktop-only browsers in this test
    test.skip(browserName === 'webkit' && process.platform !== 'darwin', 'Mobile test')

    test.step('User interacts with touch interface', async () => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 })

      await navigationPage.goToPlayer()

      // Test touch interactions
      await page.touchscreen.tap(100, 100) // Tap on progress bar
      await page.waitForTimeout(500)

      // Test swipe gestures for track navigation
      const playerArea = page.locator('[data-testid="player-area"]')
      if (await playerArea.count() > 0) {
        const box = await playerArea.boundingBox()
        if (box) {
          // Swipe left for next track
          await page.touchscreen.tap(box.x + box.width * 0.8, box.y + box.height / 2)
          await page.touchscreen.tap(box.x + box.width * 0.2, box.y + box.height / 2)
        }
      }
    })

    test.step('User navigates mobile interface', async () => {
      // Test mobile navigation
      const mobileMenuBtn = page.locator('[data-testid="mobile-menu-btn"]')
      if (await mobileMenuBtn.count() > 0) {
        await mobileMenuBtn.click()

        const mobileMenu = page.locator('[data-testid="mobile-menu"]')
        await expect(mobileMenu).toBeVisible()

        // Test menu navigation
        await mobileMenu.locator('[data-testid="nav-playlists"]').click()
        await expect(page.locator('[data-testid="playlists-view"]').toBeVisible()
      }
    })
  })

  test('Performance and Loading Journey', async ({ page }) => {
    /**
     * User Journey: Performance Validation
     * 1. Measure page load times
     * 2. Test with large datasets
     * 3. Verify smooth interactions
     */

    test.step('User experiences fast page loads', async () => {
      const loadTime = await E2EUtils.measurePageLoadTime(page)
      expect(loadTime).toBeLessThan(3000) // Should load within 3 seconds

      // Test navigation performance
      const startTime = Date.now()
      await navigationPage.goToPlaylists()
      const navigationTime = Date.now() - startTime
      expect(navigationTime).toBeLessThan(1000) // Navigation should be instant
    })

    test.step('User interacts with large datasets', async () => {
      // Test with many playlists
      await playlistPage.searchPlaylists('') // Show all playlists

      const playlistCount = await playlistPage.playlistsList
        .locator('[data-testid^="playlist-item-"]')
        .count()

      if (playlistCount > 50) {
        // Test scrolling performance with large lists
        const startTime = Date.now()
        await page.evaluate(() => {
          window.scrollTo(0, document.body.scrollHeight)
        })
        const scrollTime = Date.now() - startTime
        expect(scrollTime).toBeLessThan(100) // Smooth scrolling
      }
    })

    test.step('User experiences smooth audio playback', async () => {
      await navigationPage.goToPlayer()

      if (await playerPage.currentTrackTitle.count() > 0) {
        // Test rapid interactions
        for (let i = 0; i < 5; i++) {
          await playerPage.pause()
          await page.waitForTimeout(100)
          await playerPage.play()
          await page.waitForTimeout(100)
        }

        // Verify still playing smoothly
        await playerPage.expectIsPlaying()
      }
    })
  })

  test('Error Handling and Recovery Journey', async ({ page }) => {
    /**
     * User Journey: Error Resilience
     * 1. Test network interruptions
     * 2. Test invalid operations
     * 3. Verify graceful recovery
     */

    test.step('User experiences network interruption', async () => {
      await navigationPage.goToPlaylists()

      // Simulate network interruption
      await E2EUtils.simulateOfflineMode(page)

      // Try to perform action while offline
      const createBtn = playlistPage.createButton
      if (await createBtn.count() > 0) {
        await createBtn.click()

        // Should show offline message
        const offlineMessage = page.locator('[data-testid="offline-message"]')
        if (await offlineMessage.count() > 0) {
          await expect(offlineMessage).toBeVisible()
        }
      }

      // Restore network
      await E2EUtils.restoreNetworkConditions(page)

      // Verify app recovers
      await page.waitForTimeout(2000)
      const connectMessage = page.locator('[data-testid="online-message"]')
      if (await connectMessage.count() > 0) {
        await expect(connectMessage).toBeVisible()
      }
    })

    test.step('User encounters and recovers from errors', async () => {
      // Test invalid playlist access
      await page.goto('/playlists/non-existent-playlist')

      // Should show not found page
      const notFoundPage = page.locator('[data-testid="not-found-view"]')
      if (await notFoundPage.count() > 0) {
        await expect(notFoundPage).toBeVisible()

        // Test recovery navigation
        const homeBtn = notFoundPage.locator('[data-testid="home-btn"]')
        await homeBtn.click()
        await expect(page.locator('[data-testid="home-view"]').toBeVisible()
      }
    })
  })
})

test.describe('Cross-Device User Journey', () => {
  test('Consistent experience across devices', async ({ page, browserName }) => {
    /**
     * Test that user experience remains consistent across different devices
     */

    const deviceConfigs = [
      { width: 1920, height: 1080, name: 'Desktop' },
      { width: 768, height: 1024, name: 'Tablet' },
      { width: 375, height: 667, name: 'Mobile' }
    ]

    for (const device of deviceConfigs) {
      await test.step(`Test ${device.name} experience`, async () => {
        await page.setViewportSize({ width: device.width, height: device.height })

        // Basic navigation should work on all devices
        await page.goto('/')
        await expect(page.locator('[data-testid="app-root"]').toBeVisible()

        const nav = new NavigationPageObject(page)
        await nav.goToPlaylists()
        await expect(page.locator('[data-testid="playlists-view"]').toBeVisible()

        // Player should be accessible
        await nav.goToPlayer()
        await expect(page.locator('[data-testid="player-view"]').toBeVisible()

        // Take screenshot for visual regression testing
        await page.screenshot({
          path: `test-results/screenshots/${device.name.toLowerCase()}-${browserName}.png`,
          fullPage: true
        })
      })
    }
  })
})