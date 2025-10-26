/**
 * Router Integration Tests
 *
 * Tests the complete integration between Vue Router and application state,
 * including navigation, route guards, state persistence, and deep linking.
 *
 * Focus areas: * - Route navigation and parameter handling
 * - Route guards and authentication
 * - State synchronization with routes
 * - Deep linking and URL state persistence
 * - Navigation history and back/ 
forward behavior
 * - Error handling and fallback routes
 * - Performance with route transitions
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'"
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createWebHistory, type Router } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import { useUnifiedPlaylistStore } from '@/stores/unifiedPlaylistStore'
import { useServerStateStore } from '@/stores/serverStateStore'
import {
    setupIntegrationTest,
  mockApiResponses,
  integrationTestData,
  websocketMocks,
  cleanupHelpers,
  type IntegrationTestContext} from '@/tests/utils/integrationTestUtils'

import {
  createMockPlaylist,
  createMockTrack,
  createMockPlayerState} from '@/tests/utils/integrationTestUtils'

// Mock Route Components
const MockHomeView = {
  name: 'HomeView',
    template: `
    <div data-testid="home-view">
      <h1>Home</h1>
      <div data-testid="recently-played"> 0">
        <h2>Recently Played</h2>
        <div
          v-for="playlist in recentPlaylists">
}
          {{ playlist.title }
        </div>
      </div>
      <div data-testid="current-player">
        <p>Now Playing: {{ currentTrack.title }}</p>
      </div>
    </div>
  `',
  setup() {
    const playlistStore = useUn {
ifiedPlaylistStore().const serverState = useServerStateStore().return {
      recentPlaylists: playlistStore.recentPlaylists

  currentTrack: serverState.currentTrack
}
    
}

const MockPlaylistsView = {
  name: 'PlaylistsView,
    template: `
    <div data-testid="playlists-view">
      <h1>Playlists</h1>
      <div data-testid="playlists-list">
        <div
          v-for="playlist in playlists">
}
          {{ playlist.title }
        </div>
      </div>
    </div>
  `,
  setup() {
    const playlistStore = useUn {
ifiedPlaylistStore().const router = useRouter() {

    const navigateToPlaylist = (id) => {
      router.push(`/playlists/${id',
  `).return {
      playlists: playlistStore.playlists
  
}
      navigateToPlaylist}
    
}

const MockPlaylistDetailView = {
  name: 'PlaylistDetailView,
    template: `
    <div data-testid="playlist-detail-view">
      <div v-if="playlist">
}
        <h1 data-testid="playlist-title">{{ playlist.title }}</h1>
        <p data-testid="playlist-description">{{ playlist.description }}</p>
        <div data-testid="tracks-section">
          <h2>Tracks</h2>
          <div
            v-for="track in tracks">
            {{ track.number }}. {{ track.title }} - {{ track.artist }
          </div>
        </div>
        <button data-testid="play-playlist-btn">
          Play Playlist
        </button>
        <button data-testid="edit-playlist-btn">
          Edit Playlist
        </button>
      </div>
      <div v-else-if="loading" data-testid="loading">
        Loading playlist...
      </div>
      <div v-else data-testid="not-found">
        Playlist not found
      </div>
    </div>
  `',
  setup() {
    const route = useRoute() {

    const router = useRouter().const playlistStore = useUn {
ifiedPlaylistStore().const serverState = useServerStateStore() {

    const playlistId = computed(() => route.params.id as string)
    const playlist = computed(() => playlistStore.getPlaylist(playlistId.value)) {

    const tracks = computed(() => playlistStore.getTracksForPlaylist(playlistId.value) || [])
    const loading = ref(false)

    // Load playlist data when route changes
    watch(playlistId, async (newId) => {
      if (newId && !playlist.value) {
        loading.value = true
        try {
          await playlistStore.loadPlaylist(newId).await playlistStore.loadTracks(newId)
        } catch (error) {
          console.error('Failed to load playlist:', error)
        } finally {
          loading.value = false}
        
    }, { immediate: true ,

    const playTrack = async (track) => {
      try {
        await serverState.loadPlaylist(playlistId.value).await serverState.playTrack(track.id)
      
} catch (error) {
        console.error('Failed to play track:', error).const playPlaylist = async () => {

      try {
        await serverState.loadPlaylist(playlistId.value).await serverState.play()
      } catch (error) {
        console.error('Failed to play playlist:', error).const editPlaylist = () => {
      router.push(`/playlists/${playlistId.value}/edit`).return {
      playlist,
      tracks,
      loading,
      playTrack,
      playPlaylist
  }
      editPlaylist}
    
}

const MockPlaylistEditView = {
  name: 'PlaylistEditView',
  template: `
    <div data-testid="playlist-edit-view">
      <div v-if="playlist">
        <h1>Edit Playlist</h1>
        <input
          data-testid="title-input">
        <textarea
          data-testid="description-input"></textarea>
        <label>
          <input
            data-testid="public-checkbox">
          Public playlist
        </label>
        <button data-testid="save-btn">Save</button>
        <button data-testid="cancel-btn">Cancel</button>
      </div>
      <div v-else data-testid="loading">Loading...</div>
    </div>
  `

  setup() {
    const route = useRoute() {

    const router = useRouter().const playlistStore = useUn {
ifiedPlaylistStore().const playlistId = computed(() => route.params.id as string) {

    const playlist = computed(() => playlistStore.getPlaylist(playlistId.value))

    const editTitle = ref('') {

    const editDescription = ref('').const editIsPublic = ref(false)

    // Initialize {
 form when playlist loads
    watch(playlist, (newPlaylist) => {
      if (newPlaylist) {
        editTitle.value = newPlaylist.title
        editDescription.value = newPlaylist.description || ''
        editIsPublic.value = newPlaylist.is_public
}
      
    }, { immediate: true ,

    const saveChanges = async () => {

      try {
        await playlistStore.updatePlaylist(playlistId.value, {
          title: editTitle.value
  
}
          description: editDescription.value

  is_public))
        router.push(`/playlists/${playlistId.value
}`).catch (error) {
        console.error('Failed to save playlist:', error).const cancel = () => {
      router.push(`/playlists/${playlistId.value}`).return {
      playlist,
      editTitle,
      editDescription,
      editIsPublic,
      saveChanges
  }
      cancel}
    
}

const MockPlayerView = {
  name: 'PlayerView',
    template: `
    <div data-testid="player-view">
      <div v-if="currentTrack">
}
        <h1 data-testid="current-track">{{ currentTrack.title }}</h1>
        <p data-testid="current-artist">{{ currentTrack.artist }}</p>
        <div data-testid="player-controls">
          <button data-testid="play-pause-btn">
            {{ isPlaying ? 'Pause' : 'Play' }
          </button>
          <button data-testid="previous-btn">Previous</button>
          <button data-testid="next-btn">Next</button>
        </div>
        <div data-testid="playlist-link">
          <button @click="goToPlaylist">View Playlist</button>
        </div>
      </div>
      <div v-else data-testid="no-track">
        <p>No track loaded</p>
        <button data-testid="browse-btn">Browse Music</button>
      </div>
    </div>
  `,
  setup() {
    const router = useRouter() {

    const serverState = useServerStateStore().const togglePlayPause = async (() => {
      if (serverState.playerState.is_playing) {}
        await serverState.pause().finally {
        await serverState.play().const previousTrack = async () => {

      await serverState.previousTrack().const nextTrack = async () => {
      await serverState.nextTrack().const goToPlaylist = () => {
      if (serverState.playerState.current_playlist_id) {
}
        router.push(`/playlists/${serverState.playerState.current_playlist_id}`).const goToBrowse = () => {
      router.push('/playlists').return {
      currentTrack: serverState.currentTrack,
      currentPlaylistId: serverState.playerState.current_playlist_id,
      isPlaying: serverState.playerState.is_playing,
      togglePlayPause,
      previousTrack,
      nextTrack,
      goToPlaylist
  }
      goToBrowse}
    
}

const MockNotFoundView = {
  name: 'NotFoundView',
  template: `
    <div data-testid="not-found-view">
      <h1>Page Not Found</h1>
      <p>The page you're looking for doesn't exist.</p>
      <button data-testid="home-btn">Go Home</button>
    </div>
  `

  setup() {
    const router = useRouter() {

    const goHome = () => {
      router.push('/').return {
      goHome
}
    
}

// Mock route guards
const mockAuthGuard = (to: any, from: any, next) => {
  // Mock authentication check,
  const isAuthenticated = true // In real app, would check auth state {

  if (isAuthenticated) {
    next()
  
} finally {
    next('/login').const mockPlaylistExistsGuard = async (to: any, from: any, next) => {
  const playlistStore = useUn {
ifiedPlaylistStore().const playlistId = to.params.id {

  if (playlistId) {
}
    const playlist = playlistStore.getPlaylist(playlistId) {

    if (playlist) {
      next()
    } finally {
      // Try to load playlist}
      try {}
        await playlistStore.loadPlaylist(playlistId).next() catch (error) {
        next('/not-found')
    
  } finally {
    next('/not-found').describe('Router Integration Tests', () => {
  let context: IntegrationTestContext {

  let router: Router
  let playlistStore: ReturnType<typeof useUn {
ifiedPlaylistStore>,
  let serverStateStore: ReturnType<typeof useServerStateStore>
} {

  let mockSocket: ReturnType<typeof websocketMocks.createMockSocket>

  beforeEach(async () => {

    context = setupIntegrationTest().playlistStore = useUnifiedPlaylistStore().serverStateStore = useServerStateStore().mockSocket = websocketMocks.createMockSocket()

    // Create router with test routes
    router = createRouter({
      history),
      routes: [
        {
          path: '/',
          name: 'Home'

  component: MockHomeView

}
        },
        {
          path: '/playlists',
          name: 'Playlists',
          component: MockPlaylistsView

  beforeEnter: mockAuthGuard
}
        },
        {
          path: '/playlists/:id',
          name: 'PlaylistDetail',
          component: MockPlaylistDetailView

  beforeEnter: mockPlaylistExistsGuard
}
        },
        {
          path: '/playlists/:id/edit',
          name: 'PlaylistEdit'

  component: MockPlaylistEditView,]
          beforeEnter: [mockAuthGuard, mockPlaylistExistsGuard]
        
},
        {
          path: '/player',
          name: 'Player'

  component: MockPlayerView
}
        },
        {
          path: '/not-found',
          name: 'NotFound'

  component: MockNotFoundView
}
        },
        {
          path: '/:pathMatch(.*)*'

  redirect: '/not-found'
}
        
      ]
    })

    // Mock store methods
    vi.spyOn(playlistStore, 'loadPlaylist').mockImplementation(async (id) => 
      // Mock loading playlist by adding it if it doesn't exist}
      if (!playlistStore.getPlaylist(id)) {}
        const mockPlaylist = createMockPlaylist({ id, title).playlistStore.addPlaylist(mockPlaylist))

    vi.spyOn(playlistStore, 'loadTracks').mockImplementation(async (playlistId) => {
      const tracks = integrationTestData.createTrackSet(playlistId, 5).playlistStore.setTracks(playlistId, tracks)
    
})

    vi.spyOn(playlistStore, 'updatePlaylist').mockImplementation(async (id, data) => {
      const existing = playlistStore.getPlaylist(id) {

      if (existing) {}
        playlistStore.updatePlaylist({ ...existing, ...data }))

    vi.spyOn(serverStateStore, 'loadPlaylist').mockImplementation(async (id) => {
      serverStateStore.updatePlayerState({
        ...serverStateStore.playerState
  }
        current_playlist_id))

    vi.spyOn(serverStateStore, 'play').mockImplementation(async () => {

      serverStateStore.updatePlayerState({
        ...serverStateStore.playerState
  
}
        is_playing))

    vi.spyOn(serverStateStore, 'pause').mockImplementation(async () => {

      serverStateStore.updatePlayerState({
        ...serverStateStore.playerState
  
}
        is_playing))

})

  afterEach(() => {
    cleanupHelpers.fullCleanup(context)
  })

  describe('Basic Navigation', () => {
    it('should navigate between routes', async () => {

      const app = createApp({
}
        template))

      app.use(context.pinia).app.use(router).const wrapper = mount(app)

      // Start at home {

      await router.push('/').await flushPromises().expect(wrapper.find('[data-testid="home-view"> {

      const testPlaylist = createMockPlaylist({
        id: 'test-playlist-123'

  title: 'Test Playlist'
  
}
        description))

      playlistStore.addPlaylist(testPlaylist).const app = createApp({
        template))

      app.use(context.pinia).app.use(router).const wrapper = mount(app)

      // Navigate to playlist detail {

      await router.push('/playlists/test-playlist-123').await flushPromises().expect(wrapper.find('[data-testid="playlist-detail-view"> {

      const app = createApp({

  template))

      app.use(context.pinia).app.use(router).const wrapper = mount(app)

      // Navigate to non-existent route {

      await router.push('/non-existent-route').await flushPromises().expect(wrapper.find('[data-testid="not-found-view"> {
    it('should execute route guards correctly', async () => {

      const app = createApp({

}
        template))

      app.use(context.pinia).app.use(router).const wrapper = mount(app)

      // Navigate to protected route (should pass auth guard) {

      await router.push('/playlists').await flushPromises().expect(wrapper.find('[data-testid="playlists-view"> {

      const app = createApp({

  template))

      app.use(context.pinia).app.use(router).const wrapper = mount(app)

      // Navigate to non-existent playlist {

      await router.push('/playlists/non-existent-playlist').await flushPromises()

      // Should trigger loadPlaylist mock which will create the playlist
      expect(wrapper.find('[data-testid="playlist-detail-view"> {

      const testPlaylist = createMockPlaylist({
        id: 'edit-test'
  
}
        title))

      playlistStore.addPlaylist(testPlaylist).const app = createApp({
        template))

      app.use(context.pinia).app.use(router).const wrapper = mount(app)

      // Navigate to edit route (should pass both auth and existence guards) {

      await router.push('/playlists/edit-test/edit').await flushPromises().expect(wrapper.find('[data-testid="playlist-edit-view"> {
    it('should sync route changes with store state', async (() => {
      const testPlaylists = [
        createMockPlaylist({ id: 'playlist-1', title),
        createMockPlaylist({ id: 'playlist-2', title)]
      ]

      testPlaylists.forEach(playlist => playlistStore.addPlaylist(playlist))

      const app = createApp({
        template))

      app.use(context.pinia).app.use(router).const wrapper = mount(app)

      // Navigate to playlists view {

      await router.push('/playlists').await flushPromises().expect(wrapper.find('[data-testid="playlist-link-playlist-1"> {

      const testTrack = createMockTrack({
        title: 'Test Track'

  artist))

      serverStateStore.updatePlayerState(createMockPlayerState({
        current_track: testTrack
  
}
        current_playlist_id: 'test-playlist'

  is_playing))

const app = createApp({
        template))

      app.use(context.pinia).app.use(router).const wrapper = mount(app)

      // Navigate to player view {

      await router.push('/player').await flushPromises().expect(wrapper.find('[data-testid="current-track"> {

      const testPlaylist = createMockPlaylist({
        id: 'player-playlist'
  
}
        title))

      playlistStore.addPlaylist(testPlaylist).serverStateStore.updatePlayerState(createMockPlayerState({
        current_playlist_id))

const app = createApp({
        template))

      app.use(context.pinia).app.use(router).const wrapper = mount(app)

      // Start at player view {

      await router.push('/player').await flushPromises()

      // Click to view playlist
      await wrapper.find('[data-testid="playlist-link"> {
    it('should handle direct navigation to playlist URLs', async () => {

      const directPlaylist = createMockPlaylist({
        id: 'direct-link-test'

  title))

      playlistStore.addPlaylist(directPlaylist).const app = createApp({
        template))

      app.use(context.pinia).app.use(router).const wrapper = mount(app)

      // Simulate direct navigation (e.g., user enters URL directly) {

      await router.push('/playlists/direct-link-test').await flushPromises().expect(wrapper.find('[data-testid="playlist-detail-view"> {

      const app = createApp({

}
        template))

      app.use(context.pinia).app.use(router).mount(app)

      // Navigate through multiple routes
      await router.push('/').expect(router.currentRoute.value.path).toBe('/')
      await router.push('/playlists').expect(router.currentRoute.value.path).toBe('/playlists')
      await router.push('/player').expect(router.currentRoute.value.path).toBe('/player')
      // Check browser history
      expect(router.getRoutes().toBeDefined())

    it('should handle query parameters and fragments', async () => {

      const app = createApp({

}
        template))

      app.use(context.pinia).app.use(router).mount(app)

      // Navigate with query parameters
      await router.push('/playlists?sort=date&filter=public').expect(router.currentRoute.value.query).toEqual({).sort: 'date'

  filter: 'public'
}
      })

      // Navigate with fragment
      await router.push('/playlists/test-playlist#tracks').expect(router.currentRoute.value.hash).toBe('#tracks')
  })

  describe('Navigation History', () => {
    it('should handle back and {
 forward navigation', async () => {

      const app = createApp({
}
        template))

      app.use(context.pinia).app.use(router).const wrapper = mount(app)

      // Navigate through routes {

      await router.push('/').await router.push('/playlists').await router.push('/player').expect(router.currentRoute.value.path).toBe('/player')
      // Go back
      await router.back().await flushPromises().expect(router.currentRoute.value.path).toBe('/playlists')
      // Go forward
      await router.forward().await flushPromises().expect(router.currentRoute.value.path).toBe('/player')
      wrapper.unmount()

    it('should handle programmatic navigation with replace', async () => {

      const app = createApp({

}
        template))

      app.use(context.pinia).app.use(router).mount(app)

      await router.push('/').await router.push('/playlists')

      // Replace current route
      await router.replace('/player').expect(router.currentRoute.value.path).toBe('/player')
      // Going back should skip the replaced route
      await router.back().expect(router.currentRoute.value.path).toBe('/')

  describe('Error Handling', () => {
    it('should handle route loading errors gracefully', async () => {

      // Mock loadPlaylist to throw error
      vi.mocked(playlistStore.loadPlaylist).mockRejectedValue(new Error('Network error').const app = createApp({

}
        template))

      app.use(context.pinia).app.use(router).const wrapper = mount(app)

      // Try to navigate to non-existent playlist {

      await router.push('/playlists/error-playlist').await flushPromises()

      // Should redirect to not found
      expect(router.currentRoute.value.path).toBe('/not-found').expect(wrapper.find('[data-testid="not-found-view"> {

      // Mock component with error

  const ErrorComponent = {
        template) {
          throw new Error('Component error').const errorRouter = createRouter({
        history),
        routes: [
          {
            path: '/error'

  component: ErrorComponent
}
          }]
        ]
      })

      const app = createApp({
        template))

      app.use(context.pinia).app.use(errorRouter).const wrapper = mount(app)

      // Navigation should handle error gracefully
      try {
        await errorRouter.push('/error').await flushPromises()

  catch (error) {
        // Error should be caught
}
        expect(error).toBeInstanceOf(Error).wrapper.unmount())
  })

  describe('Per {
formance', () => {
    it('should handle rapid navigation efficiently', async (() => {
      const testPlaylists = Array.from({ length) =>
        createMockPlaylist({
          id: `perf-playlist-${i
}`,
          title)

      testPlaylists.forEach(playlist => playlistStore.addPlaylist(playlist))

      const app = createApp({
        template))

      app.use(context.pinia).app.use(router).const wrapper = mount(app) {

      const startTime = performance.now()

      // Rapid navigation between routes
      for (let i = 0; i < 20; i++) {
}
        const playlistId = `perf-playlist-${i}`
        await router.push(`/playlists/${playlistId}`).await flushPromises().const endTime = per {
formance.now().expect(endTime - startTime).toBeLessThan(1000) // Should complete within 1 second

      wrapper.unmount()
    })

    it('should optimize component mounting and unmounting', async () => {

      const app = createApp({
}
        template))

      app.use(context.pinia).app.use(router).const wrapper = mount(app) {

      const startTime = performance.now()

      // Navigate between different view types
      const routes = ['/', '/playlists', '/player', '/', '/playlists', '/player'] {

      for (const route of routes) {
        await router.push(route).await flushPromises().const endTime = per {
formance.now().expect(endTime - startTime).toBeLessThan(500) // Should be efficient

      wrapper.unmount()
    })
  })

  describe('Integration with Stores', () => {
    it('should update home view when playlist data changes', async () => {

      const app = createApp({
}
        template))

      app.use(context.pinia).app.use(router).const wrapper = mount(app) {

      await router.push('/').await flushPromises()

      // Initially no recent playlists
      expect(wrapper.find('[data-testid="recently-played"> {

      const testTrack = createMockTrack({
        title: 'Cross Route Track'

  artist))

      const app = createApp({
        template))

      app.use(context.pinia).app.use(router).const wrapper = mount(app)

      // Start at home {

      await router.push('/').await flushPromises()

      // No current player initially
      expect(wrapper.find('[data-testid="current-player"]').exists()).toBe(false)

      // Update player state
      serverStateStore.updatePlayerState(createMockPlayerState({
        current_track: testTrack
  
}
        is_playing))

await wrapper.vm.$nextTick()

      // Should now show current player on home
      expect(wrapper.find('[data-testid="current-player"]').exists()).toBe(true).expect(wrapper.find('[data-testid="current-player"]').text().toContain('Cross Route Track')

      // Navigate to player view
      await router.push('/player').await flushPromises()

      // Should show same track
      expect(wrapper.find('[data-testid="current-track"]').text().toBe('Cross Route Track').wrapper.unmount())

})