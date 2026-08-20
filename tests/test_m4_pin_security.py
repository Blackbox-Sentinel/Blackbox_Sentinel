import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "m4-gui-venture", "src"))

from pin_security import validate_pin


def test_default_pin_is_accepted():
    assert validate_pin("1234") is True


def test_wrong_four_digit_pin_is_rejected():
    assert validate_pin("4321") is False


def test_short_and_long_values_are_rejected():
    assert validate_pin("123") is False
    assert validate_pin("12345") is False


def test_configured_pin_can_be_overridden(monkeypatch):
    monkeypatch.setenv("SENTINEL_PIN", "2468")
    assert validate_pin("2468") is True
    assert validate_pin("1234") is False
