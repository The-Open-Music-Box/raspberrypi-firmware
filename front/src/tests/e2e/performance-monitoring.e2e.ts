/**
 * Performance Monitoring E2E Tests
 *
 * Tests application performance metrics, memory usage, and resource loading.
 * Monitors critical performance indicators and identifies potential bottlenecks.
 */

import { test, expect, Page } from '@playwright/test'
import type { CDPSession } from '@playwright/test'

interface PerformanceMetrics {
  fcp: number // First Contentful Paint
  lcp: number // Largest Contentful Paint
  cls: number // Cumulative Layout Shift
  fid: number // First Input Delay
  ttfb: number // Time to First Byte
  domContentLoaded: number
  load: number
  memoryUsage?: {
    usedJSHeapSize: number
    totalJSHeapSize: number
    jsHeapSizeLimit: number
  }
}

interface NetworkMetrics {
  totalRequests: number
  totalBytes: number
  slowRequests: Array<{
    url: string
    duration: number
    size: number
  }>
  failedRequests: string[]
}

test.describe('Performance Monitoring', () => {
  let cdpSession: CDPSession
  let performanceMetrics: PerformanceMetrics
  let networkMetrics: NetworkMetrics

  test.beforeEach(async ({ page }) => {
    // Enable CDP for performance monitoring
    cdpSession = await page.context().newCDPSession(page)
    await cdpSession.send('Performance.enable')
    await cdpSession.send('Runtime.enable')

    // Initialize metrics
    performanceMetrics = {} as PerformanceMetrics
    networkMetrics = {
      totalRequests: 0,
      totalBytes: 0,
      slowRequests: [],
      failedRequests: []
    }

    // Monitor network requests
    page.on('request', request => {
      networkMetrics.totalRequests++
    })

    page.on('response', response => {
      const request = response.request()
      const url = request.url()

      if (!response.ok() {
        networkMetrics.failedRequests.push(url)
      }

      // Track response size and timing
      response.body().then(body => {
        const size = body.length
        networkMetrics.totalBytes += size

        const timing = response.timing()
        const duration = timing.responseEnd - timing.requestStart

        // Flag slow requests (>2s)
        if (duration > 2000) {
          networkMetrics.slowRequests.push({
            url,
            duration,
            size
          })
        }
      }).catch(() => {
        // Ignore body reading errors for non-text responses
      })
    })
  })

  test('should load homepage within performance budget', async ({ page }) => {
    const startTime = Date.now()

    // Navigate to homepage
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    const loadTime = Date.now() - startTime

    // Collect Core Web Vitals
    const webVitals = await page.evaluate(() => {
      return new Promise<any>((resolve) => {
        const observer = new PerformanceObserver((list) => {
          const entries = list.getEntries()
          const vitals: any = {}

          entries.forEach((entry: any) => {
            if (entry.entryType === 'navigation') {
              vitals.domContentLoaded = entry.domContentLoadedEventEnd - entry.domContentLoadedEventStart
              vitals.load = entry.loadEventEnd - entry.loadEventStart
              vitals.ttfb = entry.responseStart - entry.requestStart
            }
            if (entry.entryType === 'paint') {
              if (entry.name === 'first-contentful-paint') {
                vitals.fcp = entry.startTime
              }
            }
            if (entry.entryType === 'largest-contentful-paint') {
              vitals.lcp = entry.startTime
            }
            if (entry.entryType === 'layout-shift' && !entry.hadRecentInput) {
              vitals.cls = (vitals.cls || 0) + entry.value
            }
          })

          // Check if we have enough data
          setTimeout(() => resolve(vitals), 2000)
        })

        observer.observe({ entryTypes: ['navigation', 'paint', 'largest-contentful-paint', 'layout-shift'] })
      })
    })

    // Get memory usage
    const memoryUsage = await page.evaluate(() => {
      return (performance as any).memory ? {
        usedJSHeapSize: (performance as any).memory.usedJSHeapSize,
        totalJSHeapSize: (performance as any).memory.totalJSHeapSize,
        jsHeapSizeLimit: (performance as any).memory.jsHeapSizeLimit
      } : undefined
    })

    performanceMetrics = { ...webVitals, memoryUsage }

    // Performance Budget Assertions
    expect(loadTime).toBeLessThan(5000) // Total load time < 5s
    expect(webVitals.fcp).toBeLessThan(2000) // FCP < 2s
    expect(webVitals.lcp).toBeLessThan(2500) // LCP < 2.5s
    expect(webVitals.cls).toBeLessThan(0.1) // CLS < 0.1
    expect(webVitals.ttfb).toBeLessThan(800) // TTFB < 800ms

    // Memory usage check (if available)
    if (memoryUsage) {
      expect(memoryUsage.usedJSHeapSize).toBeLessThan(50 * 1024 * 1024) // < 50MB
    }

    // Network performance
    expect(networkMetrics.totalRequests).toBeLessThan(50) // < 50 requests
    expect(networkMetrics.totalBytes).toBeLessThan(5 * 1024 * 1024) // < 5MB
    expect(networkMetrics.failedRequests).toHaveLength(0)
    expect(networkMetrics.slowRequests).toHaveLength(0)

    console.log('Performance Metrics:', {
      loadTime,
      webVitals,
      memoryUsage,
      network: networkMetrics
    })
  })

  test('should handle large playlist loading efficiently', async ({ page }) => {
    await page.goto('/')

    // Wait for app to be ready
    await page.waitForSelector('[data-testid="app-root"]')

    // Create a large playlist for testing
    await page.evaluate(async () => {
      const response = await fetch('/api/test/playlists', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: 'Performance Test Playlist',
          description: 'Large playlist for performance testing',
          track_count: 1000
        })
      })
      return response.json()
    })

    const startTime = Date.now()

    // Navigate to playlists page
    await page.goto('/playlists')
    await page.waitForSelector('[data-testid="playlist-list"]')

    // Click on the large playlist
    await page.click('[data-testid="playlist-item"]:has-text("Performance Test Playlist")')
    await page.waitForSelector('[data-testid="track-list"]')

    const loadTime = Date.now() - startTime

    // Check virtual scrolling performance
    const trackItems = page.locator('[data-testid="track-item"]')
    const visibleTracksCount = await trackItems.count()

    // Should use virtual scrolling - not all 1000 tracks should be in DOM
    expect(visibleTracksCount).toBeLessThan(100)
    expect(loadTime).toBeLessThan(3000) // Should load in < 3s

    // Test scrolling performance
    const scrollStartTime = Date.now()

    // Scroll to bottom
    await page.keyboard.press('End')
    await page.waitForTimeout(500)

    // Scroll to top
    await page.keyboard.press('Home')
    await page.waitForTimeout(500)

    const scrollTime = Date.now() - scrollStartTime
    expect(scrollTime).toBeLessThan(2000) // Scrolling should be smooth
  })

  test('should maintain performance during audio playback', async ({ page }) => {
    await page.goto('/')
    await page.waitForSelector('[data-testid="app-root"]')

    // Get initial memory baseline
    const initialMemory = await page.evaluate(() => {
      return (performance as any).memory ? (performance as any).memory.usedJSHeapSize : 0
    })

    // Start audio playback
    await page.click('[data-testid="playlist-item"]')
    await page.waitForSelector('[data-testid="audio-player"]')
    await page.click('[data-testid="play-pause-btn"]')

    // Wait for playback to start
    await page.waitForSelector('[data-testid="play-pause-btn"]:has-text("Pause")')

    // Monitor performance during playback
    const performanceDuringPlayback = []

    for (let i = 0; i < 5; i++) {
      await page.waitForTimeout(2000) // Wait 2 seconds

      const metrics = await page.evaluate(() => {
        const memory = (performance as any).memory
        return {
          timestamp: Date.now(),
          memoryUsage: memory ? memory.usedJSHeapSize : 0,
          fps: 0 // We'll calculate this separately
        }
      })

      performanceDuringPlayback.push(metrics)
    }

    // Check for memory leaks
    const finalMemory = performanceDuringPlayback[performanceDuringPlayback.length - 1].memoryUsage
    const memoryGrowth = finalMemory - initialMemory

    // Memory growth should be reasonable during playback
    expect(memoryGrowth).toBeLessThan(10 * 1024 * 1024) // < 10MB growth

    // No significant memory spikes
    const memoryValues = performanceDuringPlayback.map(m => m.memoryUsage)
    const maxMemory = Math.max(...memoryValues)
    const minMemory = Math.min(...memoryValues)
    const memoryVariation = maxMemory - minMemory

    expect(memoryVariation).toBeLessThan(5 * 1024 * 1024) // < 5MB variation
  })

  test('should handle file upload performance', async ({ page }) => {
    await page.goto('/upload')
    await page.waitForSelector('[data-testid="upload-zone"]')

    // Create a test file (simulate large file)
    const testFile = await page.evaluateHandle(() => {
      const buffer = new ArrayBuffer(10 * 1024 * 1024) // 10MB
      return new File([buffer], 'test-audio.mp3', { type: 'audio/mpeg' })
    })

    const startTime = Date.now()

    // Start file upload
    const fileInput = page.locator('input[type="file"]')
    await fileInput.setInputFiles([testFile as any])

    // Wait for upload progress to appear
    await page.waitForSelector('[data-testid="upload-progress"]')

    // Monitor upload progress
    let uploadCompleted = false
    const progressValues = []

    while (!uploadCompleted) {
      const progressText = await page.locator('[data-testid="upload-progress"]').textContent()

      if (progressText?.includes('100%') || progressText?.includes('Complete') {
        uploadCompleted = true
      } else {
        const match = progressText?.match(/(\d+)%/)
        if (match) {
          progressValues.push(parseInt(match[1])
        }
      }

      await page.waitForTimeout(100)

      // Timeout after 30 seconds
      if (Date.now() - startTime > 30000) {
        break
      }
    }

    const uploadTime = Date.now() - startTime

    // Performance expectations
    expect(uploadTime).toBeLessThan(30000) // Upload should complete in < 30s
    expect(progressValues.length).toBeGreaterThan(0) // Progress should be reported

    // Progress should be monotonically increasing
    for (let i = 1; i < progressValues.length; i++) {
      expect(progressValues[i]).toBeGreaterThanOrEqual(progressValues[i - 1])
    }
  })

  test('should maintain UI responsiveness during heavy operations', async ({ page }) => {
    await page.goto('/')
    await page.waitForSelector('[data-testid="app-root"]')

    // Simulate heavy operation (e.g., loading multiple playlists)
    const responseTimes = []

    for (let i = 0; i < 10; i++) {
      const startTime = Date.now()

      // Trigger UI interaction
      await page.click('[data-testid="nav-playlists"]')
      await page.waitForSelector('[data-testid="playlist-list"]')

      const responseTime = Date.now() - startTime
      responseTimes.push(responseTime)

      // Navigate back
      await page.click('[data-testid="nav-home"]')
      await page.waitForSelector('[data-testid="home-page"]')
    }

    // UI should remain responsive
    const averageResponseTime = responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length
    const maxResponseTime = Math.max(...responseTimes)

    expect(averageResponseTime).toBeLessThan(500) // Average < 500ms
    expect(maxResponseTime).toBeLessThan(1000) // Max < 1s

    // No response time should be more than 2x the average
    responseTimes.forEach(time => {
      expect(time).toBeLessThan(averageResponseTime * 2)
    })
  })

  test('should handle concurrent user interactions efficiently', async ({ page }) => {
    await page.goto('/')
    await page.waitForSelector('[data-testid="app-root"]')

    // Start multiple concurrent operations
    const operations = [
      // Load playlist
      page.click('[data-testid="nav-playlists"]'),

      // Search for tracks
      page.fill('[data-testid="search-input"]', 'test'),

      // Toggle player controls
      page.click('[data-testid="play-pause-btn"]'),

      // Navigate to settings
      page.click('[data-testid="nav-settings"]')
    ]

    const startTime = Date.now()

    // Execute all operations concurrently
    await Promise.all(operations)

    const concurrentOperationTime = Date.now() - startTime

    // Should handle concurrent operations efficiently
    expect(concurrentOperationTime).toBeLessThan(3000)

    // Check that the app is still responsive
    await page.click('[data-testid="nav-home"]')
    await page.waitForSelector('[data-testid="home-page"]')

    // No JavaScript errors should have occurred
    const jsErrors = await page.evaluate(() => {
      return (window as any).__jsErrors || []
    })

    expect(jsErrors).toHaveLength(0)
  })

  test.afterEach(async ({ page }) => {
    // Generate performance report
    console.log('\n=== Performance Report ===')
    console.log('Metrics:', performanceMetrics)
    console.log('Network:', networkMetrics)

    // Cleanup
    if (cdpSession) {
      await cdpSession.detach()
    }
  })
})

// Performance test configuration
test.describe.configure({
  mode: 'serial', // Run performance tests in sequence to avoid interference
  timeout: 60000 // Extended timeout for performance tests
})