# Frontend Contracts Usage

## Overview

The frontend uses TypeScript types generated from the `tomb-contracts` repository (added as a git submodule).

## Structure

```
front/
├── src/
│   └── types/
│       ├── index.ts          # Re-exports from contracts (main import point)
│       ├── contracts.ts      # Legacy (will be removed after migration)
│       └── socket.ts         # App-specific Socket.IO types
└── ../contracts/             # Git submodule
    └── generated/
        └── typescript/       # Generated types used by frontend
```

## Usage in Components

### Import Types

```typescript
// ✅ Correct: Import from types/index
import { PlayerState, Playlist, Track } from '@/types';

// ❌ Wrong: Don't import directly from contracts
import { PlayerState } from '../../contracts/generated/typescript';
```

### Example Component

```typescript
<script setup lang="ts">
import { ref } from 'vue';
import type { PlayerState, Playlist } from '@/types';

const playerState = ref<PlayerState | null>(null);
const playlists = ref<Playlist[]>([]);

async function loadPlayer() {
  const response = await fetch('/api/player/status');
  const json = await response.json();
  playerState.value = json.data; // Fully typed!
}
</script>
```

## Updating Contracts

### When Backend Changes API

```bash
# 1. Update contracts submodule
cd ../contracts
git pull origin main

# 2. Regenerate TypeScript types
bash scripts/generate-all.sh

# 3. Types are now updated in your frontend
cd ../front
npm run type-check  # Verify no breaking changes
```

### When You Need Latest Contracts

```bash
# Quick command
npm run contracts:update

# Or manually
cd ../contracts && git pull && bash scripts/generate-all.sh
```

## Migration Path

### Current State (Before Submodule)
- Using `front/src/types/contracts.ts` (manually maintained)

### After Submodule Added
1. Add contracts as submodule (see root `CONTRACTS_INTEGRATION.md`)
2. Update `front/src/types/index.ts` to import from generated types
3. Remove `front/src/types/contracts.ts` (replaced by generated types)
4. All imports continue to work from `@/types`

### Breaking Changes
- When contracts change in breaking ways, TypeScript compiler will error
- Fix errors before deploying
- Use `server_seq` for gradual migration if needed

## Type Safety Benefits

✅ **Compile-time errors** when backend changes API
✅ **Auto-complete** in IDE for all API responses
✅ **Refactoring support** when renaming fields
✅ **Self-documenting** code with types
✅ **No drift** between backend and frontend

## Common Patterns

### API Response Handling

```typescript
import type { ApiResponse, PlayerState } from '@/types';

async function getPlayer(): Promise<PlayerState> {
  const response = await fetch('/api/player/status');
  const json: ApiResponse<PlayerState> = await response.json();

  if (json.status === 'success') {
    return json.data!;
  }
  throw new Error(json.message);
}
```

### Store Integration (Pinia)

```typescript
import { defineStore } from 'pinia';
import type { PlayerState } from '@/types';

export const usePlayerStore = defineStore('player', {
  state: () => ({
    playerState: null as PlayerState | null,
  }),

  actions: {
    async fetchState() {
      const response = await fetch('/api/player/status');
      const json = await response.json();
      this.playerState = json.data;
    }
  }
});
```

### Socket.IO with Types

```typescript
import { io } from 'socket.io-client';
import type { StateEventEnvelope, PlayerState } from '@/types';

const socket = io();

socket.on('state:player', (envelope: StateEventEnvelope<PlayerState>) => {
  console.log('Player updated:', envelope.data);
  console.log('Sequence:', envelope.server_seq);
});
```

## Troubleshooting

### Types Not Found

**Error:** `Cannot find module '@/types'`

**Fix:**
```bash
# Ensure contracts are generated
cd ../contracts
bash scripts/generate-all.sh

# Restart TypeScript server in VSCode
# Cmd+Shift+P → "TypeScript: Restart TS Server"
```

### Outdated Types

**Error:** Type doesn't match API response

**Fix:**
```bash
cd ../contracts
git pull origin main
bash scripts/generate-all.sh
cd ../front
npm run dev  # Restart dev server
```

### Submodule Not Initialized

**Error:** `contracts/generated/typescript` not found

**Fix:**
```bash
cd ..  # Root of tomb-rpi
git submodule update --init --recursive
cd contracts
bash scripts/generate-all.sh
```

## Scripts

Add to `front/package.json`:

```json
{
  "scripts": {
    "contracts:update": "cd ../contracts && git pull && bash scripts/generate-all.sh",
    "contracts:generate": "cd ../contracts && bash scripts/generate-all.sh",
    "type-check": "vue-tsc --noEmit"
  }
}
```

Then use:

```bash
npm run contracts:update    # Pull latest and generate
npm run contracts:generate  # Just regenerate from current
npm run type-check          # Check types without building
```
