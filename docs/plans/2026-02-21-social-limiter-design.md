# Social Media Limiter - Design Document

**Date:** 2026-02-21
**Status:** Approved
**Author:** Human + Claude

## Overview

A macOS menu bar application that limits time spent on addictive social media and streaming websites. Uses system-level blocking via `/etc/hosts` for hard-to-bypass enforcement.

## Goals

- Help users manage addiction to YouTube, Reddit, TikTok, Netflix, etc.
- Provide a shared daily time budget across all blocked sites
- Make bypassing difficult but not impossible (emergency override with friction)
- Clean, minimal UI suitable for open-source distribution

## Technical Approach

**Stack:** Python + rumps (menu bar framework) + pyobjc (macOS APIs)
**Future:** Swift/SwiftUI rewrite if prototype succeeds

### Why System-Level Blocking?

Browser extensions are too easy to disable in weak moments. Modifying `/etc/hosts` requires terminal access or password prompts, providing meaningful friction against impulse browsing.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Menu Bar App                       │
│              (Python + rumps)                        │
├─────────────────────────────────────────────────────┤
│  - Shows remaining daily time                        │
│  - Quick-add sites                                   │
│  - Trigger override flow                             │
│  - Settings access                                   │
└───────────────────┬─────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│               Blocking Service                       │
│           (Background process)                       │
├─────────────────────────────────────────────────────┤
│  - Tracks time spent on blocked sites               │
│  - Modifies /etc/hosts when limit reached           │
│  - Handles override countdown                        │
│  - Persists state to ~/.config/social_limiter/      │
└─────────────────────────────────────────────────────┘
```

## Core Features

### 1. Daily Time Budget (Shared Pool)

- Single time budget shared across all blocked sites
- Configurable daily limit (e.g., 30 minutes)
- Resets at midnight (or configurable time)

### 2. Time Tracking

Every 5 seconds, the background process:
1. Uses AppleScript to get active browser tab URL (Safari/Chrome/Firefox)
2. Checks if domain matches any blocked site
3. Decrements remaining budget if matched
4. Triggers blocking when budget hits zero

### 3. Blocking Mechanism

When budget is exhausted, append to `/etc/hosts`:

```
# -- SocialLimiter Start --
127.0.0.1    youtube.com
127.0.0.1    www.youtube.com
127.0.0.1    m.youtube.com
# -- SocialLimiter End --
```

After modification, flush DNS cache:
```bash
sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder
```

### 4. Shutdown/Sleep Handling

State includes timestamps for proper reset detection:

```json
{
  "remaining_seconds": 300,
  "last_active": "2026-02-21T21:00:00",
  "next_reset": "2026-02-22T00:00:00"
}
```

On app launch or wake from sleep:
- If `current_time > next_reset`: Reset budget, unblock sites
- Otherwise: Maintain existing state

Registers for macOS power notifications (`NSWorkspaceWillSleepNotification`, `NSWorkspaceDidWakeNotification`).

### 5. Override Mechanism

When blocked and needing emergency access:

1. Click "Request Override" in menu bar
2. 5-minute countdown window appears (cannot be skipped/closed)
3. After countdown completes, grants 10 minutes of access
4. After 10 minutes, blocks again
5. Repeat override flow for more time

Configurable values:
- `override_delay_seconds`: 300 (5 minutes)
- `override_grant_seconds`: 600 (10 minutes)

## User Interface

### Menu Bar Icon States

| Icon | State |
|------|-------|
| ● Green | Sites unblocked, time remaining |
| ◐ Yellow | Under 10 minutes left |
| ○ Red | Blocked, budget exhausted |
| ⏳ Hourglass | Override countdown in progress |

### Dropdown Menu

```
┌─────────────────────────────────┐
│  ● 23 min remaining            │
├─────────────────────────────────┤
│  ▶ Today's usage: 37 min        │
├─────────────────────────────────┤
│  Blocked Sites               ▶ │
│  Add Site...                    │
├─────────────────────────────────┤
│  Request Override...            │
├─────────────────────────────────┤
│  Settings...                    │
│  View History                   │
├─────────────────────────────────┤
│  Quit                           │
└─────────────────────────────────┘
```

### Settings Window

- Daily time limit (slider/input)
- Reset time (default: midnight)
- Override delay duration
- Override grant duration
- Launch at login toggle

## Project Structure

```
social_media_limiter/
├── src/
│   ├── __init__.py
│   ├── app.py              # Menu bar app (rumps)
│   ├── blocker.py          # /etc/hosts manipulation
│   ├── tracker.py          # Time tracking, browser tab detection
│   ├── config.py           # Load/save config
│   ├── state.py            # State management, reset logic
│   └── override.py         # Override countdown window
├── resources/
│   ├── icon_green.png
│   ├── icon_yellow.png
│   ├── icon_red.png
│   └── icon_countdown.png
├── tests/
│   ├── test_blocker.py
│   ├── test_tracker.py
│   └── test_state.py
├── docs/
│   ├── INSTALLATION.md
│   ├── CONFIGURATION.md
│   ├── DEVELOPMENT.md
│   └── plans/
├── config.example.json
├── pyproject.toml
├── LICENSE
├── CHANGELOG.md
└── README.md
```

## Dependencies

- `rumps` - Menu bar app framework
- `pyobjc` - macOS APIs (power notifications, AppleScript)
- `ruff` - Linting/formatting
- `pytest` - Testing
- `pre-commit` - Git hooks

## Configuration Files

### config.json (user config)

```json
{
  "daily_limit_seconds": 1800,
  "reset_time": "00:00",
  "override_delay_seconds": 300,
  "override_grant_seconds": 600,
  "blocked_sites": [
    {
      "domain": "youtube.com",
      "subdomains": ["www", "m"]
    },
    {
      "domain": "reddit.com",
      "subdomains": ["www", "old", "i"]
    }
  ],
  "launch_at_login": true
}
```

### state.json (runtime state)

```json
{
  "remaining_seconds": 1200,
  "last_active": "2026-02-21T14:30:00",
  "next_reset": "2026-02-22T00:00:00",
  "is_blocked": false,
  "override_active_until": null
}
```

## Known Limitations (Prototype)

1. **Password prompts** - Each block/unblock requires sudo password. User could refuse to enter password to bypass. Will be fixed with privileged helper in Swift rewrite.

2. **Browser detection** - AppleScript only detects frontmost/active tab. Background tabs aren't tracked.

3. **App-level blocking** - Only blocks browsers. Native YouTube/Reddit apps not affected (but most desktop usage is browser-based).

## Future Improvements (Swift Rewrite)

- Privileged helper tool for seamless blocking
- Screen Time API integration
- Native SwiftUI interface
- iOS companion app
- Usage statistics/graphs
- Multiple profiles (work mode, weekend mode)

## Success Criteria

1. App successfully blocks configured sites when time runs out
2. Time tracking accurately reflects browser usage
3. Override flow provides meaningful friction
4. State persists correctly across sleep/shutdown cycles
5. Clean enough for open-source release
