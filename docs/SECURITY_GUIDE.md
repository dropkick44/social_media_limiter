# Security Guide

This document explains the security implications of using Social Media Limiter and provides commands to revoke any permissions you've granted.

## Overview

Social Media Limiter requires certain macOS permissions to function:

1. **Automation/AppleScript access** - To read browser URLs and detect blocked sites
2. **Administrator privileges** - To modify `/etc/hosts` for blocking

## What Permissions Are Granted

### AppleScript/Automation Access

When you allow the app to control browsers, you're granting permission to:

- Read the URL of active browser tabs
- Read tab/window titles
- Potentially navigate or open new tabs (though we don't do this)

**What we actually use:**
```applescript
# We ONLY read the active tab's URL:
return URL of active tab of front window
```

We do NOT access:
- Passwords or saved credentials
- Cookies or session data
- Page content or DOM
- Browsing history
- Bookmarks

### Administrator Privileges

When blocking sites, we modify `/etc/hosts` which requires sudo access. This allows:

- Adding entries to redirect blocked domains to `127.0.0.1`
- Flushing the DNS cache

**We only modify the section between our markers:**
```
# -- SocialLimiter Start --
127.0.0.1    youtube.com
127.0.0.1    www.youtube.com
# -- SocialLimiter End --
```

## Security Considerations

### Terminal App Permissions

If you're running the app from a terminal (like Ghostty, iTerm2, or Terminal.app), the Automation permission is granted to **the terminal app**, not specifically to Social Media Limiter. This means:

- Any script run from that terminal can access the allowed browsers
- The permission persists until you manually revoke it
- Other scripts could potentially abuse this access

**Mitigation:** In the future Swift version, the app will be a standalone `.app` bundle with its own scoped permissions.

### AppleScript Capabilities

AppleScript can be powerful. Depending on the browser, it may be able to:

- Open new tabs/windows
- Navigate to URLs
- Execute JavaScript (in some browsers)
- Access open tabs' URLs and titles

We only use URL reading, but the permission grants broader access.

### Trust Chain

When running from a terminal, you're trusting:
1. Your terminal emulator (Ghostty, iTerm2, etc.)
2. Python and its dependencies
3. Our application code

## Revoking Permissions

### Revoke Automation/AppleScript Access

**Via System Settings (GUI):**
1. Open **System Settings** (or System Preferences on older macOS)
2. Go to **Privacy & Security**
3. Click **Automation**
4. Find your terminal app (e.g., "Ghostty", "Terminal", "iTerm")
5. Uncheck the browsers you want to revoke access for

**Via Terminal:**
```bash
# Reset ALL Automation permissions (requires restart of apps)
tccutil reset AppleEvents

# Or reset for a specific app (e.g., Ghostty)
# Note: This resets ALL automation permissions for that app
tccutil reset AppleEvents com.mitchellh.ghostty

# Common terminal app bundle IDs:
# - Terminal.app: com.apple.Terminal
# - iTerm2: com.googlecode.iterm2
# - Ghostty: com.mitchellh.ghostty
# - Alacritty: org.alacritty
# - Warp: dev.warp.Warp-Stable
```

### Revoke Accessibility Access (if granted)

**Via System Settings:**
1. Open **System Settings**
2. Go to **Privacy & Security**
3. Click **Accessibility**
4. Find and uncheck your terminal app

**Via Terminal:**
```bash
# Reset ALL Accessibility permissions
sudo tccutil reset Accessibility

# Reset for specific app
sudo tccutil reset Accessibility com.mitchellh.ghostty
```

### Remove Hosts File Modifications

If you want to ensure all our blocks are removed from `/etc/hosts`:

```bash
# View current hosts file
cat /etc/hosts

# Remove SocialLimiter entries manually
sudo nano /etc/hosts
# Delete everything between:
# # -- SocialLimiter Start --
# ... (blocked domains)
# # -- SocialLimiter End --

# Or use sed to remove automatically
sudo sed -i '' '/# -- SocialLimiter Start --/,/# -- SocialLimiter End --/d' /etc/hosts

# Flush DNS cache to apply changes
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
```

### Remove App Configuration and State

```bash
# Remove all Social Media Limiter data
rm -rf ~/.config/social_limiter

# This removes:
# - config.json (your settings and blocked sites)
# - state.json (remaining time, last active, etc.)
# - *.lock files (file locks)
```

## Complete Reset Commands

Run all of these to completely reset everything:

```bash
# 1. Stop the app if running
pkill -f social-limiter

# 2. Remove hosts file entries
sudo sed -i '' '/# -- SocialLimiter Start --/,/# -- SocialLimiter End --/d' /etc/hosts
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder

# 3. Remove app data
rm -rf ~/.config/social_limiter

# 4. Reset Automation permissions for your terminal
# (Replace with your terminal's bundle ID)
tccutil reset AppleEvents com.mitchellh.ghostty

# 5. Verify hosts file is clean
grep -i "SocialLimiter" /etc/hosts || echo "Hosts file is clean"

# 6. Verify config is removed
ls ~/.config/social_limiter 2>/dev/null || echo "Config directory removed"
```

## Verifying Current State

### Check Active Permissions

```bash
# List apps with Automation access (requires Full Disk Access)
sqlite3 ~/Library/Application\ Support/com.apple.TCC/TCC.db \
  "SELECT client, allowed FROM access WHERE service='kTCCServiceAppleEvents';" 2>/dev/null

# If you get a permission error, check via System Settings instead
```

### Check Hosts File

```bash
# See if any SocialLimiter entries exist
grep -A 100 "SocialLimiter Start" /etc/hosts
```

### Check App Data

```bash
# List all app data files
ls -la ~/.config/social_limiter/

# View current state
cat ~/.config/social_limiter/state.json 2>/dev/null | python3 -m json.tool

# View current config
cat ~/.config/social_limiter/config.json 2>/dev/null | python3 -m json.tool
```

## Best Practices

1. **Use a dedicated terminal** for running this app if you're concerned about shared permissions

2. **Revoke permissions when not in use** if you're security-conscious

3. **Check the source code** - It's open source, so you can verify exactly what it does

4. **Wait for the Swift version** - The production app will be a signed, sandboxed `.app` bundle with properly scoped permissions

5. **Don't run untrusted scripts** from a terminal that has browser Automation access

## Reporting Security Issues

If you discover a security vulnerability, please:

1. **Do not** open a public GitHub issue
2. Contact the maintainer directly
3. Allow time for a fix before public disclosure

## Future Improvements

The Swift/SwiftUI rewrite will include:

- Standalone `.app` bundle with own permissions
- Privileged helper tool for hosts modification (no repeated password prompts)
- macOS sandbox for additional security
- Code signing and notarization
- Scoped permissions that only apply to our app
