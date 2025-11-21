<template>
  <div>
    <TransitionRoot appear :show="open" as="template">
      <Dialog as="div" @close="$emit('cancel')" class="relative z-10">
        <TransitionChild
          as="template"
          enter="duration-300 ease-out"
          enter-from="opacity-0"
          enter-to="opacity-100"
          leave="duration-200 ease-in"
          leave-from="opacity-100"
          leave-to="opacity-0"
        >
          <div class="fixed inset-0 bg-black bg-opacity-25 dark:bg-opacity-50" />
        </TransitionChild>

        <div class="fixed inset-0 overflow-y-auto">
          <div class="flex min-h-full items-center justify-center p-4 text-center">
            <TransitionChild
              as="template"
              enter="duration-300 ease-out"
              enter-from="opacity-0 scale-95"
              enter-to="opacity-100 scale-100"
              leave="duration-200 ease-in"
              leave-from="opacity-100 scale-100"
              leave-to="opacity-0 scale-95"
            >
              <DialogPanel
                class="w-full max-w-md transform overflow-hidden rounded-2xl bg-surface p-6 text-left align-middle shadow-xl transition-all"
              >
                <DialogTitle as="h3" class="text-lg font-medium leading-6 text-onBackground">
                  {{ t('file.createPlaylist') }}
                </DialogTitle>
                
                <div class="mt-4">
                  <div class="mb-4">
                    <label for="playlist-title" class="block text-sm font-medium text-onBackground mb-1">
                      {{ t('file.playlistTitle') }}
                    </label>
                    <input
                      id="playlist-title"
                      v-model="title"
                      type="text"
                      class="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary bg-background text-onBackground"
                      :placeholder="t('file.playlistTitlePlaceholder')"
                      @keyup.enter="createPlaylist"
                      ref="titleInput"
                    />
                    <p v-if="error" class="mt-2 text-sm text-error">{{ error }}</p>
                  </div>
                </div>

                <div class="mt-6 flex justify-end space-x-3">
                  <button
                    type="button"
                    class="inline-flex justify-center rounded-md border border-border px-4 py-2 text-sm font-medium text-onBackground hover:bg-background focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
                    @click="$emit('cancel')"
                  >
                    {{ t('common.cancel') }}
                  </button>
                  <button
                    type="button"
                    :disabled="isCreating || !title.trim()"
                    :class="[
                      'inline-flex justify-center rounded-md border border-transparent px-4 py-2 text-sm font-medium text-onPrimary focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary',
                      isCreating || !title.trim() ? 'bg-primary-light cursor-not-allowed' : 'bg-primary hover:bg-primary-light'
                    ]"
                    @click="createPlaylist"
                  >
                    <svg v-if="isCreating" class="animate-spin -ml-1 mr-2 h-4 w-4 text-onPrimary" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    {{ t('common.create') }}
                  </button>
                </div>
              </DialogPanel>
            </TransitionChild>
          </div>
        </div>
      </Dialog>
    </TransitionRoot>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { logger } from '@/utils/logger'
import {
  Dialog,
  DialogPanel,
  DialogTitle,
  TransitionChild,
  TransitionRoot,
} from '@headlessui/vue'

const { t } = useI18n()

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits(['create', 'cancel'])

const title = ref('')
const error = ref('')
const isCreating = ref(false)
const titleInput = ref<HTMLInputElement | null>(null)

// Focus the title input when the dialog opens
watch(() => props.open, (isOpen: boolean) => {
  if (isOpen) {
    // Reset form state when opening
    title.value = ''
    error.value = ''
    isCreating.value = false
    
    // Focus the input after the dialog animation completes
    nextTick(() => {
      titleInput.value?.focus()
    })
  } else {
    // Reset creating state when closing
    isCreating.value = false
  }
})

// Create a new playlist
async function createPlaylist() {
  if (!title.value.trim()) {
    error.value = t('file.errorEmptyTitle')
    return
  }
  
  // Prevent double-clicks
  if (isCreating.value) {
    return
  }
  
  try {
    isCreating.value = true
    error.value = ''
    emit('create', title.value.trim())
    // Note: Dialog will be closed by parent component after successful creation
  } catch (err) {
    logger.error('Error creating playlist', { error: err }, 'CreatePlaylistDialog')
    error.value = t('file.errorCreating')
    isCreating.value = false
  }
}
</script>
