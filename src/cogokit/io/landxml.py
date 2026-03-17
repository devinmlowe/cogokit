"""LandXML 1.2 import/export for survey points, parcels, and alignments."""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, TextIO, Tuple, Union

from ..core.job import Job
from ..core.point import Point
from ..surveying.alignment import CircularCurve, HorizontalAlignment, Tangent

NS = "http://www.landxml.org/schema/LandXML-1.2"
_NS_PREFIX = f"{{{NS}}}"

# Register default namespace so ET uses unprefixed tags instead of ns0:
ET.register_namespace("", NS)


@dataclass
class LandXMLResult:
    """Result of importing a LandXML file.

    Attributes:
        job: Job populated with imported CgPoints.
        parcels: List of (name, [Point, ...]) tuples for each imported parcel.
        alignments: List of (name, HorizontalAlignment) tuples for each
            imported alignment.
    """

    job: Job = field(default_factory=Job)
    parcels: list[tuple[str, list[Point]]] = field(default_factory=list)
    alignments: list[tuple[str, HorizontalAlignment]] = field(default_factory=list)


def import_landxml(source: Union[str, Path, TextIO]) -> LandXMLResult:
    """Read CgPoints, parcels, and alignments from a LandXML file.

    Parameters:
        source: File path or file-like object containing LandXML data.

    Returns:
        A LandXMLResult with job, parcels, and alignments.
    """
    job = Job()

    if isinstance(source, (str, Path)):
        path = Path(source)
        job.name = path.stem
        tree = ET.parse(path)
        root = tree.getroot()
    else:
        tree = ET.parse(source)
        root = tree.getroot()

    for cg_point in root.iter(f"{_NS_PREFIX}CgPoint"):
        name = cg_point.get("name", "")
        desc = cg_point.get("desc", "")
        text = (cg_point.text or "").strip()
        if not text:
            continue

        coords = text.split()
        if len(coords) < 2:
            continue

        northing = float(coords[0])
        easting = float(coords[1])
        elevation = float(coords[2]) if len(coords) >= 3 else 0.0

        try:
            number = int(name)
        except (ValueError, TypeError):
            continue

        job.add_point(Point(
            northing=northing,
            easting=easting,
            elevation=elevation,
            number=number,
            description=desc,
        ))

    parcels = _import_parcels(root)
    alignments = _import_alignments(root)

    return LandXMLResult(job=job, parcels=parcels, alignments=alignments)


def _import_parcels(root: ET.Element) -> list[tuple[str, list[Point]]]:
    """Parse <Parcels>/<Parcel> elements into (name, vertices) tuples."""
    result: list[tuple[str, list[Point]]] = []
    parcels_elem = root.find(f"{_NS_PREFIX}Parcels")
    if parcels_elem is None:
        return result

    for parcel in parcels_elem.findall(f"{_NS_PREFIX}Parcel"):
        name = parcel.get("name", "")
        coord_geom = parcel.find(f"{_NS_PREFIX}CoordGeom")
        if coord_geom is None:
            continue

        vertices: list[Point] = []
        for line in coord_geom.findall(f"{_NS_PREFIX}Line"):
            start_elem = line.find(f"{_NS_PREFIX}Start")
            if start_elem is not None and start_elem.text:
                coords = start_elem.text.strip().split()
                if len(coords) >= 2:
                    vertices.append(Point(
                        northing=float(coords[0]),
                        easting=float(coords[1]),
                    ))

        result.append((name, vertices))

    return result


def _import_alignments(root: ET.Element) -> list[tuple[str, HorizontalAlignment]]:
    """Parse <Alignments>/<Alignment> elements into (name, HorizontalAlignment) tuples."""
    result: list[tuple[str, HorizontalAlignment]] = []
    aligns_elem = root.find(f"{_NS_PREFIX}Alignments")
    if aligns_elem is None:
        return result

    for alignment in aligns_elem.findall(f"{_NS_PREFIX}Alignment"):
        name = alignment.get("name", "")
        sta_start = float(alignment.get("staStart", "0.0"))
        coord_geom = alignment.find(f"{_NS_PREFIX}CoordGeom")
        if coord_geom is None:
            continue

        elements = []
        for child in coord_geom:
            tag = child.tag.replace(_NS_PREFIX, "")
            if tag == "Line":
                elem = _import_line_element(child, sta_start, elements)
                if elem is not None:
                    elements.append(elem)
            elif tag == "Curve":
                elem = _import_curve_element(child, sta_start, elements)
                if elem is not None:
                    elements.append(elem)

        if elements:
            result.append((name, HorizontalAlignment(elements)))

    return result


def _parse_point(elem: ET.Element | None) -> Point | None:
    """Parse a LandXML coordinate text element into a Point."""
    if elem is None or not elem.text:
        return None
    coords = elem.text.strip().split()
    if len(coords) < 2:
        return None
    return Point(northing=float(coords[0]), easting=float(coords[1]))


def _import_line_element(
    line_elem: ET.Element,
    sta_start: float,
    preceding: list,
) -> Tangent | None:
    """Import a LandXML <Line> as a Tangent alignment element."""
    start_pt = _parse_point(line_elem.find(f"{_NS_PREFIX}Start"))
    end_pt = _parse_point(line_elem.find(f"{_NS_PREFIX}End"))
    if start_pt is None or end_pt is None:
        return None

    length = float(line_elem.get("length", "0.0"))
    dir_deg = line_elem.get("dir")

    if dir_deg is not None:
        azimuth = math.radians(float(dir_deg))
    else:
        # Compute azimuth from start/end points
        dn = end_pt.northing - start_pt.northing
        de = end_pt.easting - start_pt.easting
        azimuth = math.atan2(de, dn)
        if azimuth < 0:
            azimuth += 2 * math.pi

    if length == 0.0:
        length = math.hypot(
            end_pt.northing - start_pt.northing,
            end_pt.easting - start_pt.easting,
        )

    start_station = preceding[-1].end_station if preceding else sta_start

    return Tangent(
        start_station=start_station,
        length=length,
        azimuth=azimuth,
        start_point=start_pt,
    )


def _import_curve_element(
    curve_elem: ET.Element,
    sta_start: float,
    preceding: list,
) -> CircularCurve | None:
    """Import a LandXML <Curve> as a CircularCurve alignment element."""
    pc_point = _parse_point(curve_elem.find(f"{_NS_PREFIX}Start"))
    center_point = _parse_point(curve_elem.find(f"{_NS_PREFIX}Center"))
    end_point = _parse_point(curve_elem.find(f"{_NS_PREFIX}End"))
    if pc_point is None or center_point is None or end_point is None:
        return None

    radius = float(curve_elem.get("radius", "0.0"))
    length = float(curve_elem.get("length", "0.0"))
    rot = curve_elem.get("rot", "cw")
    direction = "R" if rot == "cw" else "L"

    # Compute delta from length and radius
    delta = length / radius if radius > 0 else 0.0

    # Compute start azimuth: tangent at PC is perpendicular to radial line
    az_to_pc = math.atan2(
        pc_point.easting - center_point.easting,
        pc_point.northing - center_point.northing,
    )
    if direction == "R":
        start_azimuth = az_to_pc + math.pi / 2
    else:
        start_azimuth = az_to_pc - math.pi / 2

    start_station = preceding[-1].end_station if preceding else sta_start

    return CircularCurve(
        start_station=start_station,
        length=length,
        radius=radius,
        delta=delta,
        direction=direction,
        pc_point=pc_point,
        center_point=center_point,
        start_azimuth=start_azimuth,
    )


def export_landxml(
    job: Job,
    destination: Union[str, Path, TextIO],
    parcels: Optional[List[Tuple[str, List[int]]]] = None,
    alignments: Optional[List[Tuple[str, HorizontalAlignment]]] = None,
) -> None:
    """Write a LandXML 1.2 file with points, optional parcels, and alignments.

    Parameters:
        job: Job containing points to export.
        destination: Output file path or file-like object.
        parcels: List of (name, point_number_list) tuples for parcel export.
            Point numbers reference points in the job. Parcels are closed polygons.
        alignments: List of (name, HorizontalAlignment) tuples for alignment export.
    """
    root = ET.Element(f"{_NS_PREFIX}LandXML", attrib={"version": "1.2"})

    # CgPoints
    cg_points = ET.SubElement(root, f"{_NS_PREFIX}CgPoints")
    for p in job.points():
        attrib = {"name": str(p.number)}
        if p.description:
            attrib["desc"] = p.description
        elem = ET.SubElement(cg_points, f"{_NS_PREFIX}CgPoint", attrib=attrib)
        elem.text = f"{p.northing:.3f} {p.easting:.3f} {p.elevation:.3f}"

    # Parcels
    if parcels:
        parcels_elem = ET.SubElement(root, f"{_NS_PREFIX}Parcels")
        for parcel_name, pt_numbers in parcels:
            parcel = ET.SubElement(parcels_elem, f"{_NS_PREFIX}Parcel", attrib={"name": parcel_name})
            coord_geom = ET.SubElement(parcel, f"{_NS_PREFIX}CoordGeom")
            # Close the polygon: connect last point back to first
            pts = [job.get_point(n) for n in pt_numbers]
            pts = [p for p in pts if p is not None]
            closed_pts = pts + [pts[0]] if pts else []
            for a, b in zip(closed_pts, closed_pts[1:]):
                line = ET.SubElement(coord_geom, f"{_NS_PREFIX}Line")
                start = ET.SubElement(line, f"{_NS_PREFIX}Start")
                start.text = f"{a.northing:.3f} {a.easting:.3f}"
                end = ET.SubElement(line, f"{_NS_PREFIX}End")
                end.text = f"{b.northing:.3f} {b.easting:.3f}"

    # Alignments
    if alignments:
        aligns_elem = ET.SubElement(root, f"{_NS_PREFIX}Alignments")
        for align_name, ha in alignments:
            sta_start = ha.elements[0].start_station if ha.elements else 0.0
            align = ET.SubElement(aligns_elem, f"{_NS_PREFIX}Alignment", attrib={
                "name": align_name,
                "length": f"{ha.total_length:.3f}",
                "staStart": f"{sta_start:.3f}",
            })
            coord_geom = ET.SubElement(align, f"{_NS_PREFIX}CoordGeom")
            for elem in ha.elements:
                if isinstance(elem, Tangent):
                    _export_tangent(coord_geom, elem)
                elif isinstance(elem, CircularCurve):
                    _export_curve(coord_geom, elem)

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")

    if isinstance(destination, (str, Path)):
        tree.write(destination, encoding="unicode", xml_declaration=True)
    else:
        tree.write(destination, encoding="unicode", xml_declaration=True)


def _export_tangent(parent: ET.Element, tangent: Tangent) -> None:
    """Export a Tangent element as a LandXML Line."""
    end_pt = tangent.point_at(tangent.end_station)
    line = ET.SubElement(parent, f"{_NS_PREFIX}Line", attrib={
        "dir": f"{math.degrees(tangent.azimuth):.4f}",
        "length": f"{tangent.length:.3f}",
    })
    start = ET.SubElement(line, f"{_NS_PREFIX}Start")
    start.text = f"{tangent.start_point.northing:.3f} {tangent.start_point.easting:.3f}"
    end = ET.SubElement(line, f"{_NS_PREFIX}End")
    end.text = f"{end_pt.northing:.3f} {end_pt.easting:.3f}"


def _export_curve(parent: ET.Element, curve: CircularCurve) -> None:
    """Export a CircularCurve element as a LandXML Curve."""
    end_pt = curve.point_at(curve.end_station)
    rot = "cw" if curve.direction == "R" else "ccw"
    curve_elem = ET.SubElement(parent, f"{_NS_PREFIX}Curve", attrib={
        "rot": rot,
        "radius": f"{curve.radius:.3f}",
        "length": f"{curve.length:.3f}",
    })
    start = ET.SubElement(curve_elem, f"{_NS_PREFIX}Start")
    start.text = f"{curve.pc_point.northing:.3f} {curve.pc_point.easting:.3f}"
    center = ET.SubElement(curve_elem, f"{_NS_PREFIX}Center")
    center.text = f"{curve.center_point.northing:.3f} {curve.center_point.easting:.3f}"
    end = ET.SubElement(curve_elem, f"{_NS_PREFIX}End")
    end.text = f"{end_pt.northing:.3f} {end_pt.easting:.3f}"
