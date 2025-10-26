<template>
  <div>
    <main class="pt-12">
      <div class="mx-auto max-w-7xl px-4 pb-12 sm:px-6 lg:px-8">
        <div class="rounded-lg bg-surface px-5 py-6 shadow sm:px-6">
          <div class="app-container">
            <AudioPlayer
              :selectedTrack="selectedTrack"
              :playlist="selectedPlaylist"
            />
          </div>
          <!-- Zone d'upload globale supprimée - l'upload se fait maintenant dans chaque playlist -->

          <FileListContainer
            :selectedTrack="selectedTrack"
            @select-track="handleSelectTrack"
          />


        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import AudioPlayer from '../components/audio/AudioPlayer.vue'
// UploadForm global supprimé car l'upload se fait directement dans les playlists
import FileListContainer from '../components/files/FileListContainer.vue'
// import GeneralInfo from '../components/StatsInfo.vue' // Removed - not used
import type { Track, PlayList } from '../components/files/types'

// const uploadProgress = ref(0) // Removed - not used
const selectedTrack = ref<Track | null>(null)
const selectedPlaylist = ref<PlayList | null>(null)

const handleSelectTrack = (data: { track: Track, playlist: PlayList }) => {
  selectedTrack.value = data.track
  selectedPlaylist.value = data.playlist
}
</script>