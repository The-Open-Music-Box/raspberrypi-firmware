import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { i18n } from './i18n'
import './registerServiceWorker'
import router from './router'
import './assets/tailwind.css'
import './assets/modern-theme.css'
import socketService from './services/socketService'
import { useServerStateStore } from './stores/serverStateStore'

const app = createApp(App)
const pinia = createPinia()

// Install Pinia before using any stores
app.use(pinia)

// Socket.IO connection is initialized automatically in socketService

// Initialize server state store to wire socket events and subscribe to playlists
const serverStateStore = useServerStateStore()
void serverStateStore

// Add Socket.IO service to Vue global properties
app.config.globalProperties.$socketService = socketService
app.use(i18n)
app.use(router).mount('#app')
