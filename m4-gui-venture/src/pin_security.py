"""PIN validation helpers for the simulation-only M4 dashboard.

The default PIN exists only for the controlled semester-project simulation.
For local demos it can be overridden with SENTINEL_PIN.
"""

from __future__ import annotations

import hmac
import os

DEFAULT_PIN = "1234"


def configured_pin() -> str:
    """Return the configured demo PIN, falling back to the documented default."""
    value = os.getenv("SENTINEL_PIN", DEFAULT_PIN)
    return value if value else DEFAULT_PIN


def validate_pin(candidate: str, expected: str | None = None) -> bool:
    """Validate an exact PIN using constant-time comparison.

    This is a simulation control, not a production authentication system. The
    exact-length check prevents the browser-style ``any four digits`` bug.
    """
    candidate = str(candidate)
    expected = configured_pin() if expected is None else str(expected)
    return len(candidate) == len(expected) and hmac.compare_digest(candidate, expected)
