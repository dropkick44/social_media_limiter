"""Main menu bar application for Social Media Limiter."""

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
    save_state,
)
from .tracker import check_current_activity

# Menu bar icons (using emoji for prototype - replace with proper icons later)
ICON_ACTIVE = "●"  # Green - time remaining
ICON_WARNING = "◐"  # Yellow - low time
ICON_BLOCKED = "○"  # Red - blocked
ICON_OVERRIDE = "⏳"  # Hourglass - override countdown

WARNING_THRESHOLD_SECONDS = 600  # 10 minutes


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
            item.state = True  # Checkmark shows it's blocked
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
                self.time_remaining_item.title = f"○ Blocked (0:00 remaining)"
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
        self.usage_item.title = f"Today's usage: {format_time(used)}"

    def _sync_blocking_state(self):
        """Ensure /etc/hosts matches our state."""
        should_block = self.state.is_blocked and not is_override_active()
        currently_blocking = is_blocking_active()

        if should_block and not currently_blocking:
            domains = self.config.get_all_blocked_domains()
            block_sites(domains)
        elif not should_block and currently_blocking:
            unblock_sites()

    def _on_tick(self, _):
        """Called every 5 seconds to track time."""
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

            # Basic validation
            if "." not in domain:
                rumps.alert(
                    title="Invalid Domain",
                    message="Please enter a valid domain (e.g., youtube.com)",
                )
                return

            # Remove http/https/www if present
            domain = domain.replace("https://", "").replace("http://", "")
            domain = domain.replace("www.", "")
            domain = domain.split("/")[0]  # Remove path

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
            message="Enter daily limit in minutes:",
            default_text=str(self.config.daily_limit_seconds // 60),
            ok="Save",
            cancel="Cancel",
            dimensions=(100, 24),
        ).run()

        if response.clicked and response.text.strip():
            try:
                minutes = int(response.text.strip())
                if minutes < 1:
                    raise ValueError("Must be at least 1 minute")

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
        # Clean up: unblock sites before quitting
        close_countdown_window()

        # Note: We intentionally leave blocks in place
        # This prevents bypassing by just quitting the app
        # The app should be run at startup

        rumps.quit_application()


def main():
    """Entry point for the application."""
    app = SocialLimiterApp()
    app.run()


if __name__ == "__main__":
    main()
