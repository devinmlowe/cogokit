# State Plane CRS Support — Design

**Date:** 2026-02-12
**Status:** Approved

## Summary

Extend the CRS layer beyond geodetic/UTM to support State Plane coordinate systems, arbitrary projected CRS via PROJ4 strings, and all three SPCS projection types (Transverse Mercator, Lambert Conformal Conic, Hotine Oblique Mercator).

## Data Architecture

### Zone Database — `src/cogopro/data/spcs_zones.json`

External JSON file containing all 125 NAD83 SPCS zones. Keyed by EPSG code (string). Each entry stores name, FIPS code, state abbreviation, zone name, unit, and a PROJ4 string as the source of truth for projection parameters.

```json
{
  "2277": {
    "name": "NAD83 / Texas Central (ftUS)",
    "fips": 4203,
    "state": "TX",
    "zone": "Central",
    "unit": "us-ft",
    "proj4": "+proj=lcc +lat_0=29.6666666666667 +lon_0=-100.333333333333 +lat_1=31.8833333333333 +lat_2=30.1166666666667 +x_0=699999.999898399 +y_0=3000000 +ellps=GRS80"
  }
}
```

Zone parameters sourced from epsg.io at development time. The JSON file is loaded lazily on first zone lookup.

### PROJ4 Parser — `cogopro/geodetic/proj4.py`

Parses PROJ4 strings into a `ProjectionDef` dataclass. Handles `+proj=tmerc`, `+proj=lcc`, and `+proj=omerc`. Converts angle parameters from degrees to radians and resolves `+ellps` to existing `Ellipsoid` objects.

```python
@dataclass
class ProjectionDef:
    proj_type: str            # "tmerc", "lcc", "omerc"
    lat_0: float              # latitude of origin (radians)
    lon_0: float              # central meridian (radians)
    k_0: float                # scale factor (1.0 for LCC)
    x_0: float                # false easting (meters)
    y_0: float                # false northing (meters)
    lat_1: float | None       # LCC standard parallel 1 (radians)
    lat_2: float | None       # LCC standard parallel 2 (radians)
    lonc: float | None        # OMerc longitude of center (radians)
    alpha: float | None       # OMerc azimuth of initial line (radians)
    gamma: float | None       # OMerc rectified grid angle (radians)
    ellipsoid: Ellipsoid
```

This parser powers both the zone database and user-supplied custom PROJ4 strings.

## Projection Math

### New: Lambert Conformal Conic (2SP)

`lcc_forward()` and `lcc_inverse()` in `cogopro/geodetic/projections.py`. Standard two-standard-parallel LCC as used by all ~58 SPCS LCC zones. Scale factor is computed from the two standard parallels (not an input). Returns convergence and point scale factor.

### New: Hotine Oblique Mercator

`omerc_forward()` and `omerc_inverse()` in `cogopro/geodetic/projections.py`. Variant B (azimuth of initial line) as used by SPCS Alaska Zone 1. One zone, but fully general implementation.

### Existing: Transverse Mercator

Already implemented (`tm_forward`/`tm_inverse`). No changes needed. State Plane TM zones call these with zone-specific parameters.

### Unified Dispatch

Convenience functions that route to the correct projection based on `ProjectionDef.proj_type`:

```python
def projection_forward(lat, lon, proj_def: ProjectionDef) -> TMResult: ...
def projection_inverse(easting, northing, proj_def: ProjectionDef) -> TMInverseResult: ...
```

## CRS Layer

### CRS Extension — `cogopro/core/crs.py`

New fields on `CRS`: `proj_def` (ProjectionDef) and `name` (human label).

New factory methods:
- `CRS.state_plane(epsg)` — Look up SPCS zone by EPSG code, parse PROJ4, return CRS with `kind="projected"`.
- `CRS.from_proj4(proj4_string, name=None)` — Create CRS from any PROJ4 string.

State Plane and custom PROJ4 CRS both use `kind="projected"`. No separate "state_plane" kind needed since the projection math is identical.

### Transform Extension

`transform_point()` gains a `"projected"` branch that calls `projection_inverse()` / `projection_forward()` via the CRS's `proj_def`. All transforms still route through geodetic as intermediate, so geodetic <-> state plane, UTM <-> state plane, and state plane <-> state plane all work automatically.

## Zone Lookup — `cogopro/geodetic/state_plane.py`

```python
def get_zone(epsg: int) -> StatePlaneZone: ...
def find_zone(state: str, zone: str) -> StatePlaneZone: ...
def find_zones_by_fips(fips: int) -> StatePlaneZone: ...
def list_zones(state: str | None = None) -> list[StatePlaneZone]: ...
```

`StatePlaneZone` dataclass holds the parsed JSON entry plus the resolved `ProjectionDef`.

## CLI

### Extended CRS parsing for `--from-crs` / `--to-crs`:
- `epsg:2277` — EPSG code lookup
- `sp:TX-C` or `sp:TX:Central` — State + zone name shorthand
- `proj4:"+proj=lcc ..."` — Arbitrary PROJ4 string
- Existing `utm:17:N` and `geodetic:wgs84` unchanged

### New command: `cogopro zones`
```bash
cogopro zones                  # List all zones
cogopro zones --state TX       # List Texas zones
cogopro zones --epsg 2277      # Show zone details
```

## Testing Strategy

- **LCC**: Round-trip tests for 3-4 representative zones, cross-validate against NGS control points
- **TM**: Round-trip tests verifying parameter wiring (existing TM math is proven)
- **OMerc**: Round-trip through known Alaska coordinates
- **PROJ4 parser**: Parse all three projection types, verify conversions, test malformed input
- **CRS integration**: transform_point/transform_job between all CRS kind combinations
- **Zone database**: All 125 entries parse without error, lookup by EPSG/FIPS/state works
- **CLI**: convert command with state plane CRS, zones command output

## File Summary

| File | Change |
|------|--------|
| `src/cogopro/data/spcs_zones.json` | New — 125 zone definitions |
| `src/cogopro/geodetic/proj4.py` | New — PROJ4 string parser |
| `src/cogopro/geodetic/state_plane.py` | New — zone lookup |
| `src/cogopro/geodetic/projections.py` | Add LCC + OMerc projections, dispatch functions |
| `src/cogopro/core/crs.py` | Add projected CRS kind, state_plane/from_proj4 factories |
| `src/cogopro/cli.py` | Extended CRS parsing, zones command |
| `tests/test_proj4.py` | New — parser tests |
| `tests/test_lcc.py` | New — Lambert projection tests |
| `tests/test_omerc.py` | New — Oblique Mercator tests |
| `tests/test_state_plane.py` | New — zone lookup + integration tests |
| `tests/test_crs.py` | Extend with projected CRS tests |
| `tests/test_cli.py` | Extend with state plane CLI tests |
