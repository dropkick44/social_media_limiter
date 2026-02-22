"""Tests for state management module."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from src.state import (
    State,
    calculate_next_reset,
    format_time,
    load_state,
    save_state,
)


class TestState:
    """Tests for State class."""

    def test_to_dict(self):
        """Test serialization to dictionary."""
        now = datetime.now()
        state = State(
            remaining_seconds=1800,
            last_active=now,
            next_reset=now + timedelta(hours=12),
            is_blocked=False,
            override_active_until=None,
        )

        data = state.to_dict()

        assert data["remaining_seconds"] == 1800
        assert data["is_blocked"] is False
        assert data["override_active_until"] is None

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "remaining_seconds": 900,
            "last_active": "2026-02-21T14:30:00",
            "next_reset": "2026-02-22T00:00:00",
            "is_blocked": True,
            "override_active_until": None,
        }

        state = State.from_dict(data)

        assert state.remaining_seconds == 900
        assert state.is_blocked is True
        assert state.override_active_until is None


class TestCalculateNextReset:
    """Tests for next reset calculation."""

    def test_reset_later_today(self):
        """Test when reset time is later today."""
        from_time = datetime(2026, 2, 21, 10, 0, 0)  # 10 AM
        reset_time = "18:00"  # 6 PM

        next_reset = calculate_next_reset(reset_time, from_time)

        assert next_reset.date() == from_time.date()
        assert next_reset.hour == 18
        assert next_reset.minute == 0

    def test_reset_already_passed_today(self):
        """Test when reset time already passed today."""
        from_time = datetime(2026, 2, 21, 20, 0, 0)  # 8 PM
        reset_time = "18:00"  # 6 PM

        next_reset = calculate_next_reset(reset_time, from_time)

        assert next_reset.date() == (from_time + timedelta(days=1)).date()
        assert next_reset.hour == 18

    def test_midnight_reset(self):
        """Test midnight reset time."""
        from_time = datetime(2026, 2, 21, 14, 0, 0)  # 2 PM
        reset_time = "00:00"

        next_reset = calculate_next_reset(reset_time, from_time)

        assert next_reset.date() == datetime(2026, 2, 22).date()
        assert next_reset.hour == 0
        assert next_reset.minute == 0


class TestFormatTime:
    """Tests for time formatting."""

    def test_format_seconds(self):
        """Test formatting just seconds."""
        assert format_time(45) == "0:45"

    def test_format_minutes_seconds(self):
        """Test formatting minutes and seconds."""
        assert format_time(125) == "2:05"
        assert format_time(600) == "10:00"

    def test_format_hours(self):
        """Test formatting hours."""
        assert format_time(3665) == "1:01:05"

    def test_format_negative(self):
        """Test formatting negative values."""
        assert format_time(-10) == "0:00"


class TestStatePersistence:
    """Tests for state load/save functions."""

    def test_load_state_creates_fresh(self):
        """Test that loading state creates fresh state when file doesn't exist."""
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch("src.state.get_config_dir", return_value=Path(tmpdir)),
            patch("src.config.get_config_dir", return_value=Path(tmpdir)),
        ):
            state = load_state()

            assert state.remaining_seconds == 1800  # Default limit
            assert state.is_blocked is False

    def test_save_and_load_state(self):
        """Test saving and loading state."""
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch("src.state.get_config_dir", return_value=Path(tmpdir)),
            patch("src.config.get_config_dir", return_value=Path(tmpdir)),
        ):
            now = datetime.now()
            original = State(
                remaining_seconds=500,
                last_active=now,
                next_reset=now + timedelta(hours=6),
                is_blocked=True,
                override_active_until=None,
            )

            save_state(original)
            loaded = load_state()

            assert loaded.remaining_seconds == 500
            assert loaded.is_blocked is True
