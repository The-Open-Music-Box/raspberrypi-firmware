import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: [
      // Keep to safe, maintained unit tests first
      'src/services/__tests__/**/*.test.ts',
      'src/services/socket/__tests__/**/*.test.ts',
      'src/unit/**/*.test.ts',
      // Re-enabling src/tests/unit to fix legacy field names
      'src/tests/unit/**/*.test.ts',
      // Include contract tests
      'src/tests/contracts/**/*.contract.test.ts'
    ],
    exclude: [
      // Exclude integration and e2e tests (for future enablement)
      'src/tests/integration/**',
      'src/**/__e2e__/**'
    ],
    coverage: {
      provider: 'v8',
      include: [
        'src/stores/unifiedPlaylistStore.ts'
      ],
      reporter: ['text', 'lcov'],
      exclude: [
        'src/**/__tests__/**',
        'src/tests/**'
      ],
      thresholds: {
        lines: 100,
        statements: 100,
        branches: 100,
        functions: 100
      }
    }
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, './src')
    }
  }
})
