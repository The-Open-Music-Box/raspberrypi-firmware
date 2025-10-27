# Button System Debug Logging Guide

## Overview

The button system now includes comprehensive debug logging to help you trace button press events from GPIO hardware all the way through action execution. Every layer logs with clear prefixes and emojis for easy identification.

## Log Structure

### Log Prefixes

All button-related logs use clear prefixes:
- `[BUTTON]` - Physical button press handler
- `[DISPATCH]` - Action dispatcher
- `[SYNC_DISPATCH]` - Synchronous dispatch wrapper
- `[ACTION:action_name]` - Individual action execution

### Log Levels

- **INFO** - Normal operation events (button presses, action execution)
- **DEBUG** - Detailed flow information (volume values, return values)
- **WARNING** - Non-critical issues (unmapped buttons, at volume limits)
- **ERROR** - Critical failures (exceptions, dispatch failures)

## Example Log Flow

### Successful Button Press (Volume Up)

```
INFO  🔘 [BUTTON] Button 4 pressed - starting dispatch
INFO  🎯 [BUTTON] Button 4 → Action: 'volume_up'
DEBUG 📤 [BUTTON] Dispatching button 4 to action 'volume_up'
DEBUG 🔄 [SYNC_DISPATCH] Wrapping async dispatch for button 4
DEBUG ⏳ [SYNC_DISPATCH] Running in event loop for button 4
DEBUG 📥 [DISPATCH] Received button 4 press event
INFO  🚀 [DISPATCH] Button 4 → Executing action 'volume_up'
INFO  🔊 [ACTION:volume_up] Increasing volume
DEBUG [ACTION:volume_up] Current volume: 50%
DEBUG [ACTION:volume_up] Target volume: 55%
INFO  ✅ [ACTION:volume_up] Volume increased: 50% → 55%
INFO  ✅ [DISPATCH] Action 'volume_up' completed successfully
INFO  ✅ [BUTTON] Button 4 action 'volume_up' completed successfully
```

### Volume at Maximum

```
INFO  🔘 [BUTTON] Button 4 pressed - starting dispatch
INFO  🎯 [BUTTON] Button 4 → Action: 'volume_up'
INFO  🔊 [ACTION:volume_up] Increasing volume
DEBUG [ACTION:volume_up] Current volume: 100%
DEBUG [ACTION:volume_up] Target volume: 100%
INFO  ℹ️  [ACTION:volume_up] Volume already at maximum (100%)
INFO  ✅ [DISPATCH] Action 'volume_up' completed successfully
INFO  ✅ [BUTTON] Button 4 action 'volume_up' completed successfully
```

### Track Navigation

```
INFO  🔘 [BUTTON] Button 3 pressed - starting dispatch
INFO  🎯 [BUTTON] Button 3 → Action: 'next_track'
INFO  ⏭️  [ACTION:next_track] Skipping to next track
DEBUG [ACTION:next_track] Coordinator.next_track() returned: True
INFO  ✅ [DISPATCH] Action 'next_track' completed successfully
INFO  ✅ [BUTTON] Button 3 action 'next_track' completed successfully
```

### Failed Action

```
INFO  🔘 [BUTTON] Button 3 pressed - starting dispatch
INFO  🎯 [BUTTON] Button 3 → Action: 'next_track'
INFO  ⏭️  [ACTION:next_track] Skipping to next track
DEBUG [ACTION:next_track] Coordinator.next_track() returned: False
WARN  ⚠️  [DISPATCH] Action 'next_track' returned False (operation failed or at limit)
ERROR ❌ [BUTTON] Button 3 action 'next_track' FAILED
```

### Unmapped Button

```
INFO  🔘 [BUTTON] Button 99 pressed - starting dispatch
WARN  ⚠️  [BUTTON] Button 99 has no configured action
```

### Exception in Action

```
INFO  🔘 [BUTTON] Button 3 pressed - starting dispatch
INFO  🎯 [BUTTON] Button 3 → Action: 'next_track'
INFO  🚀 [DISPATCH] Button 4 → Executing action 'next_track'
ERROR ❌ [DISPATCH] Exception in action 'next_track' for button 3: Connection timeout
    Traceback (most recent call last):
      File "button_action_application_service.py", line 141
      ...
ERROR ❌ [BUTTON] Button 3 action 'next_track' FAILED
```

## Button-to-Action Mapping

Based on `DEFAULT_BUTTON_CONFIGS`:

| Button ID | GPIO Pin | Action | Icon | Description |
|-----------|----------|--------|------|-------------|
| 0 | 23 | `print_debug` | 🐛 | Print playback debug info |
| 1 | 20 | `volume_down` | 🔉 | Decrease volume 5% |
| 2 | 16 | `previous_track` | ⏮️ | Previous track |
| 3 | 26 | `next_track` | ⏭️ | Next track |
| 4 | 19 | `volume_up` | 🔊 | Increase volume 5% |

## Action Icons

Each action type has a unique icon for quick visual identification:

- ▶️ `play` - Start playback
- ⏸️ `pause` - Pause playback
- ⏯️ `play_pause` - Toggle play/pause
- ⏹️ `stop` - Stop playback
- ⏭️ `next_track` - Next track
- ⏮️ `previous_track` - Previous track
- 🔊 `volume_up` - Increase volume
- 🔉 `volume_down` - Decrease volume
- 🐛 `print_debug` - Debug info

## Enabling Debug Logs

### In Development

Debug logs are enabled by default in development mode. To see all debug messages:

```bash
# Set log level to DEBUG
export LOG_LEVEL=DEBUG

# Start the application
python start_app.py
```

### View Live Logs on Raspberry Pi

```bash
# Follow application logs
sudo journalctl -fu app.service

# Filter only button logs
sudo journalctl -fu app.service | grep -E '\[BUTTON\]|\[DISPATCH\]|\[ACTION'

# Show last 100 button-related logs
sudo journalctl -u app.service -n 100 | grep -E '\[BUTTON\]|\[DISPATCH\]|\[ACTION'
```

### Programmatic Log Level

In your `.env` file:

```env
LOG_LEVEL=DEBUG
```

## Troubleshooting Common Issues

### Button Press Not Logged

**Problem**: No log output when button is pressed

**Possible Causes**:
1. Physical button not connected or faulty
2. GPIO pin misconfigured
3. Physical controls not initialized

**Check**:
```bash
# Look for initialization logs
grep "PhysicalControlsManager" /path/to/log

# Check button configuration
grep "Button.*mapped to action" /path/to/log
```

### Action Not Executing

**Problem**: Button press logged but action doesn't execute

**Look for**:
- `⚠️  [DISPATCH] No action configured for button X`
- `⚠️  [BUTTON] Button X has no configured action`

**Solution**: Check `DEFAULT_BUTTON_CONFIGS` in `button_actions_config.py`

### Coordinator Method Failures

**Problem**: Action returns False

**Look for**:
- `[ACTION:name] Coordinator.method() returned: False`
- `⚠️  [DISPATCH] Action 'name' returned False`

**Common causes**:
- No playlist loaded (for track navigation)
- Audio backend not initialized
- Volume already at min/max

### Event Loop Issues

**Problem**: `dispatch_sync` failures

**Look for**:
- `❌ [SYNC_DISPATCH] Error in sync dispatch`

**Solution**: Check if event loop is properly configured in main application

## Performance Monitoring

To track button response times, search for the time between:
1. `🔘 [BUTTON] Button X pressed` (entry point)
2. `✅ [BUTTON] Button X action 'name' completed` (exit point)

Example grep:
```bash
journalctl -u app.service | grep -E '\[BUTTON\] Button 4.*pressed|\[BUTTON\] Button 4.*completed'
```

## Testing Button Logging

Run tests with log output enabled:

```bash
# Run button tests with verbose logging
USE_MOCK_HARDWARE=true python -m pytest tests/unit/domain/actions/test_button_actions.py -v -s

# Run integration tests
USE_MOCK_HARDWARE=true python -m pytest tests/integration/test_physical_button_controls_e2e.py -v -s
```

## Log Analysis Tips

### Count Button Presses by Type

```bash
journalctl -u app.service --since "1 hour ago" | \
  grep "\[BUTTON\].*→ Action" | \
  awk -F"'" '{print $2}' | \
  sort | uniq -c | sort -rn
```

### Find Failed Actions

```bash
journalctl -u app.service --since "1 hour ago" | \
  grep "❌ \[BUTTON\]"
```

### Track Volume Changes

```bash
journalctl -u app.service --since "1 hour ago" | \
  grep "Volume.*→"
```

---

**With these comprehensive logs, you can now trace every button press from hardware to completion!** 🎉
