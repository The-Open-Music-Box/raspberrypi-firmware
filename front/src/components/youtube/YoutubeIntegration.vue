<template>
  <div class="youtube-integration">
    <h3 class="text-lg font-medium mb-4">Add from YouTube</h3>
    
    <!-- Search Section -->
    <div class="mb-6">
      <div class="flex gap-3 mb-4">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search YouTube videos..."
          class="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          @keyup.enter="searchVideos"
        />
        <button
          @click="searchVideos"
          :disabled="!searchQuery.trim() || searching"
          class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ searching ? 'Searching...' : 'Search' }}
        </button>
      </div>
      
      <!-- Direct URL Input -->
      <div class="flex gap-3">
        <input
          v-model="directUrl"
          type="text"
          placeholder="Or paste YouTube URL directly..."
          class="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
        />
        <button
          @click="downloadFromUrl"
          :disabled="!directUrl.trim() || !selectedPlaylistId || downloading"
          class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ downloading ? 'Downloading...' : 'Download' }}
        </button>
      </div>
    </div>

    <!-- Search Results -->
    <div v-if="searchResults.length > 0" class="mb-6">
      <h4 class="text-md font-medium mb-3">Search Results</h4>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div
          v-for="video in searchResults"
          :key="video.id"
          class="flex gap-3 p-4 border border-gray-200 rounded-lg hover:border-gray-300"
        >
          <img
            :src="video.thumbnail_url"
            :alt="video.title"
            class="w-20 h-15 object-cover rounded"
          />
          <div class="flex-1 min-w-0">
            <h5 class="font-medium text-sm mb-1 truncate" :title="video.title">
              {{ video.title }}
            </h5>
            <p class="text-xs text-gray-600 mb-1">{{ video.channel }}</p>
            <p class="text-xs text-gray-500">
              Duration: {{ formatDuration(video.duration_ms) }} | 
              Views: {{ formatNumber(video.view_count) }}
            </p>
            <button
              @click="downloadVideo(video)"
              :disabled="!selectedPlaylistId || downloading"
              class="mt-2 px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Add to Playlist
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Playlist Selection -->
    <div class="mb-6">
      <label class="block text-sm font-medium mb-2">Select Playlist:</label>
      <select
        v-model="selectedPlaylistId"
        class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
      >
        <option value="">Choose a playlist...</option>
        <option
          v-for="playlist in playlists"
          :key="playlist.id"
          :value="playlist.id"
        >
          {{ playlist.title }}
        </option>
      </select>
    </div>

    <!-- Download Progress -->
    <div v-if="downloadTasks.length > 0" class="mb-6">
      <h4 class="text-md font-medium mb-3">Download Progress</h4>
      <div class="space-y-3">
        <div
          v-for="task in downloadTasks"
          :key="task.task_id"
          class="p-4 border border-gray-200 rounded-lg"
        >
          <div class="flex justify-between items-start mb-2">
            <div class="flex-1">
              <p class="font-medium text-sm">{{ task.title || 'Downloading...' }}</p>
              <p class="text-xs text-gray-600">{{ task.current_step || 'Preparing...' }}</p>
            </div>
            <span
              class="px-2 py-1 text-xs rounded"
              :class="getStatusClass(task.status)"
            >
              {{ task.status }}
            </span>
          </div>
          
          <!-- Progress Bar -->
          <div class="w-full bg-gray-200 rounded-full h-2">
            <div
              class="bg-blue-600 h-2 rounded-full transition-all duration-300"
              :style="{ width: `${task.progress_percent || 0}%` }"
            ></div>
          </div>
          
          <div class="flex justify-between text-xs text-gray-500 mt-1">
            <span>{{ task.progress_percent || 0 }}%</span>
            <span v-if="task.estimated_time_remaining">
              ETA: {{ formatTime(task.estimated_time_remaining) }}
            </span>
          </div>
          
          <!-- Error Message -->
          <div v-if="task.error_message" class="mt-2 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
            {{ task.error_message }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { youtubeApi } from '@/services/apiService'
import { socketService } from '@/services/socketService'
import { useServerStateStore } from '@/stores/serverStateStore'

const serverStateStore = useServerStateStore()
const { playlists } = serverStateStore

interface VideoResult {
  id: string
  title: string
  channel: string
  thumbnail_url: string
  duration_ms: number
  view_count: number
}

interface DownloadTask {
  task_id: string
  status: string
  progress_percent?: number
  title?: string
  url?: string
  current_step?: string
  estimated_time_remaining?: number
  error_message?: string
}

// Reactive state
const searchQuery = ref('')
const directUrl = ref('')
const searchResults = ref<VideoResult[]>([])
const selectedPlaylistId = ref('')
const searching = ref(false)
const downloading = ref(false)
const downloadTasks = ref<DownloadTask[]>([])

// YouTube event handlers
const handleYoutubeProgress = (data: DownloadTask) => {
  const taskIndex = downloadTasks.value.findIndex(task => task.task_id === data.task_id)
  if (taskIndex !== -1) {
    downloadTasks.value[taskIndex] = { ...downloadTasks.value[taskIndex], ...data }
  } else {
    downloadTasks.value.push(data)
  }
}

const handleYoutubeComplete = (data: DownloadTask) => {
  const taskIndex = downloadTasks.value.findIndex(task => task.task_id === data.task_id)
  if (taskIndex !== -1) {
    downloadTasks.value[taskIndex] = {
      ...downloadTasks.value[taskIndex],
      ...data,
      status: 'completed',
      progress_percent: 100
    }
  }
  downloading.value = false
}

const handleYoutubeError = (data: DownloadTask) => {
  const taskIndex = downloadTasks.value.findIndex(task => task.task_id === data.task_id)
  if (taskIndex !== -1) {
    downloadTasks.value[taskIndex] = {
      ...downloadTasks.value[taskIndex],
      ...data,
      status: 'error'
    }
  }
  downloading.value = false
}

// Component methods
const searchVideos = async () => {
  if (!searchQuery.value.trim()) return
  
  searching.value = true
  try {
    const response = await youtubeApi.searchVideos(searchQuery.value)
    searchResults.value = response.results || []
  } catch (error) {
    // Error handled silently - TODO: Add user notification system
  } finally {
    searching.value = false
  }
}

const downloadFromUrl = async () => {
  if (!directUrl.value.trim() || !selectedPlaylistId.value) return
  
  downloading.value = true
  try {
    const response = await youtubeApi.downloadVideo(directUrl.value, selectedPlaylistId.value)
    downloadTasks.value.push({
      task_id: response.task_id,
      status: 'pending',
      progress_percent: 0,
      title: 'Downloading from URL...',
      url: directUrl.value
    })
    directUrl.value = ''
  } catch (error) {
    // Error handled silently - TODO: Add user notification system
    downloading.value = false
  }
}

const downloadVideo = async (video: VideoResult) => {
  if (!selectedPlaylistId.value) return
  
  downloading.value = true
  try {
    const videoUrl = `https://www.youtube.com/watch?v=${video.id}`
    const response = await youtubeApi.downloadVideo(videoUrl, selectedPlaylistId.value)
    downloadTasks.value.push({
      task_id: response.task_id,
      status: 'pending',
      progress_percent: 0,
      title: video.title,
      url: videoUrl
    })
  } catch (error) {
    // Error handled silently - TODO: Add user notification system
    downloading.value = false
  }
}

// Utility functions
const formatDuration = (ms: number): string => {
  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`
}

const formatNumber = (num: number): string => {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M'
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K'
  }
  return num.toString()
}

const formatTime = (seconds: number): string => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const getStatusClass = (status: string): string => {
  switch (status) {
    case 'completed':
      return 'bg-green-100 text-green-800'
    case 'error':
      return 'bg-red-100 text-red-800'
    case 'downloading':
    case 'processing':
      return 'bg-blue-100 text-blue-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}

// Lifecycle hooks
onMounted(() => {
  socketService.on('youtube:progress', handleYoutubeProgress)
  socketService.on('youtube:complete', handleYoutubeComplete)
  socketService.on('youtube:error', handleYoutubeError)
})

onUnmounted(() => {
  socketService.off('youtube:progress', handleYoutubeProgress)
  socketService.off('youtube:complete', handleYoutubeComplete)
  socketService.off('youtube:error', handleYoutubeError)
})
</script>

<style scoped>
.youtube-integration {
  @apply max-w-4xl mx-auto p-6;
}
</style>