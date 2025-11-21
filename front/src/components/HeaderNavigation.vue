<template>
  <Disclosure as="nav" :class="'bg-surface'" v-slot="{ open }">
    <div class="mx-auto max-w-7xl sm:px-6 lg:px-8">
      <div class="border-b border-border">
        <div class="flex h-16 items-center justify-between px-4 sm:px-0">
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <img class="h-10 w-10" src="@/assets/logo.jpg"
                alt="The Music Box" />
            </div>
            <div class="hidden md:block">
              <div class="ml-10 flex items-baseline space-x-8">
                <router-link
                  v-for="item in navigation"
                  :key="item.name"
                  :to="item.href"
                  :class="[
                    item.current && item.key === 'home'
                      ? 'bg-background text-onBackground'
                      : item.current
                        ? 'bg-primary text-onPrimary'
                        : 'text-onBackground hover:bg-primary-light hover:text-onBackground',
                    'rounded-md px-3 py-2 text-sm font-medium',
                  ]"
                  :aria-current="item.current ? 'page' : undefined"
                >
                  {{ t(`navigation.${item.key}`) }}
                </router-link>
              </div>
            </div>
          </div>

          <div class="flex items-center space-x-4">
            <!-- Social links -->
            <a href="https://theopenmusicbox.com" target="_blank" rel="noopener" aria-label="Website" class="hover:text-primary">
              <img src="@/assets/web.svg" alt="Website" class="h-6 w-6 inline" />
            </a>
            <a href="https://github.com/The-Open-Music-Box" target="_blank" rel="noopener" aria-label="GitHub" class="hover:text-primary">
              <img src="@/assets/github.svg" alt="GitHub" class="h-6 w-6 inline" />
            </a>
            <a href="http://facebook.com/theopenmusicbox/" target="_blank" rel="noopener" aria-label="Facebook" class="hover:text-primary">
              <img src="@/assets/facebook.svg" alt="Facebook" class="h-6 w-6 inline" />
            </a>
            <a href="https://bsky.app/profile/theopenmusicbox.com" target="_blank" rel="noopener" aria-label="Bluesky" class="hover:text-primary">
              <img src="@/assets/bsky.svg" alt="Bluesky" class="h-6 w-6 inline" />
            </a>
          </div>

          <div class="-mr-2 flex md:hidden">
            <DisclosureButton
              class="relative inline-flex items-center justify-center rounded-md bg-surface p-2 text-disabled hover:bg-primary hover:text-onPrimary focus:outline-none focus:ring-2 focus:ring-focus focus:ring-offset-2 focus:ring-offset-background">
              <span class="absolute -inset-0.5" />
              <span class="sr-only">Open main menu</span>
              <Bars3Icon v-if="!open" class="block h-6 w-6" aria-hidden="true" />
              <XMarkIcon v-else class="block h-6 w-6" aria-hidden="true" />
            </DisclosureButton>
          </div>
        </div>
      </div>
    </div>

    <DisclosurePanel class="border-b border-border md:hidden">
      <div class="space-y-1 px-2 py-3 sm:px-3">
        <router-link
          v-for="item in navigation"
          :key="item.name"
          :to="item.href"
          :class="[
            item.current
              ? 'bg-primary text-onPrimary'
              : 'text-onBackground hover:bg-primary-light hover:text-onPrimary',
            'block rounded-md px-3 py-2 text-base font-medium',
          ]"
          :aria-current="item.current ? 'page' : undefined"
        >
          {{ t(`navigation.${item.key}`) }}
        </router-link>
      </div>
    </DisclosurePanel>
  </Disclosure>
</template>

<script setup>
/**
 * HeaderNavigation Component
 *
 * Main navigation header for the application.
 * Provides responsive navigation menu with mobile support.
 */
import { Disclosure, DisclosureButton, DisclosurePanel } from '@headlessui/vue'
import { colors } from '@/theme/colors'
import { Bars3Icon, XMarkIcon } from '@heroicons/vue/24/outline'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

// Navigation items configuration
const navigation = ref([
  { name: 'Home', key: 'home', href: '/', current: true },
  { name: 'About', key: 'about', href: '/about', current: false },
  { name: 'Settings', key: 'settings', href: '/settings', current: false },
])
</script>

<style scoped>
nav {
  padding: 30px;
}

nav a {
  font-weight: bold;
  color: v-bind('colors.light.onBackground');
}

nav a.router-link-exact-active {
  color: v-bind('colors.light.primary');
}
</style>