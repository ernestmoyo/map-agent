"""Session state: ref system, context tracking, and breadcrumb navigation.

Inspired by gstack's @ref element selection — assigns short refs to layers,
files, and artifacts so the agent doesn't need to pass long paths/IDs.

Ref prefixes:
    @L — catalog layers (layer IDs)
    @R — fetched rasters (file paths)
    @B — boundaries (file paths)
    @S — stats CSVs (file paths)
    @P — points/plots (file paths)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_REF_PATTERN = re.compile(r"^@([LRBSP])(\d+)$", re.IGNORECASE)

# Ref prefix → human label
_REF_LABELS: dict[str, str] = {
    "L": "layer",
    "R": "raster",
    "B": "boundary",
    "S": "stats",
    "P": "points/plot",
}


@dataclass
class Breadcrumb:
    """A single step in the drill-down navigation."""

    country: str
    admin_level: int
    name_filter: str | None = None

    def __str__(self) -> str:
        label = self.country
        if self.name_filter:
            label += f" > {self.name_filter}"
        return f"{label} (admin{self.admin_level})"


@dataclass
class SessionState:
    """In-memory session state for the MAP workbench.

    Tracks refs, current geographic focus, and drill-down breadcrumb.
    All state is lost when the MCP server restarts — by design, since
    each Claude Code conversation is a fresh session.
    """

    # Ref stores: prefix → list of (ref_value, human_label)
    _refs: dict[str, list[tuple[str, str]]] = field(default_factory=lambda: {
        "L": [], "R": [], "B": [], "S": [], "P": [],
    })

    # Current geographic focus
    current_country: str | None = None
    current_iso3: str | None = None
    current_admin_level: int = 0
    current_bbox: list[float] | None = None

    # Drill-down breadcrumb
    breadcrumb: list[Breadcrumb] = field(default_factory=list)

    # Last fetched artifacts (for implicit chaining)
    last_raster_path: str | None = None
    last_boundary_path: str | None = None
    last_stats_path: str | None = None
    last_layer_id: str | None = None

    def register_ref(self, prefix: str, value: str, label: str = "") -> str:
        """Register a value and return its ref string (e.g., '@L1').

        Args:
            prefix: One of L, R, B, S, P.
            value: The actual value (layer ID or file path).
            label: Human-readable label for display.

        Returns:
            Ref string like '@L1', '@R2', etc.
        """
        prefix = prefix.upper()
        store = self._refs[prefix]

        # Check if already registered
        for i, (existing_val, _) in enumerate(store):
            if existing_val == value:
                return f"@{prefix}{i + 1}"

        store.append((value, label or value))
        return f"@{prefix}{len(store)}"

    def register_layers(self, layers: list[dict]) -> list[dict]:
        """Register catalog search results and add ref fields.

        Mutates the layer dicts by adding a 'ref' key.
        Returns the same list for chaining.
        """
        for layer in layers:
            layer_id = layer.get("layer_id", "")
            label = layer.get("title") or layer_id
            ref = self.register_ref("L", layer_id, label)
            layer["ref"] = ref
        return layers

    def resolve_ref(self, ref_string: str) -> str | None:
        """Resolve a ref string like '@L1' to its actual value.

        Returns None if the ref doesn't exist.
        """
        match = _REF_PATTERN.match(ref_string.strip())
        if not match:
            return None
        prefix = match.group(1).upper()
        index = int(match.group(2)) - 1  # 1-based to 0-based
        store = self._refs.get(prefix, [])
        if 0 <= index < len(store):
            return store[index][0]
        return None

    def resolve_if_ref(self, value: str) -> str:
        """If value looks like a ref (@L1), resolve it. Otherwise return as-is."""
        if value and value.startswith("@"):
            resolved = self.resolve_ref(value)
            if resolved is not None:
                return resolved
        return value

    def set_focus(
        self,
        country: str | None = None,
        iso3: str | None = None,
        admin_level: int = 0,
        bbox: list[float] | None = None,
        name_filter: str | None = None,
    ) -> None:
        """Update the current geographic focus and breadcrumb."""
        if country:
            self.current_country = country
        if iso3:
            self.current_iso3 = iso3
        self.current_admin_level = admin_level
        if bbox:
            self.current_bbox = bbox

        # Update breadcrumb
        if iso3 or country:
            crumb = Breadcrumb(
                country=iso3 or country or "",
                admin_level=admin_level,
                name_filter=name_filter,
            )
            # Replace if same level exists, otherwise append
            replaced = False
            for i, existing in enumerate(self.breadcrumb):
                if existing.admin_level >= admin_level:
                    self.breadcrumb = self.breadcrumb[:i] + [crumb]
                    replaced = True
                    break
            if not replaced:
                self.breadcrumb.append(crumb)

    def get_status(self) -> dict[str, Any]:
        """Return current session status for display."""
        ref_summary: dict[str, list[dict]] = {}
        for prefix, store in self._refs.items():
            if store:
                ref_summary[_REF_LABELS[prefix]] = [
                    {"ref": f"@{prefix}{i + 1}", "value": label}
                    for i, (_, label) in enumerate(store)
                ]

        return {
            "focus": {
                "country": self.current_country,
                "iso3": self.current_iso3,
                "admin_level": self.current_admin_level,
                "bbox": self.current_bbox,
            },
            "breadcrumb": " → ".join(str(b) for b in self.breadcrumb) or "No navigation yet",
            "refs": ref_summary,
            "last_artifacts": {
                "raster": self.last_raster_path,
                "boundary": self.last_boundary_path,
                "stats": self.last_stats_path,
                "layer_id": self.last_layer_id,
            },
        }

    def clear(self) -> None:
        """Reset all session state."""
        for store in self._refs.values():
            store.clear()
        self.current_country = None
        self.current_iso3 = None
        self.current_admin_level = 0
        self.current_bbox = None
        self.breadcrumb.clear()
        self.last_raster_path = None
        self.last_boundary_path = None
        self.last_stats_path = None
        self.last_layer_id = None


# Module-level singleton
session = SessionState()
