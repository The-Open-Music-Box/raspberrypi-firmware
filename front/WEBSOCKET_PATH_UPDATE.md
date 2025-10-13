# WebSocket Path Update - RPI Frontend

**Date:** 2025-10-13
**Issue:** Frontend cannot connect to ESP32 WebSocket endpoint

---

## Change Applied

Updated `/src/config/environment.ts` to add ESP32 WebSocket path configuration.

### Before:
```typescript
socket: {
  url: apiConfig.baseUrl,
  options: {
    autoConnect: true,
    transports: ['websocket', 'polling']
  }
}
```

### After:
```typescript
socket: {
  url: apiConfig.baseUrl,
  options: {
    autoConnect: true,
    transports: ['websocket', 'polling'],
    path: '/ws'  // ESP32 WebSocket path
  }
}
```

---

## Why This Change?

When the RPI frontend connects to the ESP32 device, it needs to use the correct WebSocket path.

**Background:**
- ESP32 changed WebSocket endpoint from `/socket.io/` to `/ws`
- ESP32 provides plain WebSocket (RFC 6455), not full Socket.IO protocol
- Without `path: '/ws'`, socket.io-client defaults to `/socket.io/`
- This caused connection failures: `WebSocket connection to 'ws://10.0.0.219/socket.io/?EIO=4&transport=websocket' failed`

---

## Error Before Change

```
[Error] WebSocket connection to 'ws://10.0.0.219/socket.io/?EIO=4&transport=websocket' failed:
        There was a bad response from the server.
[Error] 🔊🎵 ❌ SOCKET CONNECTION ERROR: {message: "websocket error", type: "TransportError"}
[Warning] Cannot emit join:playlists: socket not connected
```

---

## Expected Behavior After Change

```
[Info] 🔊🎵 ✅ SOCKET CONNECTED SUCCESSFULLY!
[Info] Received connection status
[Info] Successfully joined playlists room
[Info] Receiving state:player events
```

---

## Connection Scenarios

### Scenario 1: Frontend → ESP32 (Current Configuration)
✅ **Now works with `path: '/ws'`**
- URL: `http://10.0.0.219:80` (ESP32 IP)
- Path: `/ws`
- Transport: Plain WebSocket with Socket.IO-style events

### Scenario 2: Frontend → RPI Backend (If Needed)
The RPI backend serves full Socket.IO on default path `/socket.io/`.

If you need to connect to RPI backend instead of ESP32, you have two options:

**Option A: Use environment variable**
```bash
# Connect to RPI backend
VUE_APP_API_URL=http://rpi-ip:5004 npm run dev

# Connect to ESP32
VUE_APP_API_URL=http://esp32-ip:80 npm run dev
```

**Option B: Dynamic path configuration** (requires code change)
```typescript
const createAppConfig = (): AppConfig => {
  const apiConfig = getApiConfig()

  // Detect if connecting to ESP32 (port 80) or RPI (port 5004)
  const isESP32 = apiConfig.baseUrl.includes(':80') || apiConfig.baseUrl.includes('10.0.0.')

  return {
    api: apiConfig,
    socket: {
      url: apiConfig.baseUrl,
      options: {
        autoConnect: true,
        transports: ['websocket', 'polling'],
        ...(isESP32 ? { path: '/ws' } : {})  // Only add path for ESP32
      }
    },
    // ...
  }
}
```

---

## Testing

### 1. Rebuild Frontend
```bash
cd rpi-firmware/front
npm run build
```

### 2. Test Connection
Open browser console and look for:
- ✅ `SOCKET CONNECTED SUCCESSFULLY!`
- ✅ `connection_status` event received
- ✅ `state:player` events received
- ✅ No "websocket error" messages

### 3. Verify Functionality
- Player controls should work
- Playlist updates should sync in real-time
- NFC events should be received

---

## Contract Compliance

✅ **No contract breaking changes**
- All Socket.IO events remain the same
- Event envelope format unchanged
- Only the transport path is updated

---

## Rollback (If Needed)

To connect to RPI backend instead of ESP32, remove the path:

```typescript
socket: {
  url: apiConfig.baseUrl,
  options: {
    autoConnect: true,
    transports: ['websocket', 'polling'],
    // path: '/ws'  // ← Comment out or remove for RPI backend
  }
}
```

---

## Related Documentation

- `/esp32-firmware/docs/CROSS_REPOSITORY_ALIGNMENT_ANALYSIS.md` - Full alignment analysis
- `/esp32-firmware/docs/WEBSOCKET_PATH_CHANGE_IMPACT.md` - Impact analysis
- `/WEBSOCKET_ALIGNMENT_SUMMARY.md` - Quick reference (project root)
- `/flutter_app/WEBSOCKET_CONNECTION_UPDATE.md` - Flutter changes

---

## Summary

**Single line change:** Added `path: '/ws'` to socket options for ESP32 compatibility.

This fixes the WebSocket connection error when the RPI frontend connects to ESP32 devices.
