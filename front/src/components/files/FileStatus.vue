<template>
  <p :class="[STATUS_CLASSES[status], 'rounded-md whitespace-nowrap mt-0.5 px-1.5 py-0.5 text-xs font-medium ring-1 ring-inset']">
    {{ t(`file.status.${status}`) }}
  </p>
</template>

<script setup lang="ts">
/**
 * FileStatus Component
 *
 * Shows the current status of a file with appropriate styling.
 * Different statuses have different colors for visual distinction.
 */

import { FileStatus, STATUS_CLASSES } from './types'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

defineProps<{
  /** The status of the file */
  status: FileStatus
}>()
</script>