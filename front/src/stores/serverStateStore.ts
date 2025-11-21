import { defineStore } from 'pinia'
import { ref, reactive, readonly, computed } from 'vue'
import socketService from '@/services/socketService'
import { SOCKET_EVENTS } from '@/constants/apiRoutes'
import { logger } from '@/utils/logger'
import type { Track } from '@/components/files/types'
import { getTrackNumber, filterTracksByNumbers } from '@/utils/trackFieldAccessor'

interface Playlist {
  id: string
  title: string
  description: string
  nfc_tag_id?: string
  tracks: Track[]
  track_count: number
  created_at?: string
  updated_at?: string
}

interface StateEvent {
  event_type: string
  server_seq: number
  playlist_id?: string
  data: unknown
  timestamp: number
  event_id: string
}

interface PlayerState {
  is_playing: boolean
  active_playlist_id: string | null
  active_playlist_title: string | null
  active_track_id: string | null
  active_track: {
    id?: string
    title: string
    filename: string
    duration_ms?: number
    file_path?: string
  } | null
  position_ms: number
  duration_ms: number
  track_index: number
  track_count: number
  can_prev: boolean
  can_next: boolean
  volume?: number
  muted?: boolean
  state?: string
  server_seq: number
}

interface OperationAck {
  client_op_id: string
  data?: Partial<PlayerState>
  error?: string
}

interface PlaylistIndexUpdate {
  type: 'create' | 'update' | 'delete'
  id?: string
  playlist?: Playlist
}

type StateEventDetail = StateEvent | PlayerState | Playlist | Track | {
  playlists?: Playlist[]
  playlist?: Playlist
  track?: Track
  playlist_id?: string
  track_numbers?: number[]
  volume?: number
  updates?: PlaylistIndexUpdate[]
  [key: string]: unknown
}

export const useServerStateStore = defineStore('serverState', () => {
  // Reactive state
  const playlists = ref<Playlist[]>([])
  const currentPlaylist = ref<Playlist | null>(null)
  const playerState = ref<PlayerState>({
    is_playing: false,
    state: undefined,
    active_playlist_id: null,
    active_playlist_title: null,
    active_track_id: null,
    active_track: null,
    position_ms: 0,
    duration_ms: 0,
    track_index: 0,
    track_count: 0,
    can_prev: false,
    can_next: false,
    volume: undefined,
    muted: undefined,
    server_seq: 0
  })
  const globalSequence = ref(0)
  const playlistSequences = reactive<Record<string, number>>({})
  const isConnected = ref(false)
  const isReconnecting = ref(false)

  // Clean architecture - using only real-time WebSocket state management

  // Client operation tracking for deduplication
  const pendingOperations = reactive<Set<string>>(new Set())

  // Player state monitoring for proactive sync
  let playerStateCheckInterval: ReturnType<typeof setInterval> | null = null
  const PLAYER_STATE_CHECK_INTERVAL = 5000 // 5 seconds

  // Computed getters
  const getPlaylistById = computed(() => (id: string) =>
    playlists.value.find(p => p.id === id)
  )

  const getPlaylistSequence = computed(() => (id: string) =>
    playlistSequences[id] || 0
  )

  // Simplified getters - paginated index removed

  // Connection + event wiring to RealSocketService
  function setupEventHandlers() {
    // Connection events from socket service
    socketService.on('connect', () => {
      isConnected.value = true
      isReconnecting.value = false
      logger.info('🔊🎵 ✅ CONNECTED TO SERVER (via SocketService)', {}, 'ServerState')

      // Subscribe to playlists room after connection is established
      const subscribeSuccess = subscribeToPlaylists()
      logger.info('🔊🎵 [ServerState] Subscription result:', { success: subscribeSuccess })

      // Request state resync after reconnection or initial connect
      requestStateSync()

      // ADDITION: Request current player status to initialize playerState
      logger.info('🔊🎵 [ServerState] Requesting initial player state on connect...')
      requestInitialPlayerState()

      // Start proactive player state monitoring
      startPlayerStateMonitoring()
    })

    socketService.on('disconnect', () => {
      isConnected.value = false
      logger.info('Disconnected from server (via SocketService)', {}, 'ServerState')
      
      // Stop proactive monitoring when disconnected
      stopPlayerStateMonitoring()
    })

    socketService.on('reconnect', () => {
      isReconnecting.value = false
      logger.info('Reconnected to server (via SocketService)', {}, 'ServerState')

      // Re-subscribe to playlists room after reconnection
      subscribeToPlaylists()

      requestStateSync()

      // ADDITION: Re-request player status after reconnection
      requestInitialPlayerState()

      // Restart proactive monitoring after reconnection
      startPlayerStateMonitoring()
    })

    socketService.on('reconnecting', () => {
      isReconnecting.value = true
      logger.info('Reconnecting to server... (via SocketService)', {}, 'ServerState')
    })

    // Listen to DOM events dispatched by socketService.notifyStateUpdate()
    // These events are dispatched from setupStateListeners in socketService
    logger.info('🔊 Setting up DOM event listeners for server state...', {}, 'ServerState')

    window.addEventListener('state:playlists', (e: Event) => {
      logger.info('🔊 DOM event state:playlists received', {}, 'ServerState')
      handlePlaylistsSnapshot((e as CustomEvent<StateEventDetail>).detail)
    })
    window.addEventListener('state:playlist', (e: Event) => handlePlaylistSnapshot((e as CustomEvent<StateEvent>).detail))
    window.addEventListener('state:track', (e: Event) => handleTrackSnapshot((e as CustomEvent<StateEvent>).detail))
    window.addEventListener('state:player', (e: Event) => handlePlayerState((e as CustomEvent<StateEvent | PlayerState>).detail))
    window.addEventListener('state:track_progress', (e: Event) => handleTrackProgress((e as CustomEvent<StateEvent>).detail))
    let trackPositionLogged = false
    window.addEventListener('state:track_position', (e: Event) => {
      if (!trackPositionLogged) {
        logger.info('🔊 DOM event state:track_position received for first time!', (e as CustomEvent<StateEvent>).detail, 'ServerState')
        trackPositionLogged = true
      }
      handleTrackPosition((e as CustomEvent<StateEvent>).detail)
    })

    // Specific action events for enhanced UX - also via DOM events
    window.addEventListener('state:playlist_deleted', (e: Event) => handlePlaylistDeleted((e as CustomEvent<StateEvent>).detail))
    window.addEventListener('state:playlist_created', (e: Event) => handlePlaylistCreated((e as CustomEvent<StateEvent>).detail))
    window.addEventListener('state:playlist_updated', (e: Event) => handlePlaylistUpdated((e as CustomEvent<StateEvent>).detail))
    window.addEventListener('state:track_deleted', (e: Event) => handleTrackDeleted((e as CustomEvent<StateEvent>).detail))
    window.addEventListener('state:track_added', (e: Event) => handleTrackAdded((e as CustomEvent<StateEvent>).detail))
    window.addEventListener('state:playlists_index_update', (e: Event) => handlePlaylistsIndexUpdate((e as CustomEvent<StateEvent>).detail))

    // System state events
    window.addEventListener('state:volume_changed', (e: Event) => handleVolumeChanged((e as CustomEvent<StateEvent>).detail))
    window.addEventListener('state:nfc_state', (e: Event) => handleNFCState((e as CustomEvent<StateEvent>).detail))

    // Upload events - handled by dedicated upload components

    // Operation acknowledgments - these still come directly via socket
    socketService.on(SOCKET_EVENTS.ACK_OP, (ack: OperationAck) => handleOperationSuccess(ack))
    socketService.on(SOCKET_EVENTS.ERR_OP, (ack: OperationAck) => handleOperationError(ack))
  }

  // Subscription management
  function subscribeToPlaylists() {
    if (socketService.isConnected()) {
      socketService.emit('join:playlists', {})
      logger.info('🔊🎵 [ServerState] ✅ SUBSCRIBED TO PLAYLISTS ROOM (for player events)')
      return true
    } else {
      logger.warn('🔊🎵 [ServerState] ❌ CANNOT SUBSCRIBE TO PLAYLISTS - SOCKET NOT CONNECTED')

      // Auto-retry after a short delay if not connected
      setTimeout(() => {
        if (socketService.isConnected()) {
          logger.info('🔊🎵 [ServerState] ♻️ Retrying subscription after connection established...')
          subscribeToPlaylists()
        }
      }, 500)
      return false
    }
  }

  function subscribeToPlaylist(playlistId: string) {
    if (socketService.isConnected()) {
      socketService.emit('join:playlist', { playlist_id: playlistId })
      logger.debug(`[ServerState] Subscribed to playlist room: ${playlistId}`)
    } else {
      logger.warn(`[ServerState] Cannot subscribe to playlist ${playlistId} - socket not connected`)
    }
  }

  function unsubscribeFromPlaylist(playlistId: string) {
    if (socketService.isConnected()) {
      socketService.emit('leave:playlist', { playlist_id: playlistId })
      logger.debug(`[ServerState] Unsubscribed from playlist room: ${playlistId}`)
    } else {
      logger.warn(`[ServerState] Cannot unsubscribe from playlist ${playlistId} - socket not connected`)
    }
  }

  // Clean architecture - paginated index handlers removed

  // State event handlers
  function handlePlaylistsSnapshot(event: StateEventDetail) {
    logger.debug('[ServerState] Received playlists snapshot', event)
    // Handle both wrapped and direct data formats
    let playlistsData: Playlist[] = []
    if ('data' in event && event.data && typeof event.data === 'object' && 'playlists' in event.data) {
      // Standard format: event.data.playlists
      playlistsData = (event.data as { playlists: Playlist[] }).playlists
    } else if ('playlists' in event && Array.isArray(event.playlists)) {
      // Direct format: event.playlists (from fallback)
      playlistsData = event.playlists
    }
    playlists.value = playlistsData || []
    globalSequence.value = ('server_seq' in event && typeof (event as { server_seq?: number }).server_seq === 'number')
      ? (event as { server_seq: number }).server_seq
      : 0
  }

  function handlePlaylistSnapshot(event: StateEvent) {
    logger.debug('[ServerState] Received playlist snapshot', event)
    const playlist = event.data as Playlist
    if (playlist) {
      updatePlaylistInList(playlist)
      if (currentPlaylist.value?.id === playlist.id) {
        currentPlaylist.value = playlist
      }
    }
    globalSequence.value = event.server_seq
    if (event.playlist_id) {
      const data = event.data as { playlist_seq?: number }
      playlistSequences[event.playlist_id] = data.playlist_seq || 0
    }
  }

  function handleTrackSnapshot(event: StateEvent) {
    logger.debug('[ServerState] Received track snapshot', event)
    // Track changes are embedded in playlist updates
    // This handler ensures we process any track-specific state changes
    const data = event.data as { playlist?: Playlist; playlist_seq?: number }
    if (event.playlist_id && data.playlist) {
      const playlist = data.playlist
      updatePlaylistInList(playlist)
      if (currentPlaylist.value?.id === playlist.id) {
        currentPlaylist.value = playlist
      }
      playlistSequences[event.playlist_id] = data.playlist_seq || 0
    }
    globalSequence.value = event.server_seq
  }

  function handlePlayerState(event: StateEvent | PlayerState) {
    logger.info('🔊🎵 [ServerState] PLAYER STATE EVENT RECEIVED', event)
    logger.info('🔊🎵 [ServerState] Current playerState before update:', JSON.parse(JSON.stringify(playerState.value)))

    // Handle both direct PlayerState and StateEvent wrapper
    // StateEvent has structure: { event_type, server_seq, data: {...actual player state...} }
    // Direct PlayerState has structure: { is_playing, active_track, ... }
    let stateData: Partial<PlayerState> | null = null
    let serverSeq: number | undefined

    if ('event_type' in event && (event as StateEvent).event_type === 'state:player') {
      // This is a StateEvent wrapper from socket
      stateData = (event as StateEvent).data as Partial<PlayerState>
      serverSeq = (event as StateEvent).server_seq
      logger.debug('[ServerState] Extracting from StateEvent wrapper:', {
        event_type: (event as StateEvent).event_type,
        server_seq: serverSeq,
        data_keys: Object.keys(stateData || {}),
        active_track: stateData?.active_track?.title || 'none'
      })
    } else if ('data' in event && typeof event.data === 'object') {
      // This might be another wrapper format
      stateData = event.data as Partial<PlayerState>
      serverSeq = ('server_seq' in event ? (event as { server_seq: number }).server_seq : undefined)
      logger.debug('[ServerState] Extracting from data wrapper:', {
        has_data: true,
        server_seq: serverSeq,
        data_keys: Object.keys(stateData || {})
      })
    } else {
      // Direct PlayerState object
      stateData = event as Partial<PlayerState>
      serverSeq = ('server_seq' in event ? (event as { server_seq: number }).server_seq : undefined)
      logger.debug('[ServerState] Using direct PlayerState:', {
        direct: true,
        keys: Object.keys(stateData || {})
      })
    }

    logger.debug('[ServerState] Processing state data:', {
      raw_stateData: stateData,
      is_playing: stateData?.is_playing,
      active_playlist_title: stateData?.active_playlist_title,
      active_track: stateData?.active_track,
      duration_ms: stateData?.duration_ms,
      position_ms: stateData?.position_ms,
      track_index: stateData?.track_index,
      track_count: stateData?.track_count
    })

    // Update player state with data from backend
    if (stateData) {
      const oldPlayingState = playerState.value.is_playing
      const newPlayingState = Boolean(stateData.is_playing)

      // Track if playlist ID is changing
      const oldPlaylistId = playerState.value.active_playlist_id
      const newPlaylistId = stateData.active_playlist_id

      playerState.value = {
        is_playing: newPlayingState,
        active_playlist_id: newPlaylistId ?? null,
        active_playlist_title: stateData.active_playlist_title ?? null,
        active_track_id: stateData.active_track_id ?? null,
        active_track: stateData.active_track ?? null,
        position_ms: stateData.position_ms || 0,
        duration_ms: stateData.duration_ms || 0,
        track_index: stateData.track_index || 0,
        track_count: stateData.track_count || 0,
        can_prev: Boolean(stateData.can_prev),
        can_next: Boolean(stateData.can_next),
        volume: stateData.volume,
        server_seq: serverSeq || stateData.server_seq || 0
      }

      // Log playlist changes for debugging the FileListContainer warning
      if (oldPlaylistId !== newPlaylistId) {
        logger.info('[ServerState] 🔄 PLAYLIST ID CHANGED:', {
          from: oldPlaylistId || 'none',
          to: newPlaylistId || 'none',
          playlist_title: stateData.active_playlist_title || 'none',
          timestamp: new Date().toISOString()
        })
      }

      // ADDITION: Debug log for play/pause button state changes
      if (oldPlayingState !== newPlayingState) {
        logger.debug('🎯 [ServerState] PLAY/PAUSE STATE CHANGED:', {
          from: oldPlayingState,
          to: newPlayingState,
          source_data_is_playing: stateData.is_playing,
          boolean_conversion: Boolean(stateData.is_playing)
        })
      }

      logger.debug('[ServerState] Player state successfully updated:', {
        is_playing: playerState.value.is_playing,
        active_playlist_id: playerState.value.active_playlist_id,
        has_track: !!playerState.value.active_track,
        track_title: playerState.value.active_track?.title,
        playlist_title: playerState.value.active_playlist_title,
        duration_ms: playerState.value.duration_ms,
        position_ms: playerState.value.position_ms,
        timestamp: new Date().toISOString()
      })

      // Special logging for playlist changes
      if (stateData.active_playlist_id) {
        logger.info('[ServerState] ✅ PLAYLIST STATE UPDATE:', {
          active_playlist_id: stateData.active_playlist_id,
          active_playlist_title: stateData.active_playlist_title,
          is_playing: stateData.is_playing,
          source: 'WebSocket state:player event',
          server_seq: serverSeq,
          timestamp: new Date().toISOString()
        })
      }
    } else {
      logger.error('[ServerState] No valid state data found in event:', event)
    }

    // Update global sequence if available
    if (serverSeq) {
      globalSequence.value = serverSeq
    }
  }

  function handleTrackProgress(event: StateEvent) {
    // Comment out to reduce console spam - track progress events are too frequent
    // logger.debug('[ServerState] Track progress', event)
    const data = event.data as { position_ms?: number; duration_ms?: number; track_info?: { id: string; title?: string; filename: string } }
    if (typeof data?.position_ms === 'number') {
      // Update only the position; do not change playing flags here
      playerState.value.position_ms = data.position_ms

      // Also update duration if provided
      if (typeof data?.duration_ms === 'number' && data.duration_ms > 0) {
        playerState.value.duration_ms = data.duration_ms
      }

      // Update track info if provided in progress event
      if (data.track_info) {
        playerState.value.active_track = {
          id: data.track_info.id,
          title: data.track_info.title || data.track_info.filename,
          filename: data.track_info.filename
        }
      }
    }
    if (event.server_seq) {
      globalSequence.value = event.server_seq
    }
  }

  // Debug counters for handleTrackPosition
  let firstPositionLogged = false
  let positionLogCounter = 0

  function handleTrackPosition(event: StateEvent) {
    // Lightweight position-only updates with strategic logging
    const data = event.data as { position_ms?: number; duration_ms?: number; is_playing?: boolean; track_id?: string }

    // Log first event for debugging and every subsequent event for a few seconds
    if (!firstPositionLogged) {
      logger.info('🎵 FIRST state:track_position received:', data, 'ServerState')
      firstPositionLogged = true
    }


    if (typeof data?.position_ms === 'number') {
      const oldPosition = playerState.value.position_ms
      playerState.value.position_ms = data.position_ms


      // Log position changes periodically (every 5 seconds at 1000ms interval)
      positionLogCounter++

      if (positionLogCounter % 25 === 0) {  // Reduce logging frequency
        logger.debug(`🎵 Position update #${positionLogCounter}: ${data.position_ms}ms (was ${oldPosition}ms)`, {}, 'ServerState')
      }

      // Update is_playing if provided (track_position events include this for accuracy)
      if (typeof data?.is_playing === 'boolean') {
        playerState.value.is_playing = data.is_playing
      }

      // Update duration if provided
      if (typeof data?.duration_ms === 'number' && data.duration_ms > 0) {
        playerState.value.duration_ms = data.duration_ms
      }

      // Update active track ID if provided (for consistency)
      if (data?.track_id && data.track_id !== playerState.value.active_track_id) {
        playerState.value.active_track_id = data.track_id
      }
    }

    // Update global sequence
    if (event.server_seq) {
      globalSequence.value = event.server_seq
    }
  }

  function handleOperationSuccess(ack: OperationAck) {
    logger.debug('[ServerState] Operation success', ack)
    pendingOperations.delete(ack.client_op_id)

    // IMPROVEMENT: Apply acknowledgment data to player state for immediate UI update
    if (ack.data && (ack.data.is_playing !== undefined || ack.data.active_track)) {
      logger.debug('[ServerState] Applying ack data to player state for immediate update')

      const stateData = ack.data
      const oldPlayingState = playerState.value.is_playing
      const newPlayingState = Boolean(stateData.is_playing)

      playerState.value = {
        is_playing: newPlayingState,
        active_playlist_id: stateData.active_playlist_id ?? null,
        active_playlist_title: stateData.active_playlist_title ?? null,
        active_track_id: stateData.active_track_id ?? null,
        active_track: stateData.active_track ?? null,
        position_ms: stateData.position_ms || 0,
        duration_ms: stateData.duration_ms || 0,
        track_index: stateData.track_index || 0,
        track_count: stateData.track_count || 0,
        can_prev: Boolean(stateData.can_prev),
        can_next: Boolean(stateData.can_next),
        volume: stateData.volume,
        server_seq: stateData.server_seq || 0
      }

      if (oldPlayingState !== newPlayingState) {
        logger.debug('🎯 [ServerState] PLAY/PAUSE STATE CHANGED FROM ACK:', {
          from: oldPlayingState,
          to: newPlayingState
        })
      }
    }
  }

  function handleOperationError(ack: OperationAck) {
    logger.error('[ServerState] Operation error', ack)
    pendingOperations.delete(ack.client_op_id)
  }

  // Specific action event handlers
  function handlePlaylistDeleted(event: StateEvent) {
    logger.debug('[ServerState] Playlist deleted', event)
    // Handle both event.data.playlist_id and event.playlist_id structures
    const data = event.data as { playlist_id?: string }
    const playlistId = data?.playlist_id || event.playlist_id
    if (playlistId) {
      // Remove from playlists array
      const index = playlists.value.findIndex(p => p.id === playlistId)
      if (index >= 0) {
        playlists.value.splice(index, 1)
        logger.debug(`[ServerState] Removed playlist ${playlistId} from local state`)
      }

      // Simplified architecture - paginated index removal logic removed

      // Clear current playlist if it was the deleted one
      if (currentPlaylist.value?.id === playlistId) {
        currentPlaylist.value = null
      }

      // Clean up playlist sequences
      delete playlistSequences[playlistId]
    }
    globalSequence.value = event.server_seq
  }

  function handlePlaylistCreated(event: StateEvent) {
    logger.info('🔊 [ServerState] Playlist created event received', event)
    const data = event.data as { playlist?: Playlist }
    const playlist = data?.playlist
    if (playlist) {
      // Add to playlists array if not already present
      const existingIndex = playlists.value.findIndex(p => p.id === playlist.id)
      if (existingIndex === -1) {
        playlists.value.push(playlist)
        logger.info(`🔊 [ServerState] Added playlist ${playlist.id} to local state (${playlists.value.length} total)`)
      } else {
        logger.info(`🔊 [ServerState] Playlist ${playlist.id} already exists in local state`)
      }
    } else {
      logger.warn(`🔊 [ServerState] No playlist data in creation event`, event)
    }
    globalSequence.value = event.server_seq
  }

  function handlePlaylistUpdated(event: StateEvent) {
    logger.debug('[ServerState] Playlist updated', event)
    const data = event.data as { playlist?: Playlist; playlist_seq?: number }
    const playlist = data?.playlist
    if (playlist) {
      updatePlaylistInList(playlist)
      if (currentPlaylist.value?.id === playlist.id) {
        currentPlaylist.value = playlist
      }
    }
    globalSequence.value = event.server_seq
    if (event.playlist_id) {
      playlistSequences[event.playlist_id] = data?.playlist_seq || 0
    }
  }

  function handleTrackDeleted(event: StateEvent) {
    logger.debug('[ServerState] Track deleted', event)
    const data = event.data as { playlist_id?: string; track_numbers?: number[]; playlist_seq?: number }
    const playlistId = data?.playlist_id
    const trackNumbers = data?.track_numbers

    if (playlistId && trackNumbers && Array.isArray(trackNumbers)) {
      const playlist = playlists.value.find(p => p.id === playlistId)
      if (playlist && playlist.tracks) {
        // Use trackFieldAccessor helper for unified field access
        playlist.tracks = filterTracksByNumbers(playlist.tracks, trackNumbers)
        logger.debug(`[ServerState] Removed ${trackNumbers.length} tracks from playlist ${playlistId}`)
      }

      if (currentPlaylist.value?.id === playlistId && currentPlaylist.value?.tracks) {
        currentPlaylist.value.tracks = filterTracksByNumbers(currentPlaylist.value.tracks, trackNumbers)
      }
    }

    globalSequence.value = event.server_seq
    if (playlistId) {
      playlistSequences[playlistId] = data?.playlist_seq || 0
    }
  }

  function handleTrackAdded(event: StateEvent) {
    logger.debug('[ServerState] Track added', event)
    const data = event.data as { playlist_id?: string; track?: Track; playlist_seq?: number }
    const playlistId = data?.playlist_id
    const track = data?.track

    if (playlistId && track) {
      const playlist = playlists.value.find(p => p.id === playlistId)
      if (playlist) {
        if (!playlist.tracks) {
          playlist.tracks = []
        }
        // Add track if not already present
        const trackNumber = getTrackNumber(track)
        if (!playlist.tracks.find(t => getTrackNumber(t) === trackNumber)) {
          playlist.tracks.push(track)
          // Sort tracks by number to maintain order
          playlist.tracks.sort((a, b) => getTrackNumber(a) - getTrackNumber(b))
          logger.debug(`[ServerState] Added track ${trackNumber} to playlist ${playlistId}`)
        }
      }

      if (currentPlaylist.value && currentPlaylist.value.id === playlistId) {
        if (!currentPlaylist.value.tracks) {
          currentPlaylist.value.tracks = []
        }
        const trackNumber = getTrackNumber(track)
        if (currentPlaylist.value.tracks && !currentPlaylist.value.tracks.find(t => getTrackNumber(t) === trackNumber)) {
          currentPlaylist.value.tracks.push(track)
          currentPlaylist.value.tracks.sort((a, b) => getTrackNumber(a) - getTrackNumber(b))
        }
      }
    }

    globalSequence.value = event.server_seq
    if (playlistId) {
      playlistSequences[playlistId] = data?.playlist_seq || 0
    }
  }

  function handlePlaylistsIndexUpdate(event: StateEvent) {
    logger.debug('[ServerState] Playlists index update', event)
    // Handle paginated playlist updates
    const updates = (event.data as { updates?: PlaylistIndexUpdate[] })?.updates
    if (updates && Array.isArray(updates)) {
      updates.forEach((update: PlaylistIndexUpdate) => {
        if (update.type === 'delete' && update.id) {
          const index = playlists.value.findIndex(p => p.id === update.id)
          if (index >= 0) {
            playlists.value.splice(index, 1)
            logger.debug(`[ServerState] Removed playlist ${update.id} from index update`)
          }
        } else if (update.type === 'create' && update.playlist) {
          const playlist = update.playlist
          const existingIndex = playlists.value.findIndex(p => p.id === playlist.id)
          if (existingIndex === -1) {
            playlists.value.push(playlist)
            logger.debug(`[ServerState] Added playlist ${playlist.id} from index update`)
          }
        } else if (update.type === 'update' && update.playlist) {
          updatePlaylistInList(update.playlist)
          logger.debug(`[ServerState] Updated playlist ${update.playlist.id} from index update`)
        }
      })
    }

    globalSequence.value = event.server_seq
  }

  function handleVolumeChanged(event: StateEvent) {
    logger.debug('[ServerState] Volume changed', event)
    const data = event.data as { volume?: number }
    const volume = data?.volume
    if (volume !== undefined && playerState.value) {
      playerState.value.volume = volume
      logger.debug(`[ServerState] Updated volume to ${volume}`)
    }
    globalSequence.value = event.server_seq
  }

  function handleNFCState(event: StateEvent) {
    logger.debug('[ServerState] NFC state changed', event)
    // Handle NFC state updates - could be used for UI indicators
    // The event.data should contain NFC status information
    globalSequence.value = event.server_seq
  }

  // Helper functions
  function updatePlaylistInList(playlist: Playlist) {
    const index = playlists.value.findIndex(p => p.id === playlist.id)
    if (index >= 0) {
      playlists.value[index] = playlist
      logger.debug(`[ServerState] Updated playlist ${playlist.id} in local state (${playlist.tracks?.length || 0} tracks)`)
    } else {
      // Playlist not found, add it to the beginning
      playlists.value.unshift(playlist)
      logger.debug(`[ServerState] Added new playlist ${playlist.id} to local state (${playlist.tracks?.length || 0} tracks)`)
    }
  }


  function requestStateSync() {
    if (socketService.isConnected()) {
      logger.debug('[ServerState] 🔄 Requesting state sync - current state:', {
        globalSequence: globalSequence.value,
        playlistSequences: { ...playlistSequences },
        currentPlayerState: JSON.parse(JSON.stringify(playerState.value)),
        isConnected: isConnected.value
      })

      socketService.emit(SOCKET_EVENTS.SYNC_REQUEST, {
        last_global_seq: globalSequence.value,
        last_playlist_seqs: { ...playlistSequences }
      })
      logger.debug('[ServerState] State sync request sent')
    } else {
      logger.warn('[ServerState] Cannot request state sync - socket not connected')
    }
  }

  // Manual sync method for when WebSocket events are not working
  function manualSync(playlistsData: Playlist[]) {
    logger.debug('[ServerState] Manual sync - updating playlists', playlistsData.length)
    playlists.value = playlistsData
  }

  // ADDITION: Request initial player state from server
  async function requestInitialPlayerState() {
    try {
      logger.info('🔊🎵 [ServerState] REQUESTING INITIAL PLAYER STATE...')

      // Import API service dynamically to avoid circular dependencies
      const { default: apiService } = await import('@/services/apiService')

      // Call the /player/status endpoint
      const response = await apiService.getPlayerStatus()

      if (response && typeof response === 'object') {
        logger.info('🔊🎵 [ServerState] ✅ RECEIVED INITIAL PLAYER STATE:', {
          has_active_track: !!response.active_track,
          active_playlist_id: response.active_playlist_id || 'none',
          active_playlist_title: response.active_playlist_title || 'none',
          is_playing: response.is_playing,
          track_title: response.active_track?.title || 'none',
          source: 'HTTP /api/player/status',
          timestamp: new Date().toISOString()
        })

        // Backend now returns PlayerState directly, so pass it directly to handler
        // The handlePlayerState function can handle both direct PlayerState and StateEvent wrapper
        handlePlayerState(response as PlayerState)

        // Log the resulting state after processing
        logger.info('🔊🎵 [ServerState] Player state after processing:', {
          is_playing: playerState.value.is_playing,
          has_active_track: !!playerState.value.active_track,
          active_track_title: playerState.value.active_track?.title || 'none',
          active_playlist_title: playerState.value.active_playlist_title || 'none',
          position_ms: playerState.value.position_ms,
          duration_ms: playerState.value.duration_ms
        })
      } else {
        logger.warn('🔊🎵 [ServerState] ⚠️️ Invalid player status response:', response)
      }
    } catch (error) {
      logger.error('[ServerState] ❌ Failed to fetch initial player state:', error)

      // If the API call fails, the player state will remain empty
      // This is acceptable as the state will be updated when the user interacts with the player
    }
  }

  // Proactive player state monitoring
  function startPlayerStateMonitoring() {
    if (playerStateCheckInterval) {
      clearInterval(playerStateCheckInterval)
    }
    
    logger.info('🔄 [ServerState] Starting proactive player state monitoring')
    
    playerStateCheckInterval = setInterval(async () => {
      try {
        // Check if we should request fresh player state
        const shouldSync = (
          // No active track but we might be playing
          (!playerState.value.active_track && !playerState.value.active_playlist_id) ||
          // Socket is connected but no position updates in a while
          (isConnected.value && !playerState.value.is_playing && playerState.value.active_playlist_id) ||
          // We have a playlist but no track info
          (playerState.value.active_playlist_id && !playerState.value.active_track)
        )

        if (shouldSync && isConnected.value) {
          logger.info('🔄 [ServerState] Proactive sync - requesting fresh player state')
          await requestInitialPlayerState()
        }
      } catch (error) {
        logger.error('[ServerState] Error in proactive player state check:', error)
      }
    }, PLAYER_STATE_CHECK_INTERVAL)
  }

  function stopPlayerStateMonitoring() {
    if (playerStateCheckInterval) {
      clearInterval(playerStateCheckInterval)
      playerStateCheckInterval = null
      logger.info('🛑 [ServerState] Stopped proactive player state monitoring')
    }
  }

  // Initialize event handlers for real-time WebSocket state management
  setupEventHandlers()

  const store = {
    // State (read-only, server-authoritative)
    playlists: readonly(playlists),
    currentPlaylist: readonly(currentPlaylist),
    playerState: readonly(playerState),
    globalSequence: readonly(globalSequence),
    playlistSequences: readonly(playlistSequences),
    isConnected: readonly(isConnected),
    isReconnecting: readonly(isReconnecting),
    pendingOperations: readonly(pendingOperations),

    // Getters
    getPlaylistById,
    getPlaylistSequence,

    // Socket management actions via RealSocketService
    subscribeToPlaylists,
    subscribeToPlaylist,
    unsubscribeFromPlaylist,
    requestStateSync,
    manualSync,
    requestInitialPlayerState,

    // Player state management - exposed for optimistic updates
    handlePlayerState
  }

  return store
})
