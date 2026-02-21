"""Main menu bar application for Social Media Limiter."""

import logging
import re

import rumps

from .blocker import block_sites, is_blocking_active, unblock_sites
from .config import add_blocked_site, load_config, remove_blocked_site, save_config
from .override import close_countdown_window, show_countdown_window
from .state import (
    activate_override,
    decrement_time,
    format_time,
    get_override_remaining_seconds,
    is_override_active,
    load_state,
)
from .tracker import check_current_activity

logger = logging.getLogger(__name__)

# Menu bar icons (using emoji for prototype - replace with proper icons later)
ICON_ACTIVE = "●"  # Green - time remaining
ICON_WARNING = "◐"  # Yellow - low time
ICON_BLOCKED = "○"  # Red - blocked
ICON_OVERRIDE = "⏳"  # Hourglass - override countdown

WARNING_THRESHOLD_SECONDS = 600  # 10 minutes

# Domain validation regex - allows valid domain characters only
# Matches: example.com, sub.example.com, my-site.co.uk
# Rejects: newlines, spaces, special characters that could corrupt hosts file
DOMAIN_REGEX = re.compile(
    r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
)

# Reasonable limits for settings
MAX_DAILY_LIMIT_MINUTES = 1440  # 24 hours
MIN_DAILY_LIMIT_MINUTES = 1


def is_valid_domain(domain: str) -> bool:
    """Validate a domain name for safety and correctness.

    Prevents hosts file injection via newlines, spaces, or special characters.
    """
    if not domain:
        return False

    # Check length (max 253 chars for DNS)
    if len(domain) > 253:
        return False

    # Must have at least one dot
    if "." not in domain:
        return False

    # Check against regex
    if not DOMAIN_REGEX.match(domain):
        return False

    # Additional safety: no control characters or whitespace
    if any(c.isspace() or ord(c) < 32 for c in domain):
        return False

    return True


class SocialLimiterApp(rumps.App):
    """Main menu bar application."""

    def __init__(self):
        super().__init__(ICON_ACTIVE, quit_button=None)

        self.config = load_config()
        self.state = load_state()
        self.override_countdown_active = False

        # Build menu
        self._build_menu()

        # Start tracking timer (every 5 seconds)
        self.timer = rumps.Timer(self._on_tick, 5)
        self.timer.start()

        # Initial state sync
        self._sync_blocking_state()
        self._update_display()

    def _build_menu(self):
        """Build the menu structure."""
        self.time_remaining_item = rumps.MenuItem("Loading...")
        self.usage_item = rumps.MenuItem("Today's usage: calculating...")

        self.blocked_sites_menu = rumps.MenuItem("Blocked Sites")
        self._update_blocked_sites_menu()

        self.add_site_item = rumps.MenuItem("Add Site...", callback=self._on_add_site)

        self.override_item = rumps.MenuItem(
            "Request Override...", callback=self._on_request_override
        )

        self.settings_item = rumps.MenuItem("Settings...", callback=self._on_settings)
        self.quit_item = rumps.MenuItem("Quit", callback=self._on_quit)

        self.menu = [
            self.time_remaining_item,
            self.usage_item,
            None,  # Separator
            self.blocked_sites_menu,
            self.add_site_item,
            None,  # Separator
            self.override_item,
            None,  # Separator
            self.settings_item,
            self.quit_item,
        ]

    def _update_blocked_sites_menu(self):
        """Update the blocked sites submenu."""
        self.blocked_sites_menu.clear()

        if not self.config.blocked_sites:
            self.blocked_sites_menu.add(rumps.MenuItem("No sites configured"))
            return

        for site in self.config.blocked_sites:
            item = rumps.MenuItem(site.domain, callback=self._on_toggle_site)
            item.state = 1  # Checkmark shows it's blocked (use int, not bool)
            self.blocked_sites_menu.add(item)

    def _update_display(self):
        """Update the menu bar icon and menu items."""
        self.state = load_state()

        # Update time remaining display
        time_str = format_time(self.state.remaining_seconds)

        if self.state.is_blocked:
            if is_override_active():
                override_remaining = get_override_remaining_seconds()
                self.time_remaining_item.title = f"⏳ Override: {format_time(override_remaining)}"
                self.title = ICON_OVERRIDE
            else:
                self.time_remaining_item.title = "○ Blocked (0:00 remaining)"
                self.title = ICON_BLOCKED
            self.override_item.set_callback(self._on_request_override)
        elif self.state.remaining_seconds <= WARNING_THRESHOLD_SECONDS:
            self.time_remaining_item.title = f"◐ {time_str} remaining"
            self.title = ICON_WARNING
            self.override_item.set_callback(None)  # Disable when not blocked
        else:
            self.time_remaining_item.title = f"● {time_str} remaining"
            self.title = ICON_ACTIVE
            self.override_item.set_callback(None)  # Disable when not blocked

        # Update usage
        daily_limit = self.config.daily_limit_seconds
        used = daily_limit - self.state.remaining_seconds
        self.usage_item.title = f"Today's usage: {format_time(max(0, used))}"

    def _sync_blocking_state(self):
        """Ensure /etc/hosts matches our state."""
        should_block = self.state.is_blocked and not is_override_active()
        currently_blocking = is_blocking_active()

        if should_block and not currently_blocking:
            domains = self.config.get_all_blocked_domains()
            hosts_ok, dns_ok = block_sites(domains)
            if not hosts_ok:
                logger.warning("Failed to modify hosts file for blocking")
            elif not dns_ok:
                logger.warning("Hosts modified but DNS flush failed")
        elif not should_block and currently_blocking:
            hosts_ok, dns_ok = unblock_sites()
            if not hosts_ok:
                logger.warning("Failed to modify hosts file for unblocking")
            elif not dns_ok:
                logger.warning("Hosts modified but DNS flush failed")

    def _on_tick(self, _):
        """Called every 5 seconds to track time."""
        try:
            self.state = load_state()
            self.config = load_config()

            # Check if override expired
            if self.state.is_blocked and not is_override_active():
                self._sync_blocking_state()

            # If not blocked (or override active), check browser activity
            if not self.state.is_blocked or is_override_active():
                blocked_domains = self.config.get_all_blocked_domains()

                if check_current_activity(blocked_domains):
                    # User is on a blocked site, decrement time
                    self.state = decrement_time(5)

                    # Check if we just ran out of time
                    if self.state.is_blocked and not is_override_active():
                        self._sync_blocking_state()
                        rumps.notification(
                            title="Social Media Limiter",
                            subtitle="Time's up!",
                            message="Your daily limit has been reached. Sites are now blocked.",
                        )

            self._update_display()
        except Exception as e:
            logger.error(f"Error in tick handler: {e}")

    def _on_add_site(self, _):
        """Handle Add Site menu item."""
        response = rumps.Window(
            title="Add Blocked Site",
            message="Enter the domain to block (e.g., youtube.com):",
            default_text="",
            ok="Add",
            cancel="Cancel",
            dimensions=(300, 24),
        ).run()

        if response.clicked and response.text.strip():
            domain = response.text.strip().lower()

            # Remove http/https/www if present
            domain = domain.replace("https://", "").replace("http://", "")
            if domain.startswith("www."):
                domain = domain[4:]
            domain = domain.split("/")[0]  # Remove path
            domain = domain.split("?")[0]  # Remove query string
            domain = domain.split("#")[0]  # Remove fragment

            # Validate domain to prevent hosts file injection
            if not is_valid_domain(domain):
                rumps.alert(
                    title="Invalid Domain",
                    message=(
                        "Please enter a valid domain (e.g., youtube.com).\n\n"
                        "Domain must contain only letters, numbers, hyphens, and dots."
                    ),
                )
                return

            self.config = add_blocked_site(domain)
            self._update_blocked_sites_menu()

            rumps.notification(
                title="Site Added",
                subtitle=domain,
                message=f"{domain} has been added to your blocked list.",
            )

    def _on_toggle_site(self, sender):
        """Handle toggling a blocked site."""
        domain = sender.title

        # Confirm removal
        response = rumps.alert(
            title="Remove Blocked Site?",
            message=f"Remove {domain} from blocked sites?",
            ok="Remove",
            cancel="Cancel",
        )

        if response == 1:  # OK clicked
            self.config = remove_blocked_site(domain)
            self._update_blocked_sites_menu()
            self._sync_blocking_state()

    def _on_request_override(self, _):
        """Handle override request."""
        if not self.state.is_blocked:
            rumps.alert(
                title="Not Blocked",
                message="Override is only available when sites are blocked.",
            )
            return

        if self.override_countdown_active:
            rumps.alert(
                title="Countdown Active",
                message="An override countdown is already in progress.",
            )
            return

        # Confirm override request
        response = rumps.alert(
            title="Request Override",
            message=(
                f"This will start a {self.config.override_delay_seconds // 60}-minute countdown.\n\n"
                f"After the countdown, you'll get {self.config.override_grant_seconds // 60} minutes "
                f"of access.\n\nProceed?"
            ),
            ok="Start Countdown",
            cancel="Cancel",
        )

        if response == 1:  # OK clicked
            self._start_override_countdown()

    def _start_override_countdown(self):
        """Start the override countdown window."""
        self.override_countdown_active = True

        def on_complete():
            self.override_countdown_active = False
            # Grant override
            self.state = activate_override(self.config.override_grant_seconds)
            self._sync_blocking_state()
            self._update_display()

            rumps.notification(
                title="Override Active",
                subtitle=f"{self.config.override_grant_seconds // 60} minutes granted",
                message="Sites are temporarily unblocked.",
            )

        def on_cancel():
            self.override_countdown_active = False
            self._update_display()

        show_countdown_window(
            self.config.override_delay_seconds,
            on_complete,
            on_cancel,
        )

    def _on_settings(self, _):
        """Handle Settings menu item."""
        # Simple settings via alerts for prototype
        # Full settings window would be added in Swift version

        response = rumps.Window(
            title="Daily Time Limit",
            message=f"Enter daily limit in minutes ({MIN_DAILY_LIMIT_MINUTES}-{MAX_DAILY_LIMIT_MINUTES}):",
            default_text=str(self.config.daily_limit_seconds // 60),
            ok="Save",
            cancel="Cancel",
            dimensions=(100, 24),
        ).run()

        if response.clicked and response.text.strip():
            try:
                minutes = int(response.text.strip())

                if minutes < MIN_DAILY_LIMIT_MINUTES:
                    raise ValueError(f"Must be at least {MIN_DAILY_LIMIT_MINUTES} minute")
                if minutes > MAX_DAILY_LIMIT_MINUTES:
                    raise ValueError(f"Must be at most {MAX_DAILY_LIMIT_MINUTES} minutes (24 hours)")

                self.config.daily_limit_seconds = minutes * 60
                save_config(self.config)

                rumps.notification(
                    title="Settings Saved",
                    subtitle="Daily limit updated",
                    message=f"New daily limit: {minutes} minutes",
                )
            except ValueError as e:
                rumps.alert(
                    title="Invalid Input",
                    message=str(e),
                )

    def _on_quit(self, _):
        """Handle Quit menu item."""
        # Stop the timer first
        if self.timer:
            self.timer.stop()

        # Clean up countdown window
        close_countdown_window()

        # Note: We intentionally leave blocks in place
        # This prevents bypassing by just quitting the app
        # The app should be run at startup

        rumps.quit_application()


def main():
    """Entry point for the application."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    app = SocialLimiterApp()
    app.run()


if __name__ == "__main__":
    main()
