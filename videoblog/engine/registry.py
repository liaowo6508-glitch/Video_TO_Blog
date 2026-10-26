from __future__ import annotations

from collections.abc import Callable
from typing import Any


class PipelineRegistry:
    _pipelines: dict[str, Callable[[], Any]] = {}

    @classmethod
    def register(cls, name: str) -> Callable[[Callable[[], Any]], Callable[[], Any]]:
        def decorator(factory: Callable[[], Any]) -> Callable[[], Any]:
            cls._pipelines[name] = factory
            return factory

        return decorator

    @classmethod
    def get(cls, name: str) -> Any:
        if name not in cls._pipelines:
            raise KeyError(f"Unknown pipeline: {name}")
        return cls._pipelines[name]()

    @classmethod
    def list_names(cls) -> list[str]:
        return sorted(cls._pipelines.keys())
