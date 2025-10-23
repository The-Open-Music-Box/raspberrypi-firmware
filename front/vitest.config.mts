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
        'src/**/*.ts',
        'src/**/*.vue'
      ],
      reporter: ['text', 'lcov', 'html'],
      exclude: [
        'src/**/__tests__/**',
        'src/**/*.test.ts',
        'src/**/*.spec.ts',
        'src/tests/**',
        'src/test/**',
        'src/**/*.d.ts',
        'src/main.ts',
        'src/App.vue'
      ],
      thresholds: {
        // Start with realistic thresholds, gradually increase
        lines: 50,
        statements: 50,
        branches: 40,
        functions: 50
      }
    }
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, './src')
    }
  }
})
