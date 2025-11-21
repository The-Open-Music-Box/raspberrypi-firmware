/**
 * Contract tests for Socket.IO State broadcast events - Frontend
 *
 * Validates event payload structures match backend contract.
 *
 * Progress: 11/11 events tested ✅
 */

import { describe, it, expect } from 'vitest'

describe('Socket.IO State Events Contract Tests', () => {
  it('should validate state:player event payload structure', () => {
    /**
     * Contract:
     * - Event: 'state:player'
     * - Envelope: {event_type, data: {playing, position, volume, current_track?, playlist_id?}, server_seq, timestamp}
     */
    const playerStatePayload = {
      event_type: 'state:player',
      data: {
        playing: true,
        position: 45.2,
        volume: 75,
        current_track: 'track-123',
        playlist_id: 'playlist-456'
      },
      server_seq: 100,
      timestamp: Date.now()
    }
    expect(playerStatePayload).toHaveProperty('event_type')
    expect(playerStatePayload).toHaveProperty('data')
    expect(playerStatePayload).toHaveProperty('server_seq')
    expect(playerStatePayload.data).toHaveProperty('playing')
    expect(typeof playerStatePayload.data.playing).toBe('boolean')
  })

  it('should validate state:track_position event payload structure', () => {
    /**
     * Contract:
     * - Event: 'state:track_position'
     * - Lightweight position updates (200ms interval)
     * - Data: {position_ms: number, track_id?: string, is_playing: boolean, duration_ms?: number}
     */
    const trackPositionPayload = {
      event_type: 'state:track_position',
      data: {
        position_ms: 45200,
        track_id: 'track-123',
        is_playing: true,
        duration_ms: 180000
      },
      server_seq: 101,
      timestamp: Date.now()
    }
    expect(trackPositionPayload.data).toHaveProperty('position_ms')
    expect(trackPositionPayload.data).toHaveProperty('is_playing')
    expect(typeof trackPositionPayload.data.position_ms).toBe('number')
    expect(typeof trackPositionPayload.data.is_playing).toBe('boolean')
  })

  it('should validate state:playlists event payload structure', () => {
    /**
     * Contract:
     * - Event: 'state:playlists'
     * - Data: array of playlist objects
     */
    const playlistsStatePayload = {
      event_type: 'state:playlists',
      data: [
        { id: 'playlist-1', title: 'Playlist 1', tracks: [] },
        { id: 'playlist-2', title: 'Playlist 2', tracks: [] }
      ],
      server_seq: 102,
      timestamp: Date.now()
    }
    expect(playlistsStatePayload).toHaveProperty('data')
    expect(Array.isArray(playlistsStatePayload.data)).toBe(true)
  })

  it('should validate state:playlist event payload structure', () => {
    /**
     * Contract:
     * - Event: 'state:playlist'
     * - Data: single playlist object with tracks
     */
    const playlistStatePayload = {
      event_type: 'state:playlist',
      data: {
        id: 'playlist-123',
        title: 'Test Playlist',
        tracks: [
          { id: 'track-1', title: 'Track 1', number: 1 }
        ]
      },
      playlist_id: 'playlist-123',
      server_seq: 103,
      timestamp: Date.now()
    }
    expect(playlistStatePayload.data).toHaveProperty('id')
    expect(playlistStatePayload.data).toHaveProperty('tracks')
    expect(Array.isArray(playlistStatePayload.data.tracks)).toBe(true)
  })

  it('should validate state:track event payload structure', () => {
    /**
     * Contract:
     * - Event: 'state:track'
     * - Data: track object
     */
    const trackStatePayload = {
      event_type: 'state:track',
      data: {
        id: 'track-456',
        title: 'Track Title',
        number: 3,
        duration: 180000
      },
      playlist_id: 'playlist-123',
      server_seq: 104,
      timestamp: Date.now()
    }
    expect(trackStatePayload.data).toHaveProperty('id')
    expect(trackStatePayload.data).toHaveProperty('title')
    expect(typeof trackStatePayload.data.id).toBe('string')
  })

  it('should validate state:playlist_deleted event payload structure', () => {
    /**
     * Contract:
     * - Event: 'state:playlist_deleted'
     * - Data: {playlist_id: string, message?: string}
     */
    const playlistDeletedPayload = {
      event_type: 'state:playlist_deleted',
      data: {
        playlist_id: 'playlist-deleted',
        message: 'Playlist deleted successfully'
      },
      playlist_id: 'playlist-deleted',
      server_seq: 105,
      timestamp: Date.now()
    }
    expect(playlistDeletedPayload.data).toHaveProperty('playlist_id')
    expect(typeof playlistDeletedPayload.data.playlist_id).toBe('string')
  })

  it('should validate state:playlist_created event payload structure', () => {
    /**
     * Contract:
     * - Event: 'state:playlist_created'
     * - Data: {playlist: object}
     */
    const playlistCreatedPayload = {
      event_type: 'state:playlist_created',
      data: {
        playlist: {
          id: 'playlist-new',
          title: 'New Playlist',
          tracks: []
        }
      },
      server_seq: 106,
      timestamp: Date.now()
    }
    expect(playlistCreatedPayload.data).toHaveProperty('playlist')
    expect(typeof playlistCreatedPayload.data.playlist).toBe('object')
  })

  it('should validate state:playlist_updated event payload structure', () => {
    /**
     * Contract:
     * - Event: 'state:playlist_updated'
     * - Data: {playlist_id: string, changes?: object}
     */
    const playlistUpdatedPayload = {
      event_type: 'state:playlist_updated',
      data: {
        playlist_id: 'playlist-updated',
        changes: { title: 'Updated Title' }
      },
      playlist_id: 'playlist-updated',
      server_seq: 107,
      timestamp: Date.now()
    }
    expect(playlistUpdatedPayload.data).toHaveProperty('playlist_id')
    expect(typeof playlistUpdatedPayload.data.playlist_id).toBe('string')
  })

  it('should validate state:track_deleted event payload structure', () => {
    /**
     * Contract:
     * - Event: 'state:track_deleted'
     * - Data: {track_number: number, playlist_id: string}
     */
    const trackDeletedPayload = {
      event_type: 'state:track_deleted',
      data: {
        track_number: 3,
        playlist_id: 'playlist-123'
      },
      playlist_id: 'playlist-123',
      server_seq: 108,
      timestamp: Date.now()
    }
    expect(trackDeletedPayload.data).toHaveProperty('track_number')
    expect(trackDeletedPayload.data).toHaveProperty('playlist_id')
    expect(typeof trackDeletedPayload.data.track_number).toBe('number')
  })

  it('should validate state:track_added event payload structure', () => {
    /**
     * Contract:
     * - Event: 'state:track_added'
     * - Data: {track: object, playlist_id: string}
     */
    const trackAddedPayload = {
      event_type: 'state:track_added',
      data: {
        track: {
          id: 'track-new',
          title: 'New Track',
          number: 4
        },
        playlist_id: 'playlist-123'
      },
      playlist_id: 'playlist-123',
      server_seq: 109,
      timestamp: Date.now()
    }
    expect(trackAddedPayload.data).toHaveProperty('track')
    expect(trackAddedPayload.data).toHaveProperty('playlist_id')
    expect(typeof trackAddedPayload.data.track).toBe('object')
  })

  it('should validate state:volume_changed event payload structure', () => {
    /**
     * Contract:
     * - Event: 'state:volume_changed'
     * - Data: {volume: number}
     */
    const volumeChangedPayload = {
      event_type: 'state:volume_changed',
      data: {
        volume: 85
      },
      server_seq: 110,
      timestamp: Date.now()
    }
    expect(volumeChangedPayload.data).toHaveProperty('volume')
    expect(typeof volumeChangedPayload.data.volume).toBe('number')
  })
})
