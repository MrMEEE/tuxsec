"""
TuxSec Module System

This package provides a plugin-based architecture for security modules.
Each module can be independently enabled/disabled globally and per-agent.
"""

from .base import BaseModule, ModuleCapability, ModuleCommand, ModuleResult
from .registry import ModuleRegistry

__all__ = [
    'BaseModule',
    'ModuleCapability',
    'ModuleCommand',
    'ModuleResult',
    'ModuleRegistry',
]
