"""Browser tab tracking for time monitoring."""

import subprocess
from urllib.parse import urlparse


def get_active_safari_url() -> str | None:
    """Get the URL of the active Safari tab."""
    script = '''
    tell application "System Events"
        if (name of processes) contains "Safari" then
            tell application "Safari"
                if (count of windows) > 0 then
                    return URL of current tab of front window
                end if
            end tell
        end if
    end tell
    return ""
    '''

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=5,
        )
        url = result.stdout.strip()
        return url if url else None
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return None


def get_active_chrome_url() -> str | None:
    """Get the URL of the active Chrome tab."""
    script = '''
    tell application "System Events"
        if (name of processes) contains "Google Chrome" then
            tell application "Google Chrome"
                if (count of windows) > 0 then
                    return URL of active tab of front window
                end if
            end tell
        end if
    end tell
    return ""
    '''

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=5,
        )
        url = result.stdout.strip()
        return url if url else None
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return None


def get_active_firefox_url() -> str | None:
    """Get the URL of the active Firefox tab.

    Note: Firefox requires additional setup for AppleScript access.
    This may not work out of the box.
    """
    script = '''
    tell application "System Events"
        if (name of processes) contains "firefox" then
            tell application "firefox"
                if (count of windows) > 0 then
                    return URL of current tab of front window
                end if
            end tell
        end if
    end tell
    return ""
    '''

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=5,
        )
        url = result.stdout.strip()
        return url if url else None
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return None


def get_active_arc_url() -> str | None:
    """Get the URL of the active Arc browser tab."""
    script = '''
    tell application "System Events"
        if (name of processes) contains "Arc" then
            tell application "Arc"
                if (count of windows) > 0 then
                    return URL of active tab of front window
                end if
            end tell
        end if
    end tell
    return ""
    '''

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=5,
        )
        url = result.stdout.strip()
        return url if url else None
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return None


def get_active_brave_url() -> str | None:
    """Get the URL of the active Brave browser tab."""
    script = '''
    tell application "System Events"
        if (name of processes) contains "Brave Browser" then
            tell application "Brave Browser"
                if (count of windows) > 0 then
                    return URL of active tab of front window
                end if
            end tell
        end if
    end tell
    return ""
    '''

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=5,
        )
        url = result.stdout.strip()
        return url if url else None
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return None


def get_active_edge_url() -> str | None:
    """Get the URL of the active Microsoft Edge tab."""
    script = '''
    tell application "System Events"
        if (name of processes) contains "Microsoft Edge" then
            tell application "Microsoft Edge"
                if (count of windows) > 0 then
                    return URL of active tab of front window
                end if
            end tell
        end if
    end tell
    return ""
    '''

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=5,
        )
        url = result.stdout.strip()
        return url if url else None
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return None


def get_frontmost_app() -> str | None:
    """Get the name of the frontmost application."""
    script = '''
    tell application "System Events"
        return name of first process where frontmost is true
    end tell
    '''

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() or None
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return None


def get_active_browser_url() -> str | None:
    """Get the URL from whichever browser is currently active."""
    frontmost = get_frontmost_app()

    if frontmost is None:
        return None

    frontmost_lower = frontmost.lower()

    if "safari" in frontmost_lower:
        return get_active_safari_url()
    elif "brave" in frontmost_lower:
        return get_active_brave_url()
    elif "chrome" in frontmost_lower:
        return get_active_chrome_url()
    elif "edge" in frontmost_lower:
        return get_active_edge_url()
    elif "firefox" in frontmost_lower:
        return get_active_firefox_url()
    elif "arc" in frontmost_lower:
        return get_active_arc_url()

    return None


def extract_domain(url: str) -> str | None:
    """Extract the domain from a URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Remove port if present
        if ":" in domain:
            domain = domain.split(":")[0]

        return domain if domain else None
    except Exception:
        return None


def is_blocked_site(url: str, blocked_domains: list[str]) -> bool:
    """Check if a URL belongs to a blocked site."""
    domain = extract_domain(url)
    if domain is None:
        return False

    # Direct match
    if domain in blocked_domains:
        return True

    # Check if domain ends with a blocked domain (handles subdomains)
    return any(
        domain == blocked or domain.endswith(f".{blocked}") for blocked in blocked_domains
    )


def get_all_browser_urls() -> list[str]:
    """Get URLs from all running browsers, not just the frontmost one.

    This allows tracking time even when the browser is in the background
    (e.g., YouTube playing while user is in another app).
    """
    urls = []

    # Check each browser that might be running
    browser_checks = [
        get_active_safari_url,
        get_active_chrome_url,
        get_active_brave_url,
        get_active_edge_url,
        get_active_arc_url,
        # Firefox excluded due to limited AppleScript support
    ]

    for get_url in browser_checks:
        try:
            url = get_url()
            if url:
                urls.append(url)
        except Exception:
            continue

    return urls


def check_current_activity(blocked_domains: list[str]) -> bool:
    """Check if user is currently on a blocked site in ANY browser.

    Returns True if any running browser has a blocked site open.
    This includes browsers in the background (e.g., YouTube playing
    while user is in another app).
    """
    # Check all running browsers
    urls = get_all_browser_urls()
    return any(is_blocked_site(url, blocked_domains) for url in urls)
