# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Versioning Scheme

This project uses **X.Y.Z** versioning:
- **X (Major)**: Breaking changes, major rewrites (e.g., Swift rewrite)
- **Y (Feature)**: New features, significant enhancements
- **Z (Patch)**: Bug fixes, security patches, minor improvements

## [Unreleased]

## [0.2.0] - 2026-02-22

### Added
- **Background browser tracking**: Now monitors ALL running browsers, not just the frontmost app. YouTube playing in Brave while you're in Terminal will still count toward your daily limit.
- **Brave Browser support**: Full AppleScript integration for Brave
- **Microsoft Edge support**: Full AppleScript integration for Edge
- **Security Guide**: Comprehensive `docs/SECURITY_GUIDE.md` documenting:
  - What permissions are granted and why
  - Security implications of AppleScript access
  - Commands to revoke all permissions
  - Complete reset/cleanup instructions
- **Settings reset option**: When changing daily limit, option to reset remaining time

### Fixed
- **Usage calculation bug**: "Today's usage" no longer shows incorrect values when daily limit is changed
- Remaining time now properly capped to daily limit
- Menu item state uses proper integer values instead of booleans

### Changed
- Browser detection now checks all browsers simultaneously instead of only frontmost

## [0.1.2] - 2026-02-22

### Fixed
- Code style improvements from ruff linter
- Combined nested `with` statements in tests
- Updated imports to use `collections.abc.Callable`
- Simplified boolean returns and loop constructs

## [0.1.1] - 2026-02-22

### Security
- **Fixed command injection vulnerability** in hosts file manipulation (shlex.quote)
- Added domain validation regex to prevent hosts file injection attacks
- Input sanitization for all user-provided domain names

### Fixed
- **Race conditions**: Added file locking (fcntl.flock) to state.py and config.py
- **Thread safety**: Added proper locking in override countdown window
- **Temp file cleanup**: Ensured cleanup in all code paths with try/finally
- **Memory leak**: Clear callbacks after use in override window, proper cleanup
- **Timer cleanup**: Stop timer on app quit to prevent resource leaks
- **DNS flush handling**: Properly report DNS flush failures
- **JSON error handling**: Graceful fallback to defaults on corrupted files
- **Atomic file writes**: Use temp file + rename to prevent corruption on crash
- **Reset time validation**: Validate HH:MM format with fallback to midnight
- **Settings bounds**: Daily limit now bounded between 1-1440 minutes

### Added
- Logging throughout the codebase for debugging
- Error handling in tick handler

## [0.1.0] - 2026-02-21

### Added
- Initial release of Social Media Limiter prototype
- **Menu bar application** using Python + rumps framework
- **System-level blocking** via `/etc/hosts` modification
- **Daily time budget**: Shared pool across all blocked sites
- **Browser detection**: Safari, Chrome, Firefox, Arc support via AppleScript
- **Override mechanism**: Time-delayed emergency access with countdown window
- **Sleep/shutdown awareness**: Timestamp-based reset logic survives restarts
- **Configuration persistence**: JSON-based config in `~/.config/social_limiter/`
- **State persistence**: Tracks remaining time, blocked status, overrides
- Pre-configured blocked sites: YouTube, Reddit, Twitter/X, Instagram, TikTok, Facebook
- Menu bar status icons: Active (●), Warning (◐), Blocked (○), Override (⏳)
- Add/remove sites from menu
- Basic settings dialog for daily limit

### Technical
- Python 3.11+ required
- Dependencies: rumps, pyobjc-framework-Cocoa
- Development tools: pytest, ruff, pre-commit
- MIT License

## Project Status

**Current Phase**: Python Prototype (functional)

**What Works**:
- Time tracking when browsing blocked sites
- Background browser monitoring
- System-level blocking via /etc/hosts
- Override mechanism with countdown
- Persistent state across restarts

**Known Limitations**:
- Password prompt required for each block/unblock (prototype limitation)
- Firefox has limited AppleScript support
- Only tracks browser tabs, not native apps
- Override countdown can be bypassed by force-quitting

**Planned (Swift Rewrite)**:
- Native macOS app with proper permissions
- Privileged helper tool (no password prompts)
- Usage statistics and graphs
- Multiple profiles
- iOS companion app
