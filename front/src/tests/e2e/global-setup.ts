/**
 * Global Setup for E2E Tests
 *
 * Configures the testing environment before running E2E tests.
 * Handles backend setup, database seeding, and environment preparation.
 */

import { chromium, FullConfig } from '@playwright/test'
import path from 'path'
import fs from 'fs'

async function globalSetup(config: FullConfig) {
  console.log('🚀 Starting E2E Global Setup...')

  // Create test results directories
  const testResultsDir = 'test-results'
  const screenshotsDir = path.join(testResultsDir, 'screenshots')
  const videosDir = path.join(testResultsDir, 'videos')
  const tracesDir = path.join(testResultsDir, 'traces')

  [testResultsDir, screenshotsDir, videosDir, tracesDir].forEach(dir => {
    if (!fs.existsSync(dir) {
      fs.mkdirSync(dir, { recursive: true })
      console.log(`📁 Created directory: ${dir}`)
    }
  })

  // Environment setup
  const baseURL = config.projects[0].use?.baseURL || 'http://localhost:5173'
  const apiURL = process.env.E2E_API_URL || 'http://localhost:8000'

  console.log(`🌐 Base URL: ${baseURL}`)
  console.log(`🔌 API URL: ${apiURL}`)

  // Start browser for setup operations
  const browser = await chromium.launch()
  const context = await browser.newContext()
  const page = await context.newPage()

  try {
    // Wait for development server to be ready
    console.log('⏳ Waiting for frontend server...')
    await waitForServer(baseURL, 120000) // 2 minutes timeout

    // Wait for backend API to be ready
    console.log('⏳ Waiting for backend API...')
    await waitForServer(`${apiURL}/health`, 60000) // 1 minute timeout

    // Setup test database with seed data
    console.log('🌱 Setting up test data...')
    await setupTestData(apiURL)

    // Verify application is accessible
    console.log('🔍 Verifying application accessibility...')
    await page.goto(baseURL)
    await page.waitForSelector('[data-testid="app-root"]', { timeout: 30000 })
    console.log('✅ Application is accessible')

    // Setup authentication state for tests that need it
    console.log('🔐 Setting up authentication state...')
    await setupAuthState(page, baseURL)

    // Warm up the application
    console.log('🔥 Warming up application...')
    await warmupApplication(page, baseURL)

    console.log('✅ Global setup completed successfully')

  } catch (error) {
    console.error('❌ Global setup failed:', error)
    throw error
  } finally {
    await browser.close()
  }
}

/**
 * Wait for a server to be ready
 */
async function waitForServer(url: string, timeout: number = 60000): Promise<void> {
  const start = Date.now()

  while (Date.now() - start < timeout) {
    try {
      const response = await fetch(url)
      if (response.status < 500) {
        console.log(`✅ Server ready: ${url}`)
        return
      }
    } catch (error) {
      // Server not ready yet, continue waiting
    }

    await new Promise(resolve => setTimeout(resolve, 1000)
  }

  throw new Error(`Server not ready after ${timeout}ms: ${url}`)
}

/**
 * Setup test data in the backend
 */
async function setupTestData(apiURL: string): Promise<void> {
  try {
    // Reset test database
    const resetResponse = await fetch(`${apiURL}/test/reset`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })

    if (!resetResponse.ok) {
      console.warn('⚠️ Database reset failed, continuing...')
    } else {
      console.log('🗑️ Test database reset')
    }

    // Create test user
    const testUser = {
      username: 'e2e_test_user',
      email: 'e2e@test.com',
      password: 'testpass123'
    }

    const userResponse = await fetch(`${apiURL}/test/users`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(testUser)
    })

    if (userResponse.ok) {
      console.log('👤 Test user created')
    }

    // Create test playlists
    const testPlaylists = [
      {
        title: 'E2E Test Playlist 1',
        description: 'First test playlist for E2E testing',
        is_public: true
      },
      {
        title: 'E2E Test Playlist 2',
        description: 'Second test playlist for E2E testing',
        is_public: false
      },
      {
        title: 'Large E2E Playlist',
        description: 'Large playlist for performance testing',
        is_public: true,
        track_count: 100
      }
    ]

    for (const playlist of testPlaylists) {
      const playlistResponse = await fetch(`${apiURL}/test/playlists`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(playlist)
      })

      if (playlistResponse.ok) {
        const createdPlaylist = await playlistResponse.json()
        console.log(`🎵 Created test playlist: ${playlist.title}`)

        // Add tracks to playlist
        if (playlist.track_count) {
          await createTestTracks(apiURL, createdPlaylist.id, playlist.track_count)
        } else {
          await createTestTracks(apiURL, createdPlaylist.id, 5) // Default 5 tracks
        }
      }
    }

    console.log('✅ Test data setup completed')

  } catch (error) {
    console.error('❌ Test data setup failed:', error)
    // Don't throw error to allow tests to continue with minimal data
  }
}

/**
 * Create test tracks for a playlist
 */
async function createTestTracks(apiURL: string, playlistId: string, count: number): Promise<void> {
  const tracks = Array.from({ length: count }, (_, i) => ({
    number: i + 1,
    title: `E2E Test Track ${i + 1}`,
    artist: `E2E Test Artist ${Math.floor(i / 3) + 1}`,
    album: `E2E Test Album ${Math.floor(i / 5) + 1}`,
    duration_ms: 180000 + (Math.random() * 120000), // 3-5 minutes
    file_path: `/test/tracks/track_${i + 1}.mp3`
  })

  for (const track of tracks) {
    try {
      const trackResponse = await fetch(`${apiURL}/test/playlists/${playlistId}/tracks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(track)
      })

      if (!trackResponse.ok) {
        console.warn(`⚠️ Failed to create track: ${track.title}`)
      }
    } catch (error) {
      console.warn(`⚠️ Error creating track: ${track.title}`, error)
    }
  }

  console.log(`🎵 Created ${count} test tracks for playlist ${playlistId}`)
}

/**
 * Setup authentication state
 */
async function setupAuthState(page: any, baseURL: string): Promise<void> {
  try {
    // Navigate to login page
    await page.goto(`${baseURL}/login`)

    // Check if login form exists
    const loginForm = await page.locator('[data-testid="login-form"]').count()

    if (loginForm > 0) {
      // Perform login
      await page.fill('[data-testid="username-input"]', 'e2e_test_user')
      await page.fill('[data-testid="password-input"]', 'testpass123')
      await page.click('[data-testid="login-button"]')

      // Wait for successful login
      await page.waitForURL(`${baseURL}/`, { timeout: 10000 })

      // Save auth state
      const authState = await page.context().storageState()

      // Save to file for other tests to use
      fs.writeFileSync('test-results/auth-state.json', JSON.stringify(authState, null, 2)
      console.log('🔐 Authentication state saved')
    } else {
      console.log('ℹ️ No login required for this application')
    }
  } catch (error) {
    console.warn('⚠️ Authentication setup failed:', error)
    // Continue without auth state
  }
}

/**
 * Warm up the application by visiting key pages
 */
async function warmupApplication(page: any, baseURL: string): Promise<void> {
  const pagesToWarmup = [
    '/',
    '/playlists',
    '/player',
    '/settings'
  ]

  for (const path of pagesToWarmup) {
    try {
      await page.goto(`${baseURL}${path}`)
      await page.waitForLoadState('networkidle', { timeout: 10000 })
      console.log(`🔥 Warmed up: ${path}`)
    } catch (error) {
      console.warn(`⚠️ Failed to warm up ${path}:`, error)
    }
  }
}

export default globalSetup