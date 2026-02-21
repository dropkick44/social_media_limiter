"""Override countdown window for emergency access."""

import threading
import time
from typing import Callable

import AppKit
import objc
from Foundation import NSObject
from PyObjCTools import AppHelper


class CountdownWindowController(NSObject):
    """Controller for the countdown window."""

    window = objc.ivar()
    label = objc.ivar()
    progress = objc.ivar()
    cancel_button = objc.ivar()
    remaining_seconds = objc.ivar()
    total_seconds = objc.ivar()
    timer = objc.ivar()
    on_complete = objc.ivar()
    on_cancel = objc.ivar()
    cancelled = objc.ivar()

    def initWithSeconds_onComplete_onCancel_(
        self, seconds: int, on_complete: Callable, on_cancel: Callable
    ):
        self = objc.super(CountdownWindowController, self).init()
        if self is None:
            return None

        self.remaining_seconds = seconds
        self.total_seconds = seconds
        self.on_complete = on_complete
        self.on_cancel = on_cancel
        self.cancelled = False
        self.timer = None

        self._create_window()
        return self

    def _create_window(self):
        """Create the countdown window."""
        # Window size and position (centered on screen)
        window_width = 400
        window_height = 200
        screen = AppKit.NSScreen.mainScreen()
        screen_frame = screen.frame()

        x = (screen_frame.size.width - window_width) / 2
        y = (screen_frame.size.height - window_height) / 2

        frame = AppKit.NSMakeRect(x, y, window_width, window_height)

        # Create window - always on top, no close button
        style = (
            AppKit.NSWindowStyleMaskTitled
            | AppKit.NSWindowStyleMaskFullSizeContentView
        )

        self.window = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame,
            style,
            AppKit.NSBackingStoreBuffered,
            False,
        )

        self.window.setTitle_("Override Countdown")
        self.window.setLevel_(AppKit.NSFloatingWindowLevel)
        self.window.setCollectionBehavior_(
            AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces
            | AppKit.NSWindowCollectionBehaviorFullScreenAuxiliary
        )

        # Content view
        content = self.window.contentView()

        # Title label
        title = AppKit.NSTextField.alloc().initWithFrame_(
            AppKit.NSMakeRect(20, 140, 360, 30)
        )
        title.setStringValue_("Waiting to override block...")
        title.setBezeled_(False)
        title.setDrawsBackground_(False)
        title.setEditable_(False)
        title.setSelectable_(False)
        title.setAlignment_(AppKit.NSTextAlignmentCenter)
        title.setFont_(AppKit.NSFont.boldSystemFontOfSize_(16))
        content.addSubview_(title)

        # Countdown label
        self.label = AppKit.NSTextField.alloc().initWithFrame_(
            AppKit.NSMakeRect(20, 90, 360, 40)
        )
        self.label.setStringValue_(self._format_time())
        self.label.setBezeled_(False)
        self.label.setDrawsBackground_(False)
        self.label.setEditable_(False)
        self.label.setSelectable_(False)
        self.label.setAlignment_(AppKit.NSTextAlignmentCenter)
        self.label.setFont_(AppKit.NSFont.monospacedDigitSystemFontOfSize_weight_(36, 0.5))
        content.addSubview_(self.label)

        # Progress bar
        self.progress = AppKit.NSProgressIndicator.alloc().initWithFrame_(
            AppKit.NSMakeRect(40, 70, 320, 10)
        )
        self.progress.setStyle_(AppKit.NSProgressIndicatorStyleBar)
        self.progress.setMinValue_(0)
        self.progress.setMaxValue_(self.total_seconds)
        self.progress.setDoubleValue_(self.remaining_seconds)
        content.addSubview_(self.progress)

        # Cancel button
        self.cancel_button = AppKit.NSButton.alloc().initWithFrame_(
            AppKit.NSMakeRect(150, 20, 100, 32)
        )
        self.cancel_button.setTitle_("Cancel")
        self.cancel_button.setBezelStyle_(AppKit.NSBezelStyleRounded)
        self.cancel_button.setTarget_(self)
        self.cancel_button.setAction_(objc.selector(self.cancelClicked_, signature=b"v@:@"))
        content.addSubview_(self.cancel_button)

    def _format_time(self) -> str:
        """Format remaining seconds as MM:SS."""
        minutes = int(self.remaining_seconds) // 60
        seconds = int(self.remaining_seconds) % 60
        return f"{minutes}:{seconds:02d}"

    def show(self):
        """Show the window and start countdown."""
        self.window.makeKeyAndOrderFront_(None)
        self.window.center()
        self._start_timer()

    def close(self):
        """Close the window and stop timer."""
        if self.timer:
            self.timer.cancel()
            self.timer = None
        self.window.close()

    def _start_timer(self):
        """Start the countdown timer."""
        self._tick()

    def _tick(self):
        """Update countdown every second."""
        if self.cancelled:
            return

        if self.remaining_seconds <= 0:
            self.close()
            if self.on_complete:
                self.on_complete()
            return

        # Update UI
        self.label.setStringValue_(self._format_time())
        self.progress.setDoubleValue_(self.remaining_seconds)

        # Schedule next tick
        self.remaining_seconds -= 1
        self.timer = threading.Timer(1.0, self._schedule_tick)
        self.timer.start()

    def _schedule_tick(self):
        """Schedule tick on main thread."""
        AppHelper.callAfter(self._tick)

    @objc.python_method
    def cancelClicked_(self, sender):
        """Handle cancel button click."""
        self.cancelled = True
        self.close()
        if self.on_cancel:
            self.on_cancel()


# Global reference to keep controller alive
_current_controller = None


def show_countdown_window(
    seconds: int, on_complete: Callable, on_cancel: Callable
) -> CountdownWindowController:
    """Show the countdown window.

    Args:
        seconds: Number of seconds to count down
        on_complete: Called when countdown finishes
        on_cancel: Called if user cancels

    Returns:
        The window controller (keep a reference to prevent garbage collection)
    """
    global _current_controller

    # Close any existing window
    if _current_controller:
        _current_controller.close()

    _current_controller = (
        CountdownWindowController.alloc().initWithSeconds_onComplete_onCancel_(
            seconds, on_complete, on_cancel
        )
    )
    _current_controller.show()

    return _current_controller


def close_countdown_window():
    """Close the countdown window if open."""
    global _current_controller

    if _current_controller:
        _current_controller.close()
        _current_controller = None
