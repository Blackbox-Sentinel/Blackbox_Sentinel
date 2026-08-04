"""
BlackBox Sentinel — Hardware Abstraction Layer (HAL) Package
"""

from .hal_base import (
    RelayInterface,
    TamperInterface,
    LEDInterface,
    CellularInterface,
    MeshInterface,
    SentinelHAL,
)
from .hal_factory import get_hal, is_raspberry_pi

__all__ = [
    "RelayInterface",
    "TamperInterface",
    "LEDInterface",
    "CellularInterface",
    "MeshInterface",
    "SentinelHAL",
    "get_hal",
    "is_raspberry_pi",
]
