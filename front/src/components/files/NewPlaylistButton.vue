<template>
  <button
    @click="$emit('click')"
    class="px-3 py-1.5 rounded-md bg-primary text-onPrimary hover:bg-primary-light text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-focus"
  >
    {{ t('file.newPlaylist') }}
  </button>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

defineEmits(['click'])
</script>
