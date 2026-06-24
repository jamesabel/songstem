"""Backend registry — maps a name (from settings) to a Separator implementation.

Backends register themselves lazily so importing this module does not pull in heavy ML
dependencies until a backend is actually requested.
"""

from __future__ import annotations

from collections.abc import Callable

from songstem.separation.base import Separator

_FACTORIES: dict[str, Callable[[], Separator]] = {}


def register_backend(name: str, factory: Callable[[], Separator]) -> None:
    """Register a zero-arg factory that builds a Separator named `name`."""
    _FACTORIES[name] = factory


def available_backends() -> list[str]:
    return sorted(_FACTORIES)


def get_backend(name: str) -> Separator:
    try:
        factory = _FACTORIES[name]
    except KeyError:
        raise ValueError(
            f"Unknown separation backend {name!r}; available: {available_backends()}"
        ) from None
    return factory()


def _register_builtins() -> None:
    from songstem.separation.demucs_backend import DemucsSeparator

    register_backend("demucs", DemucsSeparator)


_register_builtins()
