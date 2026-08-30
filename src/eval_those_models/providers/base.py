"""Provider contract shared by model API adapters."""

from __future__ import annotations

from typing import Any, Protocol


class Provider(Protocol):
    """Interface implemented by each execution backend."""

    def list_models(self) -> list[dict[str, Any]]: ...

    def estimate(self, case: dict[str, Any]) -> dict[str, Any]: ...

    def generate(self, case: dict[str, Any]) -> dict[str, Any]: ...

    def get_generation_metadata(self, generation_id: str) -> dict[str, Any] | None: ...
