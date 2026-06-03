"""Aegis middleware library for splunklib.ai (Surface 1)."""

from aegis_mw._base import (
    SafetyAgentMiddleware,
    SafetySubagentMiddleware,
    SafetyToolMiddleware,
)
from aegis_mw.config import Config
from aegis_mw.model_middleware import SafetyModelMiddleware
from aegis_mw.profiles import Profile

__version__ = "0.1.0"
__all__ = [
    "Config",
    "Profile",
    "SafetyAgentMiddleware",
    "SafetyModelMiddleware",
    "SafetySubagentMiddleware",
    "SafetyToolMiddleware",
]
