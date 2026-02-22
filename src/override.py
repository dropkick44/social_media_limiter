"""Override countdown window for emergency access."""

import logging
import threading
from collections.abc import Callable

import AppKit
import objc
from Foundation import NSObject
from PyObjCTools import AppHelper

logger = logging.getLogger(__name__)


class CountdownWindowController(NSObject):
    """Controller for the countdown window.

    Thread-safe implementation using locks for shared state.
    """

    window = objc.ivar()
    label = objc.ivar()
    progress = objc.ivar()
    cancel_button = objc.ivar()
    remaining_seconds = objc.ivar()
    total_seconds = objc.ivar()

    def initWithSeconds_onComplete_onCancel_(
        self, seconds: int, on_complete: Callable, on_cancel: Callable
    ):
        self = objc.super(CountdownWindowController, self).init()
        if self is None:
            return None

        self.remaining_seconds = seconds
        self.total_seconds = seconds

        # Store callbacks in Python attributes (not objc.ivar) to avoid reference issues
        self._on_complete = on_complete
        self._on_cancel = on_cancel

        # Thread safety
        self._lock = threading.Lock()
        self._cancelled = False
        self._timer = None
        self._closed = False

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
        """Close the window and stop timer. Thread-safe."""
        with self._lock:
            if self._closed:
                return
            self._closed = True

            if self._timer:
                self._timer.cancel()
                self._timer = None

        # Close window on main thread
        if self.window:
            self.window.close()

    def cleanup(self):
        """Clear callbacks to prevent memory leaks."""
        self._on_complete = None
        self._on_cancel = None

    def _start_timer(self):
        """Start the countdown timer."""
        self._tick()

    def _tick(self):
        """Update countdown every second. Called on main thread."""
        with self._lock:
            if self._cancelled or self._closed:
                return

            if self.remaining_seconds <= 0:
                # Countdown complete
                callback = self._on_complete
                self._on_complete = None
                self._on_cancel = None

        if self.remaining_seconds <= 0:
            self.close()
            if callback:
                try:
                    callback()
                except Exception as e:
                    logger.error(f"Error in on_complete callback: {e}")
            _clear_controller()
            return

        # Update UI (must be on main thread)
        self.label.setStringValue_(self._format_time())
        self.progress.setDoubleValue_(self.remaining_seconds)

        # Schedule next tick
        with self._lock:
            if self._cancelled or self._closed:
                return
            self.remaining_seconds -= 1
            self._timer = threading.Timer(1.0, self._schedule_tick)
            self._timer.start()

    def _schedule_tick(self):
        """Schedule tick on main thread."""
        with self._lock:
            if self._cancelled or self._closed:
                return
        AppHelper.callAfter(self._tick)

    @objc.python_method
    def cancelClicked_(self, sender):
        """Handle cancel button click. Called on main thread."""
        callback = None
        with self._lock:
            if self._cancelled or self._closed:
                return
            self._cancelled = True
            callback = self._on_cancel
            self._on_complete = None
            self._on_cancel = None

        self.close()

        if callback:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in on_cancel callback: {e}")

        _clear_controller()


# Global reference to keep controller alive
_current_controller = None
_controller_lock = threading.Lock()


def _clear_controller():
    """Clear the global controller reference."""
    global _current_controller
    with _controller_lock:
        if _current_controller:
            _current_controller.cleanup()
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

    with _controller_lock:
        # Close any existing window
        if _current_controller:
            _current_controller.close()
            _current_controller.cleanup()
            _current_controller = None

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

    with _controller_lock:
        if _current_controller:
            _current_controller.close()
            _current_controller.cleanup()
            _current_controller = None
