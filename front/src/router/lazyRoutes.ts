/**
 * Lazy-loaded route components for better code splitting
 * This reduces the initial bundle size by loading routes on demand
 */

import { defineAsyncComponent, type Component } from 'vue'
import { logger } from '@/utils/logger'

/**
 * Create a lazy-loaded component with error handling and loading states
 */
function createLazyComponent(importFn: () => Promise<{ default: Component }>, componentName: string) {
  return defineAsyncComponent({
    loader: importFn,
    loadingComponent: {
      template: `
        <div class="flex justify-center items-center min-h-[200px] p-8">
          <div class="text-center">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <div class="text-gray-600">Loading ${componentName}...</div>
          </div>
        </div>
      `
    },
    errorComponent: {
      template: `
        <div class="flex justify-center items-center min-h-[200px] p-8">
          <div class="text-center text-red-500">
            <div class="mb-4">
              <svg class="w-16 h-16 mx-auto text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 15.5c-.77.833.192 2.5 1.732 2.5z"></path>
              </svg>
            </div>
            <h3 class="text-lg font-semibold mb-2">Failed to load ${componentName}</h3>
            <p class="text-gray-600 mb-4">The page component couldn't be loaded. This might be due to a network issue.</p>
            <button onclick="window.location.reload()" class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors">
              Refresh Page
            </button>
          </div>
        </div>
      `
    },
    delay: 200,
    timeout: 30000, // Increased timeout to 30 seconds for better reliability
    onError: (error) => {
      logger.error(`Failed to load component: ${componentName}`, { 
        error, 
        message: error.message,
        stack: error.stack,
        timestamp: new Date().toISOString()
      }, 'LazyRoutes')
    }
  })
}

// Lazy-loaded route components
export const HomePage = createLazyComponent(
  () => import('../views/HomePage.vue'),
  'HomePage'
)

export const AboutPage = createLazyComponent(
  () => import('../views/AboutPage.vue'),
  'AboutPage'
)

export const SettingsPage = createLazyComponent(
  () => import('../views/SettingsPage.vue'),
  'SettingsPage'
)
