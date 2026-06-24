"""Pluggable stem-separation backends."""

from songstem.separation.base import Separator
from songstem.separation.registry import available_backends, get_backend, register_backend

__all__ = ["Separator", "available_backends", "get_backend", "register_backend"]
