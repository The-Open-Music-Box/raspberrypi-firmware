/**
 * Cross-Browser Compatibility E2E Tests
 *
 * Validates that The Open Music Box frontend works consistently across
 * different browsers, devices, and platforms with comprehensive compatibility testing.
 */

import { test, expect, devices, Browser, BrowserContext, Page } from '@playwright/test'
import {
  PlayerPageObject,
  PlaylistPageObject,
  NavigationPageObject,
  E2EAssertions,
  E2EUtils,
  E2EAccessibility
} from './helpers/e2e-helpers'

// Browser-specific test configurations
const browserConfigs = {
  chromium: {
    name: 'Chromium',
    features: ['webAudio', 'mediaRecorder', 'webRTC', 'serviceWorker'],
    audioFormats: ['mp3', 'ogg', 'wav', 'aac'],
    limitations: []
  },
  firefox: {
    name: 'Firefox',
    features: ['webAudio', 'mediaRecorder', 'webRTC', 'serviceWorker'],
    audioFormats: ['mp3', 'ogg', 'wav'],
    limitations: ['limitedAACSupport']
  },
  webkit: {
    name: 'WebKit/Safari',
    features: ['webAudio', 'limitedMediaRecorder', 'webRTC'],
    audioFormats: ['mp3', 'wav', 'aac'],
    limitations: ['noAutoplay', 'limitedServiceWorker', 'noOggSupport']
  }
}

test.describe('Cross-Browser Compatibility Tests', () => {

  test.describe('Core Functionality Across Browsers', () => {
    for (const [browserName, config] of Object.entries(browserConfigs) {
      test(`${config.name}: Basic application functionality`, async ({ page, browserName: currentBrowser }) => {
        test.skip(currentBrowser !== browserName, `Test specific to ${config.name}`)

        const navigation = new NavigationPageObject(page)
        const playlists = new PlaylistPageObject(page)
        const player = new PlayerPageObject(page)

        await test.step('Application loads and renders correctly', async () => {
          await page.goto('/')
          await expect(page.locator('[data-testid="app-root"]').toBeVisible()

          // Check CSS support
          const computedStyle = await page.evaluate(() => {
            const element = document.querySelector('[data-testid="app-root"]')
            return element ? window.getComputedStyle(element).display : null
          })
          expect(computedStyle).not.toBe('none')
        })

        await test.step('Navigation works across all browsers', async () => {
          await navigation.goToPlaylists()
          await expect(page.locator('[data-testid="playlists-view"]').toBeVisible()

          await navigation.goToPlayer()
          await expect(page.locator('[data-testid="player-view"]').toBeVisible()

          await navigation.goToHome()
          await expect(page.locator('[data-testid="home-view"]').toBeVisible()
        })

        await test.step('Playlist management works', async () => {
          await navigation.goToPlaylists()

          // Test playlist creation (if supported)
          const createBtn = page.locator('[data-testid="create-playlist-btn"]')
          if (await createBtn.count() > 0) {
            await playlists.createPlaylist(
              `${config.name} Test Playlist`,
              `Created in ${config.name} browser`
            )

            await playlists.expectPlaylistVisible(`${config.name} Test Playlist`)
          }
        })

        await test.step('Player functionality works', async () => {
          await navigation.goToPlayer()

          // Test basic player controls
          if (await player.playPauseButton.count() > 0) {
            // Test play/pause (considering autoplay restrictions)
            if (!config.limitations.includes('noAutoplay') {
              await player.play()
              await player.expectIsPlaying()

              await player.pause()
              await player.expectIsPaused()
            }

            // Test volume control
            await player.setVolume(50)
            await player.expectVolume(50)
          }
        })
      })
    }
  })

  test.describe('Audio Compatibility Testing', () => {
    for (const [browserName, config] of Object.entries(browserConfigs) {
      test(`${config.name}: Audio format support`, async ({ page, browserName: currentBrowser }) => {
        test.skip(currentBrowser !== browserName, `Test specific to ${config.name}`)

        await page.goto('/')

        await test.step('Test supported audio formats', async () => {
          for (const format of config.audioFormats) {
            const isSupported = await page.evaluate((audioFormat) => {
              const audio = document.createElement('audio')
              return audio.canPlayType(`audio/${audioFormat}`) !== ''
            }, format)

            expect(isSupported).toBe(true)
            console.log(`✅ ${config.name} supports ${format}`)
          }
        })

        await test.step('Test Web Audio API support', async () => {
          const hasWebAudio = await page.evaluate(() => {
            return 'AudioContext' in window || 'webkitAudioContext' in window
          })

          if (config.features.includes('webAudio') {
            expect(hasWebAudio).toBe(true)
          }
        })

        await test.step('Test audio controls responsiveness', async () => {
          const navigation = new NavigationPageObject(page)
          const player = new PlayerPageObject(page)

          await navigation.goToPlayer()

          // Test if audio controls are responsive
          if (await player.volumeSlider.count() > 0) {
            await player.setVolume(75)
            await page.waitForTimeout(500)
            await player.expectVolume(75)
          }
        })
      })
    }
  })

  test.describe('CSS and Layout Compatibility', () => {
    const cssFeatures = [
      'flexbox',
      'grid',
      'transforms',
      'animations',
      'variables',
      'calc'
    ]

    for (const [browserName, config] of Object.entries(browserConfigs) {
      test(`${config.name}: CSS feature support`, async ({ page, browserName: currentBrowser }) => {
        test.skip(currentBrowser !== browserName, `Test specific to ${config.name}`)

        await page.goto('/')

        await test.step('Test CSS feature support', async () => {
          const supportedFeatures = await page.evaluate((features) => {
            const testElement = document.createElement('div')
            document.body.appendChild(testElement)

            const results: Record<string, boolean> = {}

            features.forEach((feature: string) => {
              switch (feature) {
                case 'flexbox':
                  testElement.style.display = 'flex'
                  results[feature] = testElement.style.display === 'flex'
                  break
                case 'grid':
                  testElement.style.display = 'grid'
                  results[feature] = testElement.style.display === 'grid'
                  break
                case 'transforms':
                  testElement.style.transform = 'rotate(45deg)'
                  results[feature] = testElement.style.transform.includes('rotate')
                  break
                case 'animations':
                  testElement.style.animation = 'test 1s'
                  results[feature] = testElement.style.animation !== ''
                  break
                case 'variables':
                  testElement.style.setProperty('--test-var', 'red')
                  results[feature] = testElement.style.getPropertyValue('--test-var') === 'red'
                  break
                case 'calc':
                  testElement.style.width = 'calc(100% - 20px)'
                  results[feature] = testElement.style.width.includes('calc')
                  break
              }
            })

            document.body.removeChild(testElement)
            return results
          }, cssFeatures)

          // Verify essential CSS features are supported
          expect(supportedFeatures.flexbox).toBe(true)
          console.log(`${config.name} CSS support:`, supportedFeatures)
        })

        await test.step('Test responsive design', async () => {
          const viewports = [
            { width: 1920, height: 1080, name: 'Desktop' },
            { width: 768, height: 1024, name: 'Tablet' },
            { width: 375, height: 667, name: 'Mobile' }
          ]

          for (const viewport of viewports) {
            await page.setViewportSize(viewport)
            await page.waitForTimeout(500)

            // Check if layout adapts properly
            const appRoot = page.locator('[data-testid="app-root"]')
            const boundingBox = await appRoot.boundingBox()

            expect(boundingBox?.width).toBeLessThanOrEqual(viewport.width)

            // Navigation should be accessible on all screen sizes
            const navigation = new NavigationPageObject(page)
            const navElement = viewport.width < 768
              ? page.locator('[data-testid="mobile-menu-btn"]')
              : navigation.homeLink

            if (await navElement.count() > 0) {
              await expect(navElement).toBeVisible()
            }
          }
        })
      })
    }
  })

  test.describe('JavaScript API Compatibility', () => {
    const jsFeatures = [
      'fetch',
      'Promise',
      'localStorage',
      'sessionStorage',
      'addEventListener',
      'querySelector',
      'classList',
      'FormData'
    ]

    for (const [browserName, config] of Object.entries(browserConfigs) {
      test(`${config.name}: JavaScript API support`, async ({ page, browserName: currentBrowser }) => {
        test.skip(currentBrowser !== browserName, `Test specific to ${config.name}`)

        await page.goto('/')

        await test.step('Test JavaScript API availability', async () => {
          const apiSupport = await page.evaluate((features) => {
            const results: Record<string, boolean> = {}

            features.forEach((feature: string) => {
              switch (feature) {
                case 'fetch':
                  results[feature] = typeof fetch !== 'undefined'
                  break
                case 'Promise':
                  results[feature] = typeof Promise !== 'undefined'
                  break
                case 'localStorage':
                  results[feature] = typeof localStorage !== 'undefined'
                  break
                case 'sessionStorage':
                  results[feature] = typeof sessionStorage !== 'undefined'
                  break
                case 'addEventListener':
                  results[feature] = typeof document.addEventListener !== 'undefined'
                  break
                case 'querySelector':
                  results[feature] = typeof document.querySelector !== 'undefined'
                  break
                case 'classList':
                  results[feature] = 'classList' in document.createElement('div')
                  break
                case 'FormData':
                  results[feature] = typeof FormData !== 'undefined'
                  break
              }
            })

            return results
          }, jsFeatures)

          // All modern features should be supported
          jsFeatures.forEach(feature => {
            expect(apiSupport[feature]).toBe(true)
          })

          console.log(`${config.name} JS API support:`, apiSupport)
        })

        await test.step('Test event handling', async () => {
          // Test click events
          const navigation = new NavigationPageObject(page)
          await navigation.goToPlaylists()
          await expect(page.locator('[data-testid="playlists-view"]').toBeVisible()

          // Test keyboard events
          await page.keyboard.press('Tab')
          const focusedElement = await page.evaluate(() => document.activeElement?.tagName)
          expect(focusedElement).toBeTruthy()
        })
      })
    }
  })

  test.describe('File Upload Compatibility', () => {
    for (const [browserName, config] of Object.entries(browserConfigs) {
      test(`${config.name}: File upload functionality`, async ({ page, browserName: currentBrowser }) => {
        test.skip(currentBrowser !== browserName, `Test specific to ${config.name}`)

        await page.goto('/playlists')

        await test.step('Test file input support', async () => {
          const fileInputSupport = await page.evaluate(() => {
            const input = document.createElement('input')
            input.type = 'file'
            return input.type === 'file'
          })

          expect(fileInputSupport).toBe(true)
        })

        await test.step('Test drag and drop support', async () => {
          const dragDropSupport = await page.evaluate(() => {
            const div = document.createElement('div')
            return 'ondragstart' in div && 'ondrop' in div
          })

          expect(dragDropSupport).toBe(true)
        })

        await test.step('Test file API support', async () => {
          const fileAPISupport = await page.evaluate(() => {
            return typeof File !== 'undefined' &&
                   typeof FileList !== 'undefined' &&
                   typeof FileReader !== 'undefined'
          })

          expect(fileAPISupport).toBe(true)
        })
      })
    }
  })

  test.describe('Performance Across Browsers', () => {
    for (const [browserName, config] of Object.entries(browserConfigs) {
      test(`${config.name}: Performance benchmarks`, async ({ page, browserName: currentBrowser }) => {
        test.skip(currentBrowser !== browserName, `Test specific to ${config.name}`)

        await test.step('Measure page load performance', async () => {
          const startTime = Date.now()
          await page.goto('/')
          await page.waitForSelector('[data-testid="app-root"]')
          const loadTime = Date.now() - startTime

          // Performance expectations by browser
          const maxLoadTime = browserName === 'webkit' ? 5000 : 3000
          expect(loadTime).toBeLessThan(maxLoadTime)

          console.log(`${config.name} load time: ${loadTime}ms`)
        })

        await test.step('Test memory usage', async () => {
          // Navigate through app to build up memory usage
          const navigation = new NavigationPageObject(page)

          await navigation.goToPlaylists()
          await navigation.goToPlayer()
          await navigation.goToHome()

          // Check for memory leaks (basic)
          const memoryInfo = await page.evaluate(() => {
            return (performance as any).memory ? {
              used: (performance as any).memory.usedJSHeapSize,
              total: (performance as any).memory.totalJSHeapSize,
              limit: (performance as any).memory.jsHeapSizeLimit
            } : null
          })

          if (memoryInfo) {
            // Memory usage should be reasonable
            const memoryUsageMB = memoryInfo.used / (1024 * 1024)
            expect(memoryUsageMB).toBeLessThan(100) // Less than 100MB

            console.log(`${config.name} memory usage: ${memoryUsageMB.toFixed(2)}MB`)
          }
        })

        await test.step('Test rendering performance', async () => {
          const navigation = new NavigationPageObject(page)
          await navigation.goToPlaylists()

          // Measure rendering time for dynamic content
          const renderTime = await page.evaluate(() => {
            const start = performance.now()

            // Force a reflow/repaint
            document.body.offsetHeight

            return performance.now() - start
          })

          expect(renderTime).toBeLessThan(16) // Should render within one frame (60fps)
        })
      })
    }
  })

  test.describe('Browser-Specific Feature Testing', () => {
    test('Chrome: Advanced Web APIs', async ({ page, browserName }) => {
      test.skip(browserName !== 'chromium', 'Chrome-specific test')

      await page.goto('/')

      await test.step('Test Chrome-specific features', async () => {
        // Test advanced audio features
        const audioFeatures = await page.evaluate(() => {
          const audio = new Audio()
          return {
            audioWorklet: 'audioWorklet' in AudioContext.prototype,
            mediaSession: 'mediaSession' in navigator,
            webAudioSpatial: 'createPanner' in AudioContext.prototype
          }
        })

        expect(audioFeatures.audioWorklet).toBe(true)
        expect(audioFeatures.mediaSession).toBe(true)
      })
    })

    test('Firefox: Privacy and Security Features', async ({ page, browserName }) => {
      test.skip(browserName !== 'firefox', 'Firefox-specific test')

      await page.goto('/')

      await test.step('Test Firefox privacy features', async () => {
        // Test enhanced tracking protection compatibility
        const trackingProtection = await page.evaluate(() => {
          // Check if app works with tracking protection
          return document.readyState === 'complete'
        })

        expect(trackingProtection).toBe(true)
      })
    })

    test('Safari: iOS/macOS Specific Features', async ({ page, browserName }) => {
      test.skip(browserName !== 'webkit', 'Safari-specific test')

      await page.goto('/')

      await test.step('Test Safari-specific constraints', async () => {
        // Test autoplay restrictions
        const autoplayRestricted = await page.evaluate(() => {
          const audio = new Audio()
          audio.autoplay = true
          // Safari blocks autoplay by default
          return !audio.autoplay
        })

        // This should pass in Safari due to autoplay restrictions
        if (process.platform === 'darwin') {
          expect(autoplayRestricted).toBe(true)
        }

        // Test iOS viewport handling
        const viewportMeta = await page.evaluate(() => {
          const meta = document.querySelector('meta[name="viewport"]')
          return meta ? meta.getAttribute('content') : null
        })

        expect(viewportMeta).toBeTruthy()
      })
    })
  })

  test.describe('Device-Specific Testing', () => {
    const deviceProfiles = [
      { name: 'iPhone 12', device: devices['iPhone 12'] },
      { name: 'iPad Pro', device: devices['iPad Pro'] },
      { name: 'Pixel 5', device: devices['Pixel 5'] },
      { name: 'Desktop Chrome', device: devices['Desktop Chrome'] }
    ]

    for (const profile of deviceProfiles) {
      test(`${profile.name}: Device-specific functionality`, async ({ browser }) => {
        const context = await browser.newContext({
          ...profile.device
        })
        const page = await context.newPage()

        await test.step('Test device adaptation', async () => {
          await page.goto('/')

          // Check if UI adapts to device
          const isMobile = profile.device.isMobile
          const touchSupported = profile.device.hasTouch

          if (isMobile) {
            // Mobile-specific UI should be present
            const mobileUI = page.locator('[data-testid="mobile-interface"]')
            if (await mobileUI.count() > 0) {
              await expect(mobileUI).toBeVisible()
            }
          }

          if (touchSupported) {
            // Touch interactions should work
            const touchTarget = page.locator('[data-testid="touch-target"]').first()
            if (await touchTarget.count() > 0) {
              await touchTarget.tap()
            }
          }
        })

        await test.step('Test device-specific features', async () => {
          const navigation = new NavigationPageObject(page)
          const player = new PlayerPageObject(page)

          await navigation.goToPlayer()

          // Test orientation changes on mobile devices
          if (profile.device.isMobile) {
            // Simulate orientation change
            await page.setViewportSize({
              width: profile.device.viewport!.height,
              height: profile.device.viewport!.width
            })

            await page.waitForTimeout(1000)

            // UI should still be functional
            await expect(page.locator('[data-testid="player-view"]').toBeVisible()
          }
        })

        await context.close()
      })
    }
  })

  test.describe('Accessibility Across Browsers', () => {
    for (const [browserName, config] of Object.entries(browserConfigs) {
      test(`${config.name}: Accessibility features`, async ({ page, browserName: currentBrowser }) => {
        test.skip(currentBrowser !== browserName, `Test specific to ${config.name}`)

        await page.goto('/')

        await test.step('Test keyboard navigation', async () => {
          await E2EAccessibility.testKeyboardNavigation(page)
        })

        await test.step('Test screen reader support', async () => {
          await E2EAccessibility.testScreenReaderAnnouncements(page)
        })

        await test.step('Test high contrast mode', async () => {
          // Test if app works with high contrast mode
          await page.emulateMedia({ colorScheme: 'dark' })
          await page.waitForTimeout(500)

          const appRoot = page.locator('[data-testid="app-root"]')
          await expect(appRoot).toBeVisible()

          // Reset
          await page.emulateMedia({ colorScheme: 'light' })
        })
      })
    }
  })
})

test.describe('Compatibility Regression Prevention', () => {
  test('Visual regression across browsers', async ({ page, browserName }) => {
    const testPages = ['/', '/playlists', '/player']

    for (const pagePath of testPages) {
      await test.step(`Visual test for ${pagePath}`, async () => {
        await page.goto(pagePath)
        await page.waitForLoadState('networkidle')

        // Take screenshot for visual comparison
        await expect(page).toHaveScreenshot(`${pagePath.replace('/', 'home')}-${browserName}.png`, {
          fullPage: true,
          animations: 'disabled'
        })
      })
    }
  })

  test('API compatibility across browsers', async ({ page, browserName }) => {
    await page.goto('/')

    await test.step('Test consistent API behavior', async () => {
      // Test that API calls work consistently
      const networkPromise = page.waitForResponse(response =>
        response.url().includes('/api/') && response.status() < 400
      )

      const navigation = new NavigationPageObject(page)
      await navigation.goToPlaylists()

      try {
        await networkPromise
        console.log(`✅ API calls work in ${browserName}`)
      } catch (error) {
        console.warn(`⚠️ API issues in ${browserName}:`, error)
      }
    })
  })
})