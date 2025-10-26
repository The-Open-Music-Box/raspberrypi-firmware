/**
 * Playwright End-to-End Testing Configuration
 *
 * Comprehensive E2E testing setup for The Open Music Box frontend application.
 * Supports multiple browsers, devices, and testing scenarios.
 */

import { defineConfig, devices } from '@playwright/test'

/**
 * Read environment variables from .env file
 */
// import dotenv from 'dotenv'
// dotenv.config()

/**
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
  testDir: './src/tests/e2e',

  /* Run tests in files in parallel */
  fullyParallel: true,

  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,

  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,

  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 1 : undefined,

  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: [
    ['html'],
    ['json', { outputFile: 'test-results/e2e-results.json' }],
    ['junit', { outputFile: 'test-results/e2e-results.xml' }]
  ],

  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:5173',

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',

    /* Take screenshot on failure */
    screenshot: 'only-on-failure',

    /* Record video on failure */
    video: 'retain-on-failure',

    /* Global timeout for each test */
    actionTimeout: 30000,

    /* Global timeout for page navigation */
    navigationTimeout: 60000,

    /* Ignore HTTPS errors */
    ignoreHTTPSErrors: true,

    /* Viewport size */
    viewport: { width: 1280, height: 720 },

    /* Default locale */
    locale: 'en-US',

    /* Default timezone */
    timezoneId: 'America/New_York'
  },

  /* Configure projects for major browsers */
  projects: [
    // Desktop Browsers
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // Enable features for music playback testing
        launchOptions: {
          args: [
            '--autoplay-policy=no-user-gesture-required',
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor'
          ]
        }
      },
    },

    {
      name: 'firefox',
      use: {
        ...devices['Desktop Firefox'],
        // Firefox-specific settings for audio testing
        launchOptions: {
          firefoxUserPrefs: {
            'media.autoplay.default': 0, // Allow autoplay
            'media.autoplay.blocking_policy': 0
          }
        }
      },
    },

    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },

    // Mobile Testing
    {
      name: 'Mobile Chrome',
      use: {
        ...devices['Pixel 5'],
        // Mobile-specific viewport
        viewport: { width: 393, height: 851 }
      },
    },

    {
      name: 'Mobile Safari',
      use: {
        ...devices['iPhone 12'],
        // iOS-specific settings
        viewport: { width: 390, height: 844 }
      },
    },

    // Tablet Testing
    {
      name: 'Tablet',
      use: {
        ...devices['iPad Pro'],
        viewport: { width: 1024, height: 1366 }
      },
    },

    // Raspberry Pi Simulation
    {
      name: 'Raspberry Pi',
      use: {
        viewport: { width: 800, height: 480 }, // Common Pi touchscreen resolution
        deviceScaleFactor: 1,
        isMobile: false,
        hasTouch: true, // Pi often has touchscreen
        // Simulate lower-end hardware
        launchOptions: {
          args: [
            '--memory-pressure-off',
            '--max_old_space_size=512'
          ]
        }
      },
    },

    // Performance Testing Browser
    {
      name: 'Performance',
      use: {
        ...devices['Desktop Chrome'],
        // Enable performance monitoring
        launchOptions: {
          args: [
            '--enable-precise-memory-info',
            '--enable-memory-info',
            '--js-flags=--expose-gc'
          ]
        }
      },
    }
  ],

  /* Configuration for local development server */
  webServer: process.env.CI ? undefined : {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120000, // 2 minutes to start dev server
    env: {
      // Environment variables for E2E testing
      NODE_ENV: 'test',
      VITE_API_BASE_URL: process.env.E2E_API_URL || 'http://localhost:8000',
      VITE_WS_URL: process.env.E2E_WS_URL || 'ws://localhost:8000',
      // Enable mock hardware for testing
      VITE_USE_MOCK_HARDWARE: 'true',
      // Disable analytics in tests
      VITE_ENABLE_ANALYTICS: 'false'
    }
  },

  /* Global test timeout */
  timeout: 60000,

  /* Expect timeout for assertions */
  expect: {
    timeout: 10000,
    // Take screenshot on assertion failure
    toHaveScreenshot: {
      mode: 'only-on-failure',
      animationHandling: 'wait'
    }
  },

  /* Global setup and teardown */
  globalSetup: './src/tests/e2e/global-setup.ts',
  globalTeardown: './src/tests/e2e/global-teardown.ts',

  /* Test patterns */
  testMatch: [
    '**/*.e2e.{js,ts}',
    '**/e2e/**/*.{test,spec}.{js,ts}'
  ],

  /* Ignore patterns */
  testIgnore: [
    '**/node_modules/**',
    '**/dist/**',
    '**/*.unit.{js,ts}',
    '**/*.integration.{js,ts}'
  ],

  /* Output directory for test results */
  outputDir: 'test-results/e2e-artifacts',

  /* Maximum number of test failures before stopping */
  maxFailures: process.env.CI ? 10 : undefined,

  /* Test metadata */
  metadata: {
    testType: 'end-to-end',
    framework: 'playwright',
    application: 'The Open Music Box',
    version: process.env.npm_package_version || '1.0.0'
  },

  /* Additional configuration for specific test types */
  grep: process.env.E2E_GREP ? new RegExp(process.env.E2E_GREP) : undefined,
  grepInvert: process.env.E2E_GREP_INVERT ? new RegExp(process.env.E2E_GREP_INVERT) : undefined
})