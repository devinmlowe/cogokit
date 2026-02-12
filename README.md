# COGOpro-python

A Python reimplementation of **COGO+ Pro v4.20** by Simple Geospatial Solutions (sgss.ca).

COGO+ Pro is a comprehensive coordinate geometry (COGO) and surveying application originally written for the HP 50g/49g+ graphing calculators. This project reverse-engineers the HP calculator program and refactors it into a clean, modular Python library.

## Original Application

The `original/` directory contains the unmodified HP calculator program files from the [COGOpro.zip](https://sgss.ca/files/COGOpro.zip) distribution. The `.HP` files are compiled HP RPL programs (libraries L930-L936) containing binary and embedded string data.

### HP Library Mapping

| Library | File | Primary Domain |
|---------|------|----------------|
| L930 | `PROGRAM/L930.HP` | Main menu, point management, settings, basic COGO |
| L931 | `PROGRAM/L931.HP` | Curves, compass rule, traverse, geodetic calcs |
| L932 | `PROGRAM/L932.HP` | Figures/areas, transformations, Helmert, traverse stakeout |
| L933 | `PROGRAM/L933.HP` | Triangle solver, curve solver, vertical curves, alignments |
| L934 | `PROGRAM/L934.HP` | Coordinate systems, projections, geodetic conversions |
| L935 | `PROGRAM/L935.HP` | Levelling |
| L936 | `PROGRAM/L936.HP` | Utilities/support |

### Sample Data

The `original/ASCII/` directory contains sample point files demonstrating the data format:
```
PointNum Northing Easting Elevation Description
```

## Feature Set (Target)

### Core COGO
- **Point Traverse** - direction/distance point creation, sideshot mode
- **Inverse** - direction, distance, coordinate differences between points
- **Intersections** - bearing-bearing, bearing-distance, distance-distance (with offsets)
- **Area** - polygon area calculation

### Adjustments
- **Compass Rule** - closed-loop and fixed-point traverse adjustment
- **Transformations** - rotate, mirror, shift (N/E/Z), scale, average coordinates
- **Helmert Transformation** - 2D/3D least-squares coordinate transformation

### Surveying
- **Traverse Plus** - total station data processing (slope/hz distances, angles, heights)
- **Resection** - position from observations to known points
- **Stakeout** - alignment and point stakeout
- **Levelling** - differential levelling with circuit adjustments
- **Alignments** - 3D alignments with straights, curves, spirals, vertical curves, cross-sections
- **Cut/Fill** - earthwork calculations

### Solvers
- **Triangle Solver** - spherical and planar triangle solutions
- **Horizontal Curve** - including 3-point curves and spirals
- **Vertical Curve** - parabolic vertical curve solutions

### Geodetic
- **Coordinate Conversions** - grid to geodetic and vice versa
- **Projections** - UTM, US State Plane, Canadian, Australian, and custom projections
- **Vincenty** - direct and inverse geodesic solutions
- **Ellipsoids** - WGS84, NAD83, and user-defined ellipsoids

### I/O
- **Point Management** - store, review, delete, renumber, browse
- **Import/Export** - CSV/delimited ASCII files
- **DXF Export** - CAD integration
- **KML Export** - Google Earth visualization
- **Job Management** - project/job file handling

## Python Project Structure

```
src/cogopro/
    core/           # Points, angles, coordinate systems, units
    cogo/           # Traverse, inverse, intersections, area
    adjustments/    # Compass rule, Helmert, transformations
    surveying/      # Traverse+, levelling, alignments, stakeout
    geodetic/       # Projections, conversions, Vincenty, ellipsoids
    solvers/        # Triangle, horizontal curve, vertical curve
    io/             # File I/O (ASCII, DXF, KML, job files)
tests/              # Unit tests
original/           # Original HP calculator program files
```

## Development Approach

1. **Reverse engineer** the HP RPL programs by extracting readable strings, identifying function names, and mapping computational logic
2. **Implement core primitives** first (points, angles, coordinate systems)
3. **Build outward** from COGO fundamentals to advanced features
4. **Validate** against the sample data files and known surveying formulas
5. **Test thoroughly** with unit tests for each computational module

## License

The original COGO+ Pro is free software by Simple Geospatial Solutions. This Python reimplementation is for educational and professional use.
