<template>
  <TransitionRoot appear :show="open" as="template">
    <Dialog as="div" @close="$emit('close')" class="relative z-10">
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
              <DialogTitle
                as="h3"
                class="text-lg font-medium leading-6 text-onBackground"
              >
                {{ title || t('common.confirmDelete') }}
              </DialogTitle>
              
              <div class="mt-2">
                <p class="text-sm text-disabled">
                  {{ message || t('common.deleteConfirmMessage') }}
                </p>
              </div>

              <div class="mt-4 flex justify-end space-x-3">
                <button
                  type="button"
                  class="inline-flex justify-center rounded-md border border-transparent bg-background px-4 py-2 text-sm font-medium text-onBackground hover:bg-background-light focus:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                  @click="$emit('close')"
                >
                  {{ t('common.cancel') }}
                </button>
                <button
                  type="button"
                  class="inline-flex justify-center rounded-md border border-transparent bg-error px-4 py-2 text-sm font-medium text-onError hover:bg-error-light focus:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                  @click="$emit('confirm')"
                >
                  {{ t('common.delete') }}
                </button>
              </div>
            </DialogPanel>
          </TransitionChild>
        </div>
      </div>
    </Dialog>
  </TransitionRoot>
</template>

<script setup lang="ts">
import { } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  Dialog,
  DialogPanel,
  DialogTitle,
  TransitionChild,
  TransitionRoot,
} from '@headlessui/vue'

const { t } = useI18n()

defineProps({
  open: {
    type: Boolean,
    required: true
  },
  title: {
    type: String,
    default: ''
  },
  message: {
    type: String,
    default: ''
  }
})

defineEmits(['close', 'confirm'])
</script>
