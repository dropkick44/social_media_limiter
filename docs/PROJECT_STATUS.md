# Project Status

**Last Updated**: 2026-02-22
**Current Version**: 0.2.0
**Phase**: Python Prototype (Functional)

## Overview

Social Media Limiter is a macOS menu bar application that helps users limit time spent on addictive social media and streaming websites. It uses system-level blocking via `/etc/hosts` for hard-to-bypass enforcement.

## Current State

### What's Working

| Feature | Status | Notes |
|---------|--------|-------|
| Menu bar app | ✅ Working | Python + rumps framework |
| Time tracking | ✅ Working | Tracks active browser tabs every 5 seconds |
| Background tracking | ✅ Working | Monitors all browsers, not just frontmost |
| System blocking | ✅ Working | Modifies /etc/hosts with sudo |
| Override mechanism | ✅ Working | 5-min countdown, grants 10-min access |
| State persistence | ✅ Working | Survives sleep/shutdown/restart |
| Settings UI | ✅ Working | Change daily limit with reset option |
| Add/remove sites | ✅ Working | Via menu bar dropdown |

### Supported Browsers

| Browser | Detection | Notes |
|---------|-----------|-------|
| Safari | ✅ Full | AppleScript |
| Chrome | ✅ Full | AppleScript |
| Brave | ✅ Full | AppleScript |
| Edge | ✅ Full | AppleScript |
| Arc | ✅ Full | AppleScript |
| Firefox | ⚠️ Limited | Firefox has limited AppleScript support |

### Known Limitations

1. **Password prompts**: Each block/unblock requires sudo authentication
2. **Bypass possible**: User can refuse to enter password
3. **Browser-only**: Native apps (YouTube app) not tracked
4. **Active tab only**: Background tabs in same browser not tracked
5. **Override bypass**: Force-quitting app resets countdown

## Architecture

```
┌─────────────────────────────────────────┐
│          Menu Bar App (rumps)           │
│  - Display remaining time               │
│  - Settings, add/remove sites           │
│  - Override request                     │
└─────────────────┬───────────────────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
    ▼             ▼             ▼
┌────────┐  ┌──────────┐  ┌──────────┐
│Tracker │  │ Blocker  │  │ Override │
│        │  │          │  │          │
│AppleSc-│  │/etc/hosts│  │Countdown │
│ript to │  │modificat-│  │window    │
│browsers│  │ion       │  │(PyObjC)  │
└────────┘  └──────────┘  └──────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
    ▼             ▼             ▼
┌────────┐  ┌──────────┐  ┌──────────┐
│Config  │  │  State   │  │  Logs    │
│.json   │  │  .json   │  │          │
└────────┘  └──────────┘  └──────────┘
```

## File Structure

```
social_media_limiter/
├── src/
│   ├── __init__.py      # Version: 0.2.0
│   ├── app.py           # Main menu bar application
│   ├── blocker.py       # /etc/hosts manipulation
│   ├── config.py        # Configuration management
│   ├── override.py      # Countdown window (PyObjC)
│   ├── state.py         # State persistence
│   └── tracker.py       # Browser URL detection
├── tests/
│   ├── test_config.py   # 9 tests
│   ├── test_state.py    # 11 tests
│   └── test_tracker.py  # 13 tests
├── docs/
│   ├── plans/           # Design documents
│   ├── SECURITY_GUIDE.md
│   └── PROJECT_STATUS.md
├── CHANGELOG.md
├── README.md
├── pyproject.toml
└── LICENSE (MIT)
```

## Test Coverage

- **Total tests**: 33
- **All passing**: ✅
- **Linting**: ruff (all checks pass)

## Version History

| Version | Date | Type | Summary |
|---------|------|------|---------|
| 0.1.0 | 2026-02-21 | Feature | Initial prototype release |
| 0.1.1 | 2026-02-22 | Security | Fixed command injection, race conditions |
| 0.1.2 | 2026-02-22 | Patch | Linting fixes |
| 0.2.0 | 2026-02-22 | Feature | Background tracking, Brave/Edge support |

## Next Steps (Roadmap)

### Short Term (Python Prototype)
- [ ] Add usage history/statistics view
- [ ] Improve Firefox support (if possible)
- [ ] Add system tray notifications for warnings
- [ ] Launch at login option

### Medium Term (Swift Rewrite)
- [ ] Rewrite in Swift/SwiftUI for native experience
- [ ] Implement privileged helper tool (no password prompts)
- [ ] Code signing and notarization
- [ ] Proper sandboxing

### Long Term
- [ ] Usage statistics and graphs
- [ ] Multiple profiles (work, weekend, etc.)
- [ ] Schedule-based blocking
- [ ] iOS companion app
- [ ] Cross-device sync

## Development Setup

```bash
# Clone
git clone https://github.com/dropkick44/social_media_limiter.git
cd social_media_limiter

# Setup (requires Python 3.11+)
python3.11 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Run
social-limiter

# Test
pytest -v

# Lint
ruff check .
```

## Configuration

Config stored at: `~/.config/social_limiter/config.json`

```json
{
  "daily_limit_seconds": 1800,
  "reset_time": "00:00",
  "override_delay_seconds": 300,
  "override_grant_seconds": 600,
  "blocked_sites": [
    {"domain": "youtube.com", "subdomains": ["www", "m"]},
    ...
  ]
}
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Run tests: `pytest -v`
4. Run linter: `ruff check .`
5. Submit PR

## License

MIT License - see LICENSE file
