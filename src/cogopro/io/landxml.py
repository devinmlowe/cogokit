"""LandXML 1.2 import/export for survey points, parcels, and alignments."""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional, TextIO, Tuple, Union

from ..core.job import Job
from ..core.point import Point
from ..surveying.alignment import CircularCurve, HorizontalAlignment, Tangent

NS = "http://www.landxml.org/schema/LandXML-1.2"
_NS_PREFIX = f"{{{NS}}}"

# Register default namespace so ET uses unprefixed tags instead of ns0:
ET.register_namespace("", NS)


def import_landxml(source: Union[str, Path, TextIO]) -> Job:
    """Read CgPoints from a LandXML file into a Job.

    Parameters:
        source: File path or file-like object containing LandXML data.

    Returns:
        A Job populated with the imported points.
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

    return job


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
