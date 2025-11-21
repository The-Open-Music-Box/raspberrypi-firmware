<template>
  <div class="flex flex-none items-center gap-x-4">
    <button @click="handleAssociate"
      class="inline-flex w-full justify-center rounded-md px-3 py-2 text-sm font-semibold bg-primary text-onPrimary shadow-sm hover:bg-primary-light focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
    >
      {{ t('file.associateTag') }}
    </button>
    <Menu as="div" class="relative flex-none">
      <MenuButton class="-m-2.5 block p-2.5 text-disabled hover:text-primary">
        <span class="sr-only">{{ t('file.openOptions') }}</span>
        <EllipsisVerticalIcon class="h-5 w-5" aria-hidden="true" />
      </MenuButton>
      <MenuItems>
        <MenuItem v-slot="{ active }">
          <button @click="handleDelete"
            :class="[active ? 'bg-background' : '', 'block w-full text-left px-3 py-1 text-sm leading-6 text-onBackground']"
          >
            {{ t('common.delete') }}<span class="sr-only">, {{ file.name }}</span>
          </button>
        </MenuItem>
      </MenuItems>
    </Menu>
  </div>
</template>

<script setup lang="ts">
/**
 * FileActions Component
 *
 * Provides action buttons for a file item.
 * Includes primary action button and dropdown menu with additional options.
 */

import { Menu, MenuButton, MenuItem, MenuItems } from '@headlessui/vue'
import { EllipsisVerticalIcon } from '@heroicons/vue/20/solid'
import type { LegacyAudioFile } from './types'
import { useFileDialog } from './composables/useFileDialog'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps<{
  /** The file to provide actions for */
  file: LegacyAudioFile
}>()

const { openDeleteDialog } = useFileDialog()

/**
 * Handle delete action for the file
 */
const handleDelete = () => {
  openDeleteDialog(props.file)
}

/**
 * Handle association action for the file
 */
const handleAssociate = () => {
  console.log('Associate clicked for file:', props.file)
}
</script>

