/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Centralized Cache Service
 *
 * Provides a unified caching mechanism for API responses to avoid redundant network requests.
 * Supports TTL (Time To Live), size limits, and automatic cleanup of expired entries.
 */

import { timerManager } from '@/utils/TimerManager'
import { logger } from '@/utils/logger'

interface CacheEntry<T = unknown> {
  data: T;
  timestamp: number;
  ttl: number;
  size: number; // Estimated size in bytes for memory management
  accessCount: number;
  lastAccessed: number;
}

class CacheService {
  private cache = new Map<string, CacheEntry>();
  private defaultTTL = 30000; // 30 seconds
  private maxSize = 50 * 1024 * 1024; // 50MB max cache size
  private maxEntries = 1000; // Maximum number of entries
  private currentSize = 0;
  private cleanupIntervalId: number | null = null;

  constructor() {
    // Start periodic cleanup
    this.startPeriodicCleanup()
  }

  /**
   * Estimate the size of data in bytes
   */
  private estimateSize(data: any): number {
    if (data === null || data === undefined) return 0
    if (typeof data === 'string') return data.length * 2 // UTF-16
    if (typeof data === 'number') return 8
    if (typeof data === 'boolean') return 4
    if (ArrayBuffer.isView(data)) return data.byteLength
    
    // For objects and arrays, use JSON.stringify length as approximation
    try {
      return JSON.stringify(data).length * 2
    } catch {
      return 1024 // Default estimate for non-serializable objects
    }
  }

  /**
   * Evict entries using LRU strategy when cache is full
   */
  private evictLRUEntries(): void {
    // Sort entries by last accessed time (oldest first)
    const entries = Array.from(this.cache.entries())
      .sort(([, a], [, b]) => a.lastAccessed - b.lastAccessed)
    
    // Remove oldest entries until we're under limits
    let removedCount = 0
    for (const [key, entry] of entries) {
      if (this.cache.size <= this.maxEntries * 0.8 && this.currentSize <= this.maxSize * 0.8) {
        break
      }
      
      this.cache.delete(key)
      this.currentSize -= entry.size
      removedCount++
    }
    
    if (removedCount > 0) {
      logger.debug(`Evicted ${removedCount} LRU cache entries`)
    }
  }

  /**
   * Set a value in the cache with optional TTL
   * @param key - Cache key
   * @param data - Data to cache
   * @param ttl - Time to live in milliseconds (optional, uses default if not provided)
   */
  set<T>(key: string, data: T, ttl?: number): void {
    const now = Date.now()
    const size = this.estimateSize(data)
    
    // Remove old entry if exists
    const oldEntry = this.cache.get(key)
    if (oldEntry) {
      this.currentSize -= oldEntry.size
    }
    
    const entry: CacheEntry<T> = {
      data,
      timestamp: now,
      ttl: ttl || this.defaultTTL,
      size,
      accessCount: 0,
      lastAccessed: now
    };
    
    this.cache.set(key, entry);
    this.currentSize += size
    
    // Check if we need to evict entries
    if (this.cache.size > this.maxEntries || this.currentSize > this.maxSize) {
      this.evictLRUEntries()
    }
  }

  /**
   * Get a value from the cache
   * @param key - Cache key
   * @returns Cached data or null if not found or expired
   */
  get<T>(key: string): T | null {
    const entry = this.cache.get(key) as CacheEntry<T> | undefined;
    
    if (!entry) {
      return null;
    }

    const now = Date.now();
    if (now - entry.timestamp > entry.ttl) {
      this.cache.delete(key);
      this.currentSize -= entry.size;
      return null;
    }

    // Update access tracking for LRU
    entry.accessCount++;
    entry.lastAccessed = now;

    return entry.data;
  }

  /**
   * Check if a key exists and is not expired
   * @param key - Cache key
   * @returns True if key exists and is valid
   */
  has(key: string): boolean {
    return this.get(key) !== null;
  }

  /**
   * Remove a specific key from cache
   * @param key - Cache key to remove
   */
  delete(key: string): void {
    const entry = this.cache.get(key);
    if (entry) {
      this.currentSize -= entry.size;
    }
    this.cache.delete(key);
  }

  /**
   * Clear all cache entries
   */
  clear(): void {
    this.cache.clear();
    this.currentSize = 0;
  }

  /**
   * Clear all cache entries matching a pattern
   * @param pattern - Pattern to match (supports wildcards with *)
   */
  clearPattern(pattern: string): void {
    const regex = new RegExp(pattern.replace(/\*/g, '.*'));
    const keysToDelete = Array.from(this.cache.keys()).filter(key => regex.test(key));
    keysToDelete.forEach(key => {
      const entry = this.cache.get(key);
      if (entry) {
        this.currentSize -= entry.size;
      }
      this.cache.delete(key);
    });
  }

  /**
   * Invalidate cache for a specific playlist or all playlists
   * @param playlistId - Playlist identifier, or undefined to clear all playlist cache
   */
  invalidatePlaylistCache(playlistId?: string): void {
    if (playlistId) {
      this.delete(playlistId);
      this.delete(`playlist-${playlistId}`);
    } else {
      this.clearPattern('*playlist*');
      this.delete('all-playlists');
    }
  }

  /**
   * Invalidate files cache
   */
  invalidateFilesCache(): void {
    this.clearPattern('*files*');
    this.delete('audio_files');
  }

  /**
   * Clean up expired entries (called periodically)
   */
  cleanup(): void {
    const now = Date.now();
    const keysToDelete: string[] = [];
    let freedSize = 0;

    this.cache.forEach((entry, key) => {
      if (now - entry.timestamp > entry.ttl) {
        keysToDelete.push(key);
        freedSize += entry.size;
      }
    });

    keysToDelete.forEach(key => this.cache.delete(key));
    this.currentSize -= freedSize;
    
    if (keysToDelete.length > 0) {
      logger.debug(`Cleaned up ${keysToDelete.length} expired cache entries, freed ${(freedSize / 1024 / 1024).toFixed(2)}MB`);
    }
  }

  /**
   * Start periodic cleanup using TimerManager
   */
  private startPeriodicCleanup(): void {
    if (this.cleanupIntervalId !== null) {
      return; // Already running
    }
    
    this.cleanupIntervalId = timerManager.setInterval(() => {
      this.cleanup();
    }, 5 * 60 * 1000, 'CacheService periodic cleanup'); // Every 5 minutes
  }

  /**
   * Stop periodic cleanup
   */
  stopPeriodicCleanup(): void {
    if (this.cleanupIntervalId !== null) {
      timerManager.clearInterval(this.cleanupIntervalId);
      this.cleanupIntervalId = null;
    }
  }

  /**
   * Get cache statistics
   */
  getStats() {
    const now = Date.now();
    let validEntries = 0;
    let expiredEntries = 0;
    let totalAccessCount = 0;

    this.cache.forEach(entry => {
      totalAccessCount += entry.accessCount;
      if (now - entry.timestamp > entry.ttl) {
        expiredEntries++;
      } else {
        validEntries++;
      }
    });

    return {
      totalEntries: this.cache.size,
      validEntries,
      expiredEntries,
      currentSizeMB: (this.currentSize / 1024 / 1024).toFixed(2),
      maxSizeMB: (this.maxSize / 1024 / 1024).toFixed(2),
      sizeUsagePercent: ((this.currentSize / this.maxSize) * 100).toFixed(1),
      maxEntries: this.maxEntries,
      totalAccessCount,
      averageAccessCount: validEntries > 0 ? (totalAccessCount / validEntries).toFixed(1) : 0
    };
  }

  /**
   * Configure cache limits
   */
  configure(options: {
    maxSize?: number;
    maxEntries?: number;
    defaultTTL?: number;
  }): void {
    if (options.maxSize) this.maxSize = options.maxSize;
    if (options.maxEntries) this.maxEntries = options.maxEntries;
    if (options.defaultTTL) this.defaultTTL = options.defaultTTL;
    
    // Trigger eviction if current size exceeds new limits
    if (this.cache.size > this.maxEntries || this.currentSize > this.maxSize) {
      this.evictLRUEntries();
    }
  }
}

// Export singleton instance
export const cacheService = new CacheService();

// Register cleanup handler with TimerManager for proper shutdown
if (typeof window !== 'undefined') {
  timerManager.registerCleanupHandler(() => {
    cacheService.stopPeriodicCleanup();
    logger.debug('Cache cleanup stopped');
  });
}

export default cacheService;
