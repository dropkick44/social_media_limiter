"""State management for Social Media Limiter."""

import fcntl
import json
import logging
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path

from .config import get_config_dir, load_config

logger = logging.getLogger(__name__)

# File lock for thread-safe state operations
_state_lock_fd = None


def _get_lock_path() -> Path:
    """Get the lock file path."""
    return get_config_dir() / "state.lock"


def _acquire_lock() -> int:
    """Acquire exclusive lock for state file operations."""
    global _state_lock_fd
    lock_path = _get_lock_path()
    _state_lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)
    fcntl.flock(_state_lock_fd, fcntl.LOCK_EX)
    return _state_lock_fd


def _release_lock() -> None:
    """Release the state file lock."""
    global _state_lock_fd
    if _state_lock_fd is not None:
        fcntl.flock(_state_lock_fd, fcntl.LOCK_UN)
        os.close(_state_lock_fd)
        _state_lock_fd = None


@dataclass
class State:
    """Application runtime state."""

    remaining_seconds: int
    last_active: datetime
    next_reset: datetime
    is_blocked: bool = False
    override_active_until: datetime | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "remaining_seconds": self.remaining_seconds,
            "last_active": self.last_active.isoformat(),
            "next_reset": self.next_reset.isoformat(),
            "is_blocked": self.is_blocked,
            "override_active_until": (
                self.override_active_until.isoformat() if self.override_active_until else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "State":
        """Create from dictionary."""
        override_until = data.get("override_active_until")
        return cls(
            remaining_seconds=data["remaining_seconds"],
            last_active=datetime.fromisoformat(data["last_active"]),
            next_reset=datetime.fromisoformat(data["next_reset"]),
            is_blocked=data.get("is_blocked", False),
            override_active_until=(
                datetime.fromisoformat(override_until) if override_until else None
            ),
        )


def get_state_path() -> Path:
    """Get the state file path."""
    return get_config_dir() / "state.json"


def parse_reset_time(reset_time_str: str) -> time | None:
    """Parse reset time string (HH:MM) with validation.

    Returns None if invalid.
    """
    try:
        parts = reset_time_str.split(":")
        if len(parts) != 2:
            return None
        hour, minute = int(parts[0]), int(parts[1])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return None
        return time(hour, minute)
    except (ValueError, AttributeError):
        return None


def calculate_next_reset(reset_time_str: str, from_time: datetime | None = None) -> datetime:
    """Calculate the next reset datetime based on reset time string (HH:MM)."""
    if from_time is None:
        from_time = datetime.now()

    # Parse reset time with validation
    reset_time = parse_reset_time(reset_time_str)
    if reset_time is None:
        logger.warning(f"Invalid reset time '{reset_time_str}', defaulting to midnight")
        reset_time = time(0, 0)

    # Create reset datetime for today
    today_reset = datetime.combine(from_time.date(), reset_time)

    # If we've already passed reset time today, next reset is tomorrow
    if from_time >= today_reset:
        return today_reset + timedelta(days=1)

    return today_reset


def _create_default_state(config) -> State:
    """Create a fresh default state."""
    now = datetime.now()
    return State(
        remaining_seconds=config.daily_limit_seconds,
        last_active=now,
        next_reset=calculate_next_reset(config.reset_time, now),
        is_blocked=False,
        override_active_until=None,
    )


def load_state() -> State:
    """Load state from file, checking for reset if needed.

    Thread-safe with file locking.
    """
    state_path = get_state_path()
    config = load_config()
    now = datetime.now()

    _acquire_lock()
    try:
        if not state_path.exists():
            # Create fresh state
            state = _create_default_state(config)
            _save_state_unlocked(state)
            return state

        try:
            with open(state_path) as f:
                data = json.load(f)
            state = State.from_dict(data)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Corrupted state file, resetting: {e}")
            state = _create_default_state(config)
            _save_state_unlocked(state)
            return state

        # Check if we need to reset
        if now >= state.next_reset:
            # Reset the state
            state = State(
                remaining_seconds=config.daily_limit_seconds,
                last_active=now,
                next_reset=calculate_next_reset(config.reset_time, now),
                is_blocked=False,
                override_active_until=None,
            )
            _save_state_unlocked(state)

        # Check if override has expired
        if state.override_active_until and now >= state.override_active_until:
            state.override_active_until = None
            # Re-block if budget was exhausted
            if state.remaining_seconds <= 0:
                state.is_blocked = True
            _save_state_unlocked(state)

        return state
    finally:
        _release_lock()


def _save_state_unlocked(state: State) -> None:
    """Save state to file atomically. Must be called with lock held."""
    state_path = get_state_path()
    dir_path = state_path.parent

    # Write to temp file first, then atomically rename
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", dir=dir_path, delete=False, suffix=".tmp"
        ) as f:
            json.dump(state.to_dict(), f, indent=2)
            temp_path = f.name

        # Atomic rename on POSIX
        os.rename(temp_path, state_path)
    except OSError as e:
        logger.error(f"Failed to save state: {e}")
        # Clean up temp file if it exists
        if "temp_path" in locals():
            Path(temp_path).unlink(missing_ok=True)
        raise


def save_state(state: State) -> None:
    """Save state to file atomically. Thread-safe with file locking."""
    _acquire_lock()
    try:
        _save_state_unlocked(state)
    finally:
        _release_lock()


def decrement_time(seconds: int = 5) -> State:
    """Decrement remaining time and return updated state. Thread-safe."""
    _acquire_lock()
    try:
        # Load state without acquiring lock again (we already hold it)
        state_path = get_state_path()
        config = load_config()
        now = datetime.now()

        if not state_path.exists():
            state = _create_default_state(config)
        else:
            try:
                with open(state_path) as f:
                    data = json.load(f)
                state = State.from_dict(data)
            except (json.JSONDecodeError, KeyError, ValueError):
                state = _create_default_state(config)

        # Check for reset
        if now >= state.next_reset:
            state = _create_default_state(config)

        if state.remaining_seconds > 0 and not state.is_blocked:
            state.remaining_seconds = max(0, state.remaining_seconds - seconds)
            state.last_active = now

            # Check if budget exhausted
            if state.remaining_seconds <= 0:
                state.is_blocked = True

            _save_state_unlocked(state)

        return state
    finally:
        _release_lock()


def activate_override(grant_seconds: int) -> State:
    """Activate an override, granting temporary access. Thread-safe."""
    _acquire_lock()
    try:
        state_path = get_state_path()
        config = load_config()
        now = datetime.now()

        if not state_path.exists():
            state = _create_default_state(config)
        else:
            try:
                with open(state_path) as f:
                    data = json.load(f)
                state = State.from_dict(data)
            except (json.JSONDecodeError, KeyError, ValueError):
                state = _create_default_state(config)

        state.is_blocked = False
        state.override_active_until = now + timedelta(seconds=grant_seconds)
        state.last_active = now

        _save_state_unlocked(state)
        return state
    finally:
        _release_lock()


def is_override_active() -> bool:
    """Check if an override is currently active."""
    state = load_state()
    if state.override_active_until is None:
        return False
    return datetime.now() < state.override_active_until


def get_override_remaining_seconds() -> int:
    """Get remaining seconds in current override, or 0 if not active."""
    state = load_state()
    if state.override_active_until is None:
        return 0

    remaining = (state.override_active_until - datetime.now()).total_seconds()
    return max(0, int(remaining))


def format_time(seconds: int) -> str:
    """Format seconds as human-readable time string."""
    if seconds < 0:
        seconds = 0

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
