"""Spec key canonicalisation (aliases are configuration, not code)."""

from __future__ import annotations

from collections.abc import Mapping


class SpecKeyResolver:
    def __init__(self, aliases: Mapping[str, tuple[str, ...]]) -> None:
        self._map: dict[str, str] = {}
        for canonical, alts in aliases.items():
            canon = self.fold(canonical)
            self._map[canon] = canon
            for alt in alts:
                self._map.setdefault(self.fold(alt), canon)

    @staticmethod
    def fold(key: str) -> str:
        return " ".join(key.casefold().split())

    def canonical(self, key: str) -> str:
        folded = self.fold(key)
        return self._map.get(folded, folded)

    def index(self, specs: Mapping[str, str]) -> dict[str, str]:
        """Map canonical key -> value (first occurrence wins)."""
        out: dict[str, str] = {}
        for k, v in specs.items():
            out.setdefault(self.canonical(k), v)
        return out
