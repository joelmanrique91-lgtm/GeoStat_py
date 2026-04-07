"""Cache for geometry/scene derivations keyed by spatial context signature."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1
from typing import Any


@dataclass(frozen=True)
class GeometryCacheKey:
    dataset_signature: str
    active_domain: str
    active_variable: str
    view_mode: str
    filters_signature: str


class GeometryCacheService:
    def __init__(self) -> None:
        self._storage: dict[GeometryCacheKey, Any] = {}

    def build_key(
        self,
        *,
        dataset_signature: str,
        active_domain: str,
        active_variable: str,
        view_mode: str,
        filters: dict[str, object] | None = None,
    ) -> GeometryCacheKey:
        filters_payload = ""
        if filters:
            normalized = [f"{k}={filters[k]}" for k in sorted(filters)]
            filters_payload = "|".join(normalized)
        filters_signature = sha1(filters_payload.encode("utf-8")).hexdigest() if filters_payload else ""
        return GeometryCacheKey(
            dataset_signature=str(dataset_signature),
            active_domain=str(active_domain or ""),
            active_variable=str(active_variable or ""),
            view_mode=str(view_mode or ""),
            filters_signature=filters_signature,
        )

    def get(self, key: GeometryCacheKey):
        return self._storage.get(key)

    def put(self, key: GeometryCacheKey, value: Any) -> None:
        self._storage[key] = value

    def invalidate(self, *, dataset_signature: str | None = None) -> None:
        if dataset_signature is None:
            self._storage.clear()
            return
        for key in list(self._storage.keys()):
            if key.dataset_signature == dataset_signature:
                self._storage.pop(key, None)

    def size(self) -> int:
        return len(self._storage)
