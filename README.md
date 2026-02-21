# Social Media Limiter

A macOS menu bar app that helps you limit time spent on addictive social media and streaming websites.

## Features

- **System-level blocking** via `/etc/hosts` - works across all browsers
- **Daily time budget** - shared pool across all blocked sites
- **Override mechanism** - emergency access with time-delayed friction
- **Browser detection** - tracks time only when you're actively browsing blocked sites
- **Sleep/shutdown aware** - correctly resets at midnight even if your Mac was off

## Installation

### Requirements

- macOS 12.0 or later
- Python 3.11 or later

### Setup

```bash
# Clone the repository
git clone https://github.com/dropkick44/social_media_limiter.git
cd social_media_limiter

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Install pre-commit hooks (for development)
pre-commit install
```

## Usage

### Running the app

```bash
# Activate virtual environment if not already
source venv/bin/activate

# Run the app
social-limiter
```

The app will appear in your menu bar with a status indicator.

### Menu Bar Icons

| Icon | Status |
|------|--------|
| ● | Time remaining, sites accessible |
| ◐ | Under 10 minutes remaining |
| ○ | Blocked - daily limit reached |
| ⏳ | Override countdown in progress |

### Configuration

Configuration is stored in `~/.config/social_limiter/config.json`:

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
    }
  ],
  "launch_at_login": false
}
```

### Adding/Removing Sites

- Click the menu bar icon → "Add Site..." to block a new domain
- Click the menu bar icon → "Blocked Sites" → click a site to remove it

### Override (Emergency Access)

When blocked:
1. Click "Request Override..."
2. Wait through the countdown (default: 5 minutes)
3. Receive temporary access (default: 10 minutes)
4. Repeat for more time

The waiting period is intentional - it kills most impulse browsing urges.

## How It Works

1. **Time Tracking**: The app checks your active browser tab every 5 seconds. If you're on a blocked site, it decrements your remaining daily time.

2. **Blocking**: When your budget hits zero, the app adds entries to `/etc/hosts` that redirect blocked domains to `127.0.0.1`. This requires your admin password.

3. **Reset**: At midnight (configurable), your budget resets and blocks are removed.

4. **Override**: The countdown window ensures you really want access - most urges pass within the waiting period.

## Supported Browsers

- Safari
- Google Chrome
- Firefox (limited support)
- Arc

## Known Limitations

- **Password prompts**: Each block/unblock requires sudo authentication. You could theoretically refuse to enter your password to bypass blocking.
- **Active tab only**: Only tracks time when a blocked site is in your active browser tab. Background tabs aren't tracked.
- **Browsers only**: Native apps (e.g., YouTube app) aren't affected.

## Development

```bash
# Run tests
pytest

# Run linter
ruff check .

# Format code
ruff format .
```

## Future Plans

- Swift/SwiftUI rewrite for native feel
- Privileged helper for seamless blocking (no password prompts)
- Usage statistics and graphs
- iOS companion app
- Multiple profiles (work mode, weekend mode)

## License

MIT License - see [LICENSE](LICENSE) for details.
