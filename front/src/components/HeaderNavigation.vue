<template>
  <div class="header-modern">
    <div class="header-content">
      <div class="logo-modern">
        <div class="logo-icon">
          <img src="@/assets/logo.jpg" alt="TheOpenMusicBox" style="width: 100%; height: 100%; object-fit: cover; border-radius: 8px;" />
        </div>
        <span>{{ t('navigation.appName') || 'Music Player' }}</span>
      </div>

      <div class="flex items-center gap-3">
        <!-- Social links (desktop) -->
        <div class="hidden md:flex items-center gap-2">
          <a href="https://theopenmusicbox.com" target="_blank" rel="noopener" aria-label="Website" class="hover:opacity-70 transition-opacity">
            <img src="@/assets/web.svg" alt="Website" class="h-5 w-5" />
          </a>
          <a href="https://github.com/The-Open-Music-Box" target="_blank" rel="noopener" aria-label="GitHub" class="hover:opacity-70 transition-opacity">
            <img src="@/assets/github.svg" alt="GitHub" class="h-5 w-5" />
          </a>
          <a href="http://facebook.com/theopenmusicbox/" target="_blank" rel="noopener" aria-label="Facebook" class="hover:opacity-70 transition-opacity">
            <img src="@/assets/facebook.svg" alt="Facebook" class="h-5 w-5" />
          </a>
          <a href="https://bsky.app/profile/theopenmusicbox.com" target="_blank" rel="noopener" aria-label="Bluesky" class="hover:opacity-70 transition-opacity">
            <img src="@/assets/bsky.svg" alt="Bluesky" class="h-5 w-5" />
          </a>
        </div>

        <!-- Navigation (desktop) -->
        <div class="hidden md:flex items-center gap-2">
          <router-link
            v-for="item in navigation"
            :key="item.name"
            :to="item.href"
            :class="[
              'btn-modern',
              item.current ? '' : 'secondary'
            ]"
          >
            {{ t(`navigation.${item.key}`) }}
          </router-link>
        </div>

        <!-- Mobile menu button -->
        <Disclosure v-slot="{ open }">
          <DisclosureButton
            class="md:hidden btn-modern secondary p-2"
          >
            <span class="sr-only">Open main menu</span>
            <Bars3Icon v-if="!open" class="block h-6 w-6" aria-hidden="true" />
            <XMarkIcon v-else class="block h-6 w-6" aria-hidden="true" />
          </DisclosureButton>

          <DisclosurePanel class="md:hidden absolute left-0 right-0 top-full mt-2 mx-6 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
            <div class="p-4 space-y-2">
              <router-link
                v-for="item in navigation"
                :key="item.name"
                :to="item.href"
                :class="[
                  'block btn-modern w-full text-left',
                  item.current ? '' : 'secondary'
                ]"
              >
                {{ t(`navigation.${item.key}`) }}
              </router-link>
            </div>
          </DisclosurePanel>
        </Disclosure>
      </div>
    </div>
  </div>
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