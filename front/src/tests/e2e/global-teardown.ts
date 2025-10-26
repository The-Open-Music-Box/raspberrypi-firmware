/**
 * Global Teardown for E2E Tests
 *
 * Cleans up the testing environment after all E2E tests have completed.
 * Handles cleanup of test data, temporary files, and resources.
 */

import { FullConfig } from '@playwright/test'
import fs from 'fs'
import path from 'path'

async function globalTeardown(config: FullConfig) {
  console.log('🧹 Starting E2E Global Teardown...')

  const apiURL = process.env.E2E_API_URL || 'http://localhost:8000'

  try {
    // Cleanup test data from backend
    console.log('🗑️ Cleaning up test data...')
    await cleanupTestData(apiURL)

    // Generate test report summary
    console.log('📊 Generating test report summary...')
    await generateTestSummary()

    // Cleanup temporary files (keep results for CI)
    if (!process.env.CI) {
      console.log('🗂️ Cleaning up temporary files...')
      await cleanupTemporaryFiles()
    }

    // Archive test artifacts if needed
    if (process.env.E2E_ARCHIVE_RESULTS === 'true') {
      console.log('📦 Archiving test results...')
      await archiveTestResults()
    }

    console.log('✅ Global teardown completed successfully')

  } catch (error) {
    console.error('❌ Global teardown failed:', error)
    // Don't throw error to allow process to complete
  }
}

/**
 * Cleanup test data from the backend
 */
async function cleanupTestData(apiURL: string): Promise<void> {
  try {
    // Delete test playlists
    const cleanupResponse = await fetch(`${apiURL}/test/cleanup`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' }
    })

    if (cleanupResponse.ok) {
      console.log('🗑️ Test playlists and tracks cleaned up')
    } else {
      console.warn('⚠️ Test data cleanup failed, continuing...')
    }

    // Delete test user
    const userCleanupResponse = await fetch(`${apiURL}/test/users/e2e_test_user`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' }
    })

    if (userCleanupResponse.ok) {
      console.log('👤 Test user cleaned up')
    }

    // Reset any modified settings
    const settingsResetResponse = await fetch(`${apiURL}/test/settings/reset`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })

    if (settingsResetResponse.ok) {
      console.log('⚙️ Settings reset to defaults')
    }

  } catch (error) {
    console.warn('⚠️ Test data cleanup failed:', error)
    // Continue with other cleanup tasks
  }
}

/**
 * Generate a summary of test results
 */
async function generateTestSummary(): Promise<void> {
  try {
    const resultsFile = 'test-results/e2e-results.json'

    if (fs.existsSync(resultsFile) {
      const results = JSON.parse(fs.readFileSync(resultsFile, 'utf-8')

      const summary = {
        totalTests: results.stats?.total || 0,
        passed: results.stats?.passed || 0,
        failed: results.stats?.failed || 0,
        skipped: results.stats?.skipped || 0,
        duration: results.stats?.duration || 0,
        timestamp: new Date().toISOString(),
        browsers: extractBrowserResults(results),
        slowestTests: extractSlowestTests(results),
        failedTests: extractFailedTests(results)
      }

      // Write summary
      fs.writeFileSync(
        'test-results/e2e-summary.json',
        JSON.stringify(summary, null, 2)
      )

      // Write human-readable summary
      const readableSummary = generateReadableSummary(summary)
      fs.writeFileSync('test-results/e2e-summary.md', readableSummary)

      console.log('📊 Test summary generated')
      console.log(`   Total Tests: ${summary.totalTests}`)
      console.log(`   Passed: ${summary.passed}`)
      console.log(`   Failed: ${summary.failed}`)
      console.log(`   Duration: ${Math.round(summary.duration / 1000)}s`)

      // Log warnings for failed tests
      if (summary.failed > 0) {
        console.warn(`⚠️ ${summary.failed} tests failed`)
      }
    }

  } catch (error) {
    console.warn('⚠️ Failed to generate test summary:', error)
  }
}

/**
 * Extract browser-specific results
 */
function extractBrowserResults(results: any): any {
  const browsers: any = {}

  if (results.suites) {
    results.suites.forEach((suite: any) => {
      if (suite.title && (suite.title.includes('chromium') || suite.title.includes('firefox') || suite.title.includes('webkit')) {
        browsers[suite.title] = {
          tests: suite.specs?.length || 0,
          passed: suite.specs?.filter((spec: any) => spec.ok).length || 0,
          failed: suite.specs?.filter((spec: any) => !spec.ok).length || 0
        }
      }
    })
  }

  return browsers
}

/**
 * Extract slowest tests
 */
function extractSlowestTests(results: any, limit: number = 5): any[] {
  const allTests: any[] = []

  if (results.suites) {
    const extractTests = (suite: any) => {
      if (suite.specs) {
        suite.specs.forEach((spec: any) => {
          if (spec.tests) {
            spec.tests.forEach((test: any) => {
              allTests.push({
                title: test.title,
                duration: test.results?.[0]?.duration || 0,
                file: spec.file
              })
            })
          }
        })
      }

      if (suite.suites) {
        suite.suites.forEach(extractTests)
      }
    }

    results.suites.forEach(extractTests)
  }

  return allTests
    .sort((a, b) => b.duration - a.duration)
    .slice(0, limit)
    .map(test => ({
      ...test,
      duration: Math.round(test.duration)
    })
}

/**
 * Extract failed tests with details
 */
function extractFailedTests(results: any): any[] {
  const failedTests: any[] = []

  if (results.suites) {
    const extractFailed = (suite: any) => {
      if (suite.specs) {
        suite.specs.forEach((spec: any) => {
          if (spec.tests) {
            spec.tests.forEach((test: any) => {
              if (!test.ok) {
                failedTests.push({
                  title: test.title,
                  file: spec.file,
                  error: test.results?.[0]?.error?.message || 'Unknown error',
                  duration: test.results?.[0]?.duration || 0
                })
              }
            })
          }
        })
      }

      if (suite.suites) {
        suite.suites.forEach(extractFailed)
      }
    }

    results.suites.forEach(extractFailed)
  }

  return failedTests
}

/**
 * Generate human-readable summary
 */
function generateReadableSummary(summary: any): string {
  const passRate = summary.totalTests > 0
    ? Math.round((summary.passed / summary.totalTests) * 100)
    : 0

  let md = `# E2E Test Results Summary\n\n`
  md += `**Generated:** ${summary.timestamp}\n\n`
  md += `## Overview\n\n`
  md += `- **Total Tests:** ${summary.totalTests}\n`
  md += `- **Passed:** ${summary.passed}\n`
  md += `- **Failed:** ${summary.failed}\n`
  md += `- **Skipped:** ${summary.skipped}\n`
  md += `- **Pass Rate:** ${passRate}%\n`
  md += `- **Duration:** ${Math.round(summary.duration / 1000)}s\n\n`

  if (Object.keys(summary.browsers).length > 0) {
    md += `## Browser Results\n\n`
    Object.entries(summary.browsers).forEach(([browser, stats]: [string, any]) => {
      md += `### ${browser}\n`
      md += `- Tests: ${stats.tests}\n`
      md += `- Passed: ${stats.passed}\n`
      md += `- Failed: ${stats.failed}\n\n`
    })
  }

  if (summary.slowestTests.length > 0) {
    md += `## Slowest Tests\n\n`
    summary.slowestTests.forEach((test: any, i: number) => {
      md += `${i + 1}. **${test.title}** - ${test.duration}ms\n`
    })
    md += `\n`
  }

  if (summary.failedTests.length > 0) {
    md += `## Failed Tests\n\n`
    summary.failedTests.forEach((test: any) => {
      md += `### ${test.title}\n`
      md += `- **File:** ${test.file}\n`
      md += `- **Error:** ${test.error}\n`
      md += `- **Duration:** ${test.duration}ms\n\n`
    })
  }

  return md
}

/**
 * Cleanup temporary files
 */
async function cleanupTemporaryFiles(): Promise<void> {
  try {
    const tempDirs = [
      'test-results/videos',
      'test-results/traces'
    ]

    const tempFiles = [
      'test-results/auth-state.json'
    ]

    // Remove temporary directories
    tempDirs.forEach(dir => {
      if (fs.existsSync(dir) {
        fs.rmSync(dir, { recursive: true, force: true })
        console.log(`🗑️ Removed temporary directory: ${dir}`)
      }
    })

    // Remove temporary files
    tempFiles.forEach(file => {
      if (fs.existsSync(file) {
        fs.unlinkSync(file)
        console.log(`🗑️ Removed temporary file: ${file}`)
      }
    })

    console.log('✅ Temporary files cleaned up')

  } catch (error) {
    console.warn('⚠️ Failed to cleanup temporary files:', error)
  }
}

/**
 * Archive test results for long-term storage
 */
async function archiveTestResults(): Promise<void> {
  try {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
    const archiveDir = `test-archives/e2e-${timestamp}`

    if (!fs.existsSync('test-archives') {
      fs.mkdirSync('test-archives', { recursive: true })
    }

    // Copy test results to archive
    if (fs.existsSync('test-results') {
      fs.cpSync('test-results', archiveDir, { recursive: true })
      console.log(`📦 Test results archived to: ${archiveDir}`)
    }

    // Keep only last 10 archives to save space
    const archives = fs.readdirSync('test-archives')
      .filter(name => name.startsWith('e2e-')
      .sort()

    if (archives.length > 10) {
      const toDelete = archives.slice(0, archives.length - 10)
      toDelete.forEach(archive => {
        fs.rmSync(path.join('test-archives', archive), { recursive: true, force: true })
        console.log(`🗑️ Removed old archive: ${archive}`)
      })
    }

  } catch (error) {
    console.warn('⚠️ Failed to archive test results:', error)
  }
}

export default globalTeardown