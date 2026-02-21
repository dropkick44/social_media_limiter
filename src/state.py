"""State management for Social Media Limiter."""

import json
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path

from .config import get_config_dir, load_config


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


def calculate_next_reset(reset_time_str: str, from_time: datetime | None = None) -> datetime:
    """Calculate the next reset datetime based on reset time string (HH:MM)."""
    if from_time is None:
        from_time = datetime.now()

    # Parse reset time
    hour, minute = map(int, reset_time_str.split(":"))
    reset_time = time(hour, minute)

    # Create reset datetime for today
    today_reset = datetime.combine(from_time.date(), reset_time)

    # If we've already passed reset time today, next reset is tomorrow
    if from_time >= today_reset:
        return today_reset + timedelta(days=1)

    return today_reset


def load_state() -> State:
    """Load state from file, checking for reset if needed."""
    state_path = get_state_path()
    config = load_config()
    now = datetime.now()

    if not state_path.exists():
        # Create fresh state
        return State(
            remaining_seconds=config.daily_limit_seconds,
            last_active=now,
            next_reset=calculate_next_reset(config.reset_time, now),
            is_blocked=False,
            override_active_until=None,
        )

    with open(state_path) as f:
        data = json.load(f)

    state = State.from_dict(data)

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
        save_state(state)

    # Check if override has expired
    if state.override_active_until and now >= state.override_active_until:
        state.override_active_until = None
        # Re-block if budget was exhausted
        if state.remaining_seconds <= 0:
            state.is_blocked = True
        save_state(state)

    return state


def save_state(state: State) -> None:
    """Save state to file."""
    state_path = get_state_path()

    with open(state_path, "w") as f:
        json.dump(state.to_dict(), f, indent=2)


def decrement_time(seconds: int = 5) -> State:
    """Decrement remaining time and return updated state."""
    state = load_state()

    if state.remaining_seconds > 0 and not state.is_blocked:
        state.remaining_seconds = max(0, state.remaining_seconds - seconds)
        state.last_active = datetime.now()

        # Check if budget exhausted
        if state.remaining_seconds <= 0:
            state.is_blocked = True

        save_state(state)

    return state


def activate_override(grant_seconds: int) -> State:
    """Activate an override, granting temporary access."""
    state = load_state()
    now = datetime.now()

    state.is_blocked = False
    state.override_active_until = now + timedelta(seconds=grant_seconds)
    state.last_active = now

    save_state(state)
    return state


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
        return "0:00"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
