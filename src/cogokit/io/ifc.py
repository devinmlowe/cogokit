"""IFC 4X3 (Industry Foundation Classes) import/export for survey data.

Supports export/import of survey points, georeferencing (CRS), alignments,
and parcel boundaries. Points are stored as IfcAnnotation entities with
IfcCartesianPoint geometry.

Requires ifcopenshell (optional dependency): pip install cogokit[ifc]
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING, Union

try:
    import ifcopenshell
    import ifcopenshell.api
except ImportError:
    raise ImportError(
        "ifcopenshell is required for IFC support. "
        "Install with: pip install cogokit[ifc]"
    )

from ..core.job import Job
from ..core.point import Point

if TYPE_CHECKING:
    from ..core.crs import CRS
    from ..surveying.alignment import (
        CircularCurve,
        HorizontalAlignment,
        Tangent,
    )


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def export_ifc(
    job: Job,
    destination: Union[str, Path],
    *,
    crs: CRS | None = None,
    parcels: list[tuple[str, list[Point]]] | None = None,
    alignments: list[tuple[str, HorizontalAlignment]] | None = None,
) -> None:
    """Export a Job to an IFC 4X3 file.

    Parameters:
        job: Job containing points to export.
        destination: Output file path.
        crs: Optional CRS for georeferencing (creates IfcProjectedCRS +
            IfcMapConversion entities).
        parcels: Optional list of ``(name, [Point, ...])`` tuples to export
            as parcel polygons.
        alignments: Optional list of ``(name, HorizontalAlignment)`` tuples
            to export as IfcAlignment entities.
    """
    model = ifcopenshell.file(schema="IFC4X3")

    # Project hierarchy
    project = ifcopenshell.api.run(
        "root.create_entity", model, ifc_class="IfcProject", name=job.name,
    )
    if job.description:
        project.Description = job.description

    # Geometric representation context
    ctx = ifcopenshell.api.run("context.add_context", model, context_type="Model")
    body = ifcopenshell.api.run(
        "context.add_context", model,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=ctx,
    )

    site = ifcopenshell.api.run(
        "root.create_entity", model, ifc_class="IfcSite", name=job.name,
    )
    ifcopenshell.api.run(
        "aggregate.assign_object", model,
        relating_object=project, products=[site],
    )

    # Georeferencing
    if crs is not None:
        _export_crs(model, ctx, crs)

    # Points
    _export_points(model, job, site, body)

    # Alignments
    if alignments:
        _export_alignments(model, site, body, alignments)

    # Parcels
    if parcels:
        _export_parcels(model, site, body, parcels)

    model.write(str(destination))


def _export_crs(
    model: ifcopenshell.file,
    context: ifcopenshell.entity_instance,
    crs: CRS,
) -> None:
    """Add IfcProjectedCRS and IfcMapConversion to the model."""
    crs_name = _crs_to_name(crs)
    ifc_crs = model.create_entity("IfcProjectedCRS", Name=crs_name)

    if crs.kind == "utm":
        ifc_crs.MapProjection = "UTM"
        if crs.zone is not None:
            zone_str = f"{crs.zone}{crs.hemisphere or 'N'}"
            ifc_crs.MapZone = zone_str
        if crs.ellipsoid is not None:
            ifc_crs.GeodeticDatum = getattr(crs.ellipsoid, "name", None)
    elif crs.kind == "projected" and crs.name:
        ifc_crs.MapProjection = crs.name

    # IfcMapConversion: identity transform (no offset)
    model.create_entity(
        "IfcMapConversion",
        SourceCRS=context,
        TargetCRS=ifc_crs,
        Eastings=0.0,
        Northings=0.0,
        OrthogonalHeight=0.0,
    )


def _crs_to_name(crs: CRS) -> str:
    """Derive an IFC CRS name string from a cogokit CRS."""
    if crs.name:
        return crs.name
    if crs.kind == "utm" and crs.zone is not None:
        hem = crs.hemisphere or "N"
        # EPSG 326xx for N, 327xx for S
        epsg_base = 32600 if hem == "N" else 32700
        return f"EPSG:{epsg_base + crs.zone}"
    return "Unknown"


def _export_points(
    model: ifcopenshell.file,
    job: Job,
    site: ifcopenshell.entity_instance,
    body_context: ifcopenshell.entity_instance,
) -> None:
    """Export job points as IfcAnnotation entities."""
    annotations = []
    for pt in job.points():
        ann = ifcopenshell.api.run(
            "root.create_entity", model,
            ifc_class="IfcAnnotation",
            name=str(pt.number) if pt.number is not None else "",
        )
        ann.Description = pt.description or ""
        ann.ObjectType = "SurveyPoint"

        # IFC coordinates: (X=Easting, Y=Northing, Z=Elevation)
        ifc_pt = model.createIfcCartesianPoint(
            [pt.easting, pt.northing, pt.elevation]
        )
        point_rep = model.create_entity(
            "IfcShapeRepresentation",
            ContextOfItems=body_context,
            RepresentationIdentifier="Point",
            RepresentationType="Point",
            Items=[ifc_pt],
        )
        prod_repr = model.create_entity(
            "IfcProductDefinitionShape",
            Representations=[point_rep],
        )
        ann.Representation = prod_repr
        annotations.append(ann)

    if annotations:
        ifcopenshell.api.run(
            "spatial.assign_container", model,
            relating_structure=site, products=annotations,
        )


def _export_alignments(
    model: ifcopenshell.file,
    site: ifcopenshell.entity_instance,
    body_context: ifcopenshell.entity_instance,
    alignments: list[tuple[str, HorizontalAlignment]],
) -> None:
    """Export horizontal alignments as IfcAlignment entities."""
    from ..surveying.alignment import CircularCurve, Tangent

    for name, horiz_align in alignments:
        alignment = ifcopenshell.api.run(
            "root.create_entity", model,
            ifc_class="IfcAlignment", name=name,
        )

        horiz = ifcopenshell.api.run(
            "root.create_entity", model,
            ifc_class="IfcAlignmentHorizontal",
        )
        ifcopenshell.api.run(
            "aggregate.assign_object", model,
            relating_object=alignment, products=[horiz],
        )

        for elem in horiz_align.elements:
            seg = ifcopenshell.api.run(
                "root.create_entity", model,
                ifc_class="IfcAlignmentSegment",
            )

            if isinstance(elem, Tangent):
                start_pt = model.createIfcCartesianPoint(
                    [elem.start_point.easting, elem.start_point.northing]
                )
                design_params = model.create_entity(
                    "IfcAlignmentHorizontalSegment",
                    StartPoint=start_pt,
                    StartDirection=elem.azimuth,
                    StartRadiusOfCurvature=0.0,
                    EndRadiusOfCurvature=0.0,
                    SegmentLength=elem.length,
                    PredefinedType="LINE",
                )
            elif isinstance(elem, CircularCurve):
                start_pt = model.createIfcCartesianPoint(
                    [elem.pc_point.easting, elem.pc_point.northing]
                )
                sign = 1.0 if elem.direction == "R" else -1.0
                design_params = model.create_entity(
                    "IfcAlignmentHorizontalSegment",
                    StartPoint=start_pt,
                    StartDirection=elem.start_azimuth,
                    StartRadiusOfCurvature=sign * elem.radius,
                    EndRadiusOfCurvature=sign * elem.radius,
                    SegmentLength=elem.length,
                    PredefinedType="CIRCULARARC",
                )
            else:
                # Unsupported element type — skip
                continue

            seg.DesignParameters = design_params
            ifcopenshell.api.run(
                "aggregate.assign_object", model,
                relating_object=horiz, products=[seg],
            )

        ifcopenshell.api.run(
            "spatial.assign_container", model,
            relating_structure=site, products=[alignment],
        )


def _export_parcels(
    model: ifcopenshell.file,
    site: ifcopenshell.entity_instance,
    body_context: ifcopenshell.entity_instance,
    parcels: list[tuple[str, list[Point]]],
) -> None:
    """Export parcels as IfcAnnotation entities with polyline geometry."""
    annotations = []
    for name, boundary_points in parcels:
        if len(boundary_points) < 3:
            continue

        ann = ifcopenshell.api.run(
            "root.create_entity", model,
            ifc_class="IfcAnnotation", name=name,
        )
        ann.ObjectType = "Parcel"

        # Create closed polyline from boundary points
        # IFC coords: X=Easting, Y=Northing, Z=Elevation
        ifc_points = []
        for pt in boundary_points:
            ifc_points.append(
                model.createIfcCartesianPoint(
                    [pt.easting, pt.northing, pt.elevation]
                )
            )
        # Close the polygon by repeating the first point
        ifc_points.append(
            model.createIfcCartesianPoint(
                [boundary_points[0].easting,
                 boundary_points[0].northing,
                 boundary_points[0].elevation]
            )
        )

        polyline = model.create_entity("IfcPolyline", Points=ifc_points)
        shape_rep = model.create_entity(
            "IfcShapeRepresentation",
            ContextOfItems=body_context,
            RepresentationIdentifier="Annotation",
            RepresentationType="Curve2D",
            Items=[polyline],
        )
        prod_repr = model.create_entity(
            "IfcProductDefinitionShape",
            Representations=[shape_rep],
        )
        ann.Representation = prod_repr
        annotations.append(ann)

    if annotations:
        ifcopenshell.api.run(
            "spatial.assign_container", model,
            relating_structure=site, products=annotations,
        )


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------


def import_ifc(source: Union[str, Path]) -> Job:
    """Import survey points from an IFC file.

    Reads IfcAnnotation entities with ObjectType ``'SurveyPoint'`` and
    extracts their IfcCartesianPoint coordinates. Also reads georeferencing
    information (IfcProjectedCRS + IfcMapConversion) if present.

    Parameters:
        source: Path to the IFC file.

    Returns:
        A Job populated with imported points and CRS (if available).

    Raises:
        FileNotFoundError: If the source file does not exist.
    """
    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"IFC file not found: {path}")

    model = ifcopenshell.open(str(path))

    job = Job(name=path.stem)

    # Import project description if available
    projects = model.by_type("IfcProject")
    if projects:
        proj = projects[0]
        if proj.Description:
            job.description = proj.Description

    # Import CRS
    job.crs = _import_crs(model)

    # Import points from IfcAnnotation entities
    _import_points(model, job)

    return job


def _import_crs(model: ifcopenshell.file) -> CRS | None:
    """Read IfcProjectedCRS and reconstruct a cogokit CRS."""
    from ..core.crs import CRS

    projected_crs_list = model.by_type("IfcProjectedCRS")
    if not projected_crs_list:
        return None

    ifc_crs = projected_crs_list[0]
    name = ifc_crs.Name or ""

    # Try to reconstruct UTM CRS from map projection/zone info
    if ifc_crs.MapProjection == "UTM" and ifc_crs.MapZone:
        zone_str = ifc_crs.MapZone
        # Parse zone like "17N" or "32S"
        zone_num = int("".join(c for c in zone_str if c.isdigit()))
        hem = "S" if "S" in zone_str.upper() else "N"
        return CRS.utm(zone=zone_num, hemisphere=hem)

    # Try to parse EPSG code from name
    if name.startswith("EPSG:"):
        epsg_str = name.split(":")[1]
        epsg = int(epsg_str)
        # UTM North zones: 32601-32660, South: 32701-32760
        if 32601 <= epsg <= 32660:
            return CRS.utm(zone=epsg - 32600, hemisphere="N")
        if 32701 <= epsg <= 32760:
            return CRS.utm(zone=epsg - 32700, hemisphere="S")

    return None


def _import_points(model: ifcopenshell.file, job: Job) -> None:
    """Import points from IfcAnnotation entities with SurveyPoint type."""
    for ann in model.by_type("IfcAnnotation"):
        if ann.ObjectType != "SurveyPoint":
            continue

        coords = _extract_point_coords(ann)
        if coords is None:
            continue

        easting, northing, elevation = coords

        # Parse point number from name
        number = None
        if ann.Name:
            try:
                number = int(ann.Name)
            except ValueError:
                pass

        description = ann.Description or ""

        pt = Point(
            northing=northing,
            easting=easting,
            elevation=elevation,
            number=number,
            description=description,
        )
        job.add_point(pt)


def _extract_point_coords(
    ann: ifcopenshell.entity_instance,
) -> tuple[float, float, float] | None:
    """Extract (easting, northing, elevation) from an IfcAnnotation's geometry."""
    if ann.Representation is None:
        return None

    for rep in ann.Representation.Representations:
        for item in rep.Items:
            if item.is_a("IfcCartesianPoint"):
                coords = item.Coordinates
                if len(coords) >= 3:
                    return (coords[0], coords[1], coords[2])
                if len(coords) >= 2:
                    return (coords[0], coords[1], 0.0)

    return None
