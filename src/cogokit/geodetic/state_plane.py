"""State Plane Coordinate System (SPCS) zone lookup.

Loads zone definitions from the embedded JSON database and provides
lookup by EPSG code, state + zone name, and listing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources

from cogokit.geodetic.proj4 import ProjectionDef, parse_proj4


@dataclass
class StatePlaneZone:
    """A State Plane zone with its projection definition.

    Attributes:
        epsg: EPSG code.
        name: Full zone name (e.g. "NAD83 / California zone 5").
        state: Two-letter state abbreviation.
        zone: Zone name within state (e.g. "5", "Central", "East").
        proj_def: Parsed projection definition.
    """

    epsg: int
    name: str
    state: str
    zone: str
    proj_def: ProjectionDef


# Module-level cache
_zones: dict[int, StatePlaneZone] | None = None


def _load_zones() -> dict[int, StatePlaneZone]:
    """Load and parse all zones from the JSON database."""
    global _zones
    if _zones is not None:
        return _zones

    data_ref = resources.files("cogokit") / "data" / "spcs_zones.json"
    raw = json.loads(data_ref.read_text(encoding="utf-8"))

    _zones = {}
    for epsg_str, entry in raw.items():
        epsg = int(epsg_str)
        proj_def = parse_proj4(entry["proj4"])
        _zones[epsg] = StatePlaneZone(
            epsg=epsg,
            name=entry.get("name", ""),
            state=entry.get("state", ""),
            zone=entry.get("zone", ""),
            proj_def=proj_def,
        )

    return _zones


def get_zone(epsg: int) -> StatePlaneZone:
    """Look up a State Plane zone by EPSG code.

    Parameters:
        epsg: EPSG code (e.g. 26945 for California zone 5 in metres).

    Returns:
        StatePlaneZone with parsed projection definition.

    Raises:
        ValueError: If the EPSG code is not in the database.
    """
    zones = _load_zones()
    if epsg not in zones:
        raise ValueError(f"Unknown SPCS EPSG code: {epsg}")
    return zones[epsg]


def find_zone(state: str, zone: str) -> StatePlaneZone:
    """Look up a State Plane zone by state abbreviation and zone name.

    Parameters:
        state: Two-letter state abbreviation (case-insensitive).
        zone: Zone name (case-insensitive, partial match supported).

    Returns:
        StatePlaneZone matching the query.

    Raises:
        ValueError: If no matching zone is found.
    """
    zones = _load_zones()
    state_upper = state.upper()
    zone_lower = zone.lower()

    for z in zones.values():
        if z.state == state_upper and zone_lower in z.zone.lower():
            return z

    raise ValueError(
        f"State Plane zone not found: state={state!r}, zone={zone!r}"
    )


def list_zones(state: str | None = None) -> list[StatePlaneZone]:
    """List all available State Plane zones, optionally filtered by state.

    Parameters:
        state: Two-letter state abbreviation (case-insensitive).
            If None, returns all zones.

    Returns:
        List of StatePlaneZone objects, sorted by EPSG code.
    """
    zones = _load_zones()
    result = list(zones.values())

    if state is not None:
        state_upper = state.upper()
        result = [z for z in result if z.state == state_upper]

    return sorted(result, key=lambda z: z.epsg)
