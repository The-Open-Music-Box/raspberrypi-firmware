# ADR 002: StateEventCoordinator Throttling Responsibility

**Status:** Accepted

**Date:** 2025-11-09

**Context:**

During Phase 6 architecture audit, we identified that `StateEventCoordinator` handles throttling of position update events. This appears to violate the Single Responsibility Principle (SRP) because the coordinator has multiple concerns:

1. **Coordination**: Orchestrating state broadcasts across the system (primary responsibility)
2. **Throttling**: Rate-limiting position updates to prevent flooding (performance optimization)

The throttling code in question:

```python
# app/src/application/services/state_event_coordinator.py:154-160
# Throttle position updates
current_time = time.time()
if (
    current_time - self._last_position_emit_time
    < socket_config.POSITION_THROTTLE_MIN_MS / 1000
):
    return None

self._last_position_emit_time = current_time
```

## Decision

**We accept this design and will KEEP throttling in StateEventCoordinator.**

## Rationale

### 1. Performance-Critical Coordination

Position updates are a special case in the system:

- **Volume**: Generated ~1000 times per second by the audio engine
- **Impact**: Without throttling, would overwhelm WebSocket connections
- **Timing**: Must be decided BEFORE creating event envelopes (not after)

The throttling decision is part of the coordination logic: "Should this position update be broadcast?"

### 2. State Management Concern

Throttling position updates is not a generic rate-limiting concern—it's specific to state event semantics:

- Position updates are **continuous state** (not discrete events)
- Clients only need the LATEST position (not every intermediate value)
- The coordinator knows this semantic and can optimize accordingly

This is fundamentally different from generic API rate limiting.

### 3. Placement Prevents Waste

Throttling at the coordinator level prevents:

- Creating unnecessary event envelopes
- Serializing payloads that will never be sent
- Incrementing sequence numbers for dropped events
- Wasting CPU cycles in the broadcast pipeline

If we throttled downstream (e.g., in WebSocket layer), we'd still pay these costs.

### 4. Cohesion with Broadcast Logic

The throttling is tightly coupled to the broadcast decision:

```python
# Pseudo-code showing the cohesion:
def broadcast_position_update(...):
    if should_throttle():  # Coordination decision
        return None

    envelope = create_envelope(...)  # Coordination action
    broadcast(envelope)  # Coordination action
```

Separating the throttle decision would break this natural flow.

### 5. Domain-Specific Behavior

This isn't generic throttling—it's **playback position throttling** with domain-specific rules:

- Only applies to position updates (not other state events)
- Configurable via `POSITION_THROTTLE_MIN_MS`
- Tied to audio playback semantics

A generic `ThrottleService` wouldn't understand these domain rules.

## Alternatives Considered

### Option A: Extract to ThrottleService

```python
class ThrottleService:
    def should_throttle(self, key: str, min_interval_ms: int) -> bool:
        ...

# In coordinator:
if self.throttle_service.should_throttle("position", 1000):
    return None
```

**Rejected because:**
- Adds abstraction without benefit
- Generic throttling loses domain context
- Requires passing coordinator state to external service
- More complex to test and maintain

### Option B: Throttle in WebSocket Layer

```python
# In WebSocketStateHandlers
async def emit_event(self, event):
    if event.type == "position" and should_throttle(event):
        return
    await self.sio.emit(...)
```

**Rejected because:**
- Too late in the pipeline (envelope already created)
- WebSocket layer shouldn't understand domain semantics
- Violates layer boundaries (infra shouldn't know about position updates)
- Still requires throttle state management somewhere

### Option C: Throttle in Audio Engine

```python
# In PlaybackCoordinator
def _report_position(self, position_ms):
    if not self._should_report_position(position_ms):
        return
    self.coordinator.broadcast_position_update(...)
```

**Rejected because:**
- Audio engine shouldn't know about network constraints
- Domain layer shouldn't handle infrastructure concerns
- Couples playback logic to WebSocket performance

## Decision Details

We keep throttling in `StateEventCoordinator` because:

1. **It's coordination logic**: Deciding whether to broadcast IS coordination
2. **It's performance-critical**: Must happen before expensive operations
3. **It's domain-specific**: Rules are tied to playback state semantics
4. **It's correctly placed**: Application layer is the right place for this decision

## Consequences

### Positive

- Efficient: Prevents waste in the broadcast pipeline
- Cohesive: Throttle decision is part of coordination logic
- Maintainable: All position broadcast logic in one place
- Testable: Easy to verify throttling behavior in coordinator tests

### Negative

- Coordinator has two responsibilities (coordination + throttling)
- Theoretical SRP violation (accepted as pragmatic trade-off)

### Mitigation

To keep the code clean:

1. **Document the throttling logic** clearly in coordinator docstrings
2. **Extract throttle state** to a private `_PositionThrottle` helper class if it grows
3. **Keep configuration external** (via `socket_config.POSITION_THROTTLE_MIN_MS`)

Example of potential future extraction:

```python
class _PositionThrottle:
    """Helper for throttling position update broadcasts."""

    def __init__(self, min_interval_ms: int):
        self.min_interval_ms = min_interval_ms
        self._last_emit_time = 0

    def should_emit(self) -> bool:
        current_time = time.time()
        if current_time - self._last_emit_time < self.min_interval_ms / 1000:
            return False
        self._last_emit_time = current_time
        return True

# In StateEventCoordinator:
self._position_throttle = _PositionThrottle(socket_config.POSITION_THROTTLE_MIN_MS)

def broadcast_position_update(...):
    if not self._position_throttle.should_emit():
        return None
    ...
```

This would encapsulate the throttle logic while keeping it in the coordinator.

## Compliance Notes

This decision is **acceptable under DDD/Clean Architecture** because:

- StateEventCoordinator is in the **Application Layer**
- Application layer orchestrates use cases and coordinates between layers
- Performance optimizations at this layer are appropriate
- No domain logic leaks into infrastructure
- Infrastructure doesn't make domain decisions

The application layer is specifically designed for this kind of coordination logic.

## Performance Impact

Current throttling (1000ms interval):

- **Before throttling**: ~1000 events/second
- **After throttling**: ~1 event/second
- **Bandwidth saved**: ~99.9%
- **CPU saved**: Significant (no envelope creation, serialization, or WebSocket writes)

This is a critical performance optimization that must stay close to the decision point.

## References

- Phase 6 Architecture Audit: Issue 6.4B
- Related File: `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/application/services/state_event_coordinator.py:154-160`
- Configuration: `back/app/src/config/socket_config.py` (`POSITION_THROTTLE_MIN_MS`)

## Review

This ADR should be reviewed if:

- Position update frequency requirements change
- We implement adaptive throttling based on client capabilities
- Performance profiling shows throttling is insufficient
- We need different throttle rates for different event types
- Client-side interpolation makes throttling obsolete
