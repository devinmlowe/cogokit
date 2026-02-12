# COGOpro Python

A Python reimplementation of **COGO+ Pro v4.20**, a coordinate geometry and surveying application originally written for the HP 50g/49g+ calculators by [Simple Geospatial Solutions](https://sgss.ca).

This project reverse-engineers the HP RPL calculator programs (libraries L930-L936) into a clean, modular Python package with comprehensive test coverage. The original calculator source files are preserved in the `original/` directory for reference.

## Features

**519 tests** covering all computational modules. One runtime dependency ([Typer](https://typer.tiangolo.com/) for the CLI). Optional: [NumPy](https://numpy.org/) for least-squares network adjustment.

### Core (`cogopro.core`)

- **Point** - Survey point with northing/easting/elevation, distance and azimuth calculations
- **Angle** - DMS, decimal degrees, radians, HP notation, and surveyor bearing conversions with full arithmetic
- **Job** - Point collection container with add/get/remove/iterate operations and optional CRS
- **CRS** - Coordinate reference system (geodetic/UTM) with point and job transformations between systems
- **Units** - Linear (feet, meters, chains, links, rods) and angular (DMS, decimal degrees, radians, grads) unit conversions

### Coordinate Geometry (`cogopro.cogo`)

- **Inverse** - Azimuth, horizontal/slope/vertical distance, and grade between two points
- **Traverse** - Forward traverse and sideshot from a point along a bearing
- **Intersections** - Bearing-bearing, bearing-distance, and distance-distance intersections
- **Area** - Polygon area (shoelace formula) and perimeter

### Adjustments (`cogopro.adjustments`)

- **Compass Rule** - Bowditch traverse adjustment for closed and fixed-endpoint traverses
- **Helmert Transform** - 2D similarity transformation (least-squares) with translation, rotation, and scale
- **Least Squares** - General-purpose network adjustment with distance, angle, direction, and azimuth observations (requires NumPy: `pip install cogopro[lsa]`)
- **Transforms** - Rotate, mirror, shift, scale, and average point sets

### Geometric Solvers (`cogopro.solvers`)

- **Triangle** - All solution cases: SSS, SAS, ASA, AAS, ambiguous SSA
- **Horizontal Curve** - Circular curve solver (any 2 elements), 3-point curve, clothoid spirals
- **Vertical Curve** - Parabolic vertical curve solver with high/low point detection

### Geodetic (`cogopro.geodetic`)

- **Ellipsoids** - 9 reference ellipsoids (WGS84, GRS80, Clarke 1866, etc.) with derived parameters
- **Vincenty** - Direct and inverse geodesic solutions on the ellipsoid
- **Projections** - Transverse Mercator and UTM forward/inverse projections
- **Conversions** - Grid-to-geodetic coordinate conversion, combined scale factor, ground/grid distance

### Surveying (`cogopro.surveying`)

- **Levelling** - Differential level run reduction, loop closure adjustment
- **Traverse Plus** - Total station field observation reduction (HI/HT, slope-to-horizontal), station processing, Tienstra 3-point resection
- **Alignment** - Horizontal alignment (tangents, circular curves, clothoid spirals), vertical profile with grade breaks and vertical curves, combined 3D alignment with station/offset
- **Traverse Workflow** - End-to-end traverse pipeline: observation reduction, angular closure, coordinate computation, compass rule adjustment with precision analysis
- **Stakeout** - Point and alignment stakeout calculations, batch staking, slope staking with cut/fill
- **Cross Sections** - Cross-section templates, cut/fill area computation, average end area and prismoidal volumes, earthwork summaries, mass haul ordinates

### I/O (`cogopro.io`)

- **ASCII I/O** - Read/write delimited point files (space, tab, comma) with auto-detection
- **CSV** - Flexible CSV import/export with configurable column mappings and header auto-detection
- **LandXML** - Import points from LandXML 1.2; export points, parcels, and alignments
- **DXF Export** - Point, text label, line, and polyline entities with layer organization
- **KML Export** - Point export with automatic CRS-to-WGS84 coordinate transformation

## Installation

```bash
git clone git@github.com:devinmlowe/cogopro-python.git
cd cogopro-python
pip install -e ".[dev]"
```

Requires Python 3.11+. Runtime dependency: `typer` (for CLI). Development: `pytest` and `ruff`. Optional: `pip install cogopro[lsa]` for least-squares network adjustment (NumPy).

## Usage

```python
from cogopro.core import Point, Angle, Job
from cogopro.cogo.inverse import inverse
from cogopro.cogo.traverse import traverse
from cogopro.io import read_points, write_points, Delimiter

# Create points
p1 = Point(northing=1000.0, easting=2000.0, elevation=100.0, number=1, description="BM1")
p2 = Point(northing=1500.0, easting=2500.0, elevation=105.0, number=2, description="BM2")

# Inverse calculation
result = inverse(p1, p2)
print(f"Azimuth: {Angle.from_azimuth(result.azimuth).to_bearing_string()}")
print(f"Distance: {result.horizontal_distance:.3f}")

# Forward traverse
p3 = traverse(p1, azimuth=result.azimuth, distance=100.0, elevation=102.0)

# Read/write point files
job = read_points("points.txt")
write_points(job, "output.csv", delimiter=Delimiter.COMMA)
```

## CLI

After installation, the `cogopro` command is available:

```bash
# Inverse between two points
cogopro inverse 1000 2000 1500 2500

# Forward traverse
cogopro traverse 1000 2000 45.0 100.0 --elevation 102.0

# Polygon area from a points file
cogopro area points.txt

# Solve a horizontal curve (any 2 elements)
cogopro curve --radius 500 --delta 30

# Transform coordinates between CRS types
cogopro convert points.txt --from-crs utm:17:N --to-crs geodetic:wgs84

# Export to DXF or KML
cogopro export points.txt --format dxf --output site.dxf

# Run a full traverse workflow from observations
cogopro traverse-run observations.csv --start-point "1 1000.0 5000.0 100.0" --start-azimuth 45.0
```

Run `cogopro --help` or `cogopro <command> --help` for full option details.

## Running Tests

```bash
pytest           # Run all 519 tests
pytest -v        # Verbose output
pytest tests/test_alignment.py  # Single module
```

## Project Structure

```
cogopro-python/
  src/cogopro/
    cli.py          # Typer CLI
    core/           # Point, Angle, Job, CRS, Units
    cogo/           # Inverse, traverse, intersections, area
    adjustments/    # Compass rule, Helmert, least-squares, transforms
    solvers/        # Triangle, horizontal curve, vertical curve
    geodetic/       # Ellipsoids, Vincenty, projections, conversions
    surveying/      # Levelling, traverse+, alignment, stakeout, cross-sections, workflow
    io/             # ASCII/CSV I/O, LandXML, DXF/KML export
  tests/            # 519 tests across 29 test files
  original/         # Original HP calculator source files (L930-L936)
```

### HP Library Mapping

| Library | File | Domain |
|---------|------|--------|
| L930 | `PROGRAM/L930.HP` | Main menu, point management, settings, basic COGO |
| L931 | `PROGRAM/L931.HP` | Curves, compass rule, traverse, geodetic calcs |
| L932 | `PROGRAM/L932.HP` | Figures/areas, transformations, Helmert, traverse stakeout |
| L933 | `PROGRAM/L933.HP` | Triangle solver, curve solver, vertical curves, alignments |
| L934 | `PROGRAM/L934.HP` | Coordinate systems, projections, geodetic conversions |
| L935 | `PROGRAM/L935.HP` | Levelling |
| L936 | `PROGRAM/L936.HP` | Utilities/support |

## Next Steps

### High Priority

- **State Plane CRS support** - Extend the CRS layer beyond geodetic/UTM to support State Plane coordinate systems with zone definitions and custom TM parameters.
- **GPS baseline observations** - Add 3D GPS baseline vectors to the least-squares network adjustment module (requires different weight model).
- **Interactive TUI** - Build a terminal UI (via `textual` or `curses`) mirroring the original COGO+ Pro menu system for interactive field use.

### Medium Priority

- **Report generation** - Generate formatted traverse reports, adjustment reports, and stakeout sheets as PDF or HTML.
- **Point database backend** - Replace the in-memory `Job` dict with an optional SQLite backend for large projects with thousands of points.
- **3D slope staking** - Extend cross-sections and earthwork to handle iterative catch-point computation on irregular ground surfaces.

### Lower Priority

- **LandXML complex import** - Import alignments and parcels from LandXML (currently export-only for these; point import is complete).
- **Edge-case test hardening** - Additional testing for antipodal Vincenty, near-zero curves, degenerate triangles, and boundary conditions.

## Origin

COGO+ Pro v4.20 was developed by Simple Geospatial Solutions (sgss.ca) as a comprehensive coordinate geometry suite for HP 50g and 49g+ graphing calculators. The original software was distributed as compiled HP RPL libraries (L930-L936) covering COGO, adjustments, curves, triangles, geodetics, and surveying operations.

This Python port preserves the mathematical algorithms while modernizing the architecture into a testable, extensible package.

## License

Private repository. All rights reserved.
