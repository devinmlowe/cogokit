"""Tests for LandXML import/export."""

import io
import math
import xml.etree.ElementTree as ET
from pathlib import Path

from cogokit.core.job import Job
from cogokit.core.point import Point
from cogokit.io.landxml import export_landxml, import_landxml
from cogokit.surveying.alignment import (
    CircularCurve,
    HorizontalAlignment,
    Tangent,
)

NS = "http://www.landxml.org/schema/LandXML-1.2"


def _make_job():
    """Create a small test job with 3 points."""
    job = Job(name="TestJob")
    job.add_point(Point(northing=1000.0, easting=2000.0, elevation=100.0, number=1, description="BM1"))
    job.add_point(Point(northing=1100.0, easting=2100.0, elevation=101.0, number=2, description="IP"))
    job.add_point(Point(northing=1200.0, easting=2200.0, elevation=102.0, number=3, description="EP"))
    return job


SAMPLE_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<LandXML xmlns="http://www.landxml.org/schema/LandXML-1.2" version="1.2">
  <CgPoints>
    <CgPoint name="1" desc="BM1">1000.000 2000.000 100.000</CgPoint>
    <CgPoint name="2" desc="IP">1100.000 2100.000 101.000</CgPoint>
    <CgPoint name="3" desc="EP">1200.000 2200.000 102.000</CgPoint>
  </CgPoints>
</LandXML>
"""


# --- Import tests ---


class TestImportLandXML:
    def test_import_from_string(self):
        job = import_landxml(io.StringIO(SAMPLE_XML))
        assert job.point_count == 3

    def test_import_point_values(self):
        job = import_landxml(io.StringIO(SAMPLE_XML))
        p1 = job.get_point(1)
        assert p1 is not None
        assert math.isclose(p1.northing, 1000.0)
        assert math.isclose(p1.easting, 2000.0)
        assert math.isclose(p1.elevation, 100.0)
        assert p1.description == "BM1"

    def test_import_all_points(self):
        job = import_landxml(io.StringIO(SAMPLE_XML))
        p3 = job.get_point(3)
        assert p3 is not None
        assert math.isclose(p3.northing, 1200.0)
        assert p3.description == "EP"

    def test_import_from_file(self, tmp_path: Path):
        xml_file = tmp_path / "test.xml"
        xml_file.write_text(SAMPLE_XML)
        job = import_landxml(xml_file)
        assert job.point_count == 3
        assert job.name == "test"

    def test_import_no_description(self):
        xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<LandXML xmlns="http://www.landxml.org/schema/LandXML-1.2" version="1.2">
  <CgPoints>
    <CgPoint name="10">500.0 600.0 50.0</CgPoint>
  </CgPoints>
</LandXML>
"""
        job = import_landxml(io.StringIO(xml))
        p = job.get_point(10)
        assert p is not None
        assert p.description == ""

    def test_import_no_elevation(self):
        xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<LandXML xmlns="http://www.landxml.org/schema/LandXML-1.2" version="1.2">
  <CgPoints>
    <CgPoint name="5">500.0 600.0</CgPoint>
  </CgPoints>
</LandXML>
"""
        job = import_landxml(io.StringIO(xml))
        p = job.get_point(5)
        assert p is not None
        assert math.isclose(p.northing, 500.0)
        assert math.isclose(p.easting, 600.0)
        assert math.isclose(p.elevation, 0.0)

    def test_import_empty_cgpoints(self):
        xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<LandXML xmlns="http://www.landxml.org/schema/LandXML-1.2" version="1.2">
  <CgPoints/>
</LandXML>
"""
        job = import_landxml(io.StringIO(xml))
        assert job.point_count == 0


# --- Export tests ---


class TestExportLandXMLPoints:
    def test_export_creates_valid_xml(self, tmp_path: Path):
        job = _make_job()
        out = tmp_path / "test.xml"
        export_landxml(job, out)
        tree = ET.parse(out)
        root = tree.getroot()
        assert root.tag == f"{{{NS}}}LandXML"

    def test_export_cgpoints(self, tmp_path: Path):
        job = _make_job()
        out = tmp_path / "test.xml"
        export_landxml(job, out)
        tree = ET.parse(out)
        root = tree.getroot()
        cg_points = root.findall(f".//{{{NS}}}CgPoint")
        assert len(cg_points) == 3

    def test_export_point_attributes(self, tmp_path: Path):
        job = _make_job()
        out = tmp_path / "test.xml"
        export_landxml(job, out)
        tree = ET.parse(out)
        root = tree.getroot()
        first_pt = root.find(f".//{{{NS}}}CgPoint")
        assert first_pt is not None
        assert first_pt.get("name") == "1"
        assert first_pt.get("desc") == "BM1"

    def test_export_point_coordinates(self, tmp_path: Path):
        job = _make_job()
        out = tmp_path / "test.xml"
        export_landxml(job, out)
        tree = ET.parse(out)
        root = tree.getroot()
        first_pt = root.find(f".//{{{NS}}}CgPoint")
        assert first_pt is not None
        coords = first_pt.text.split()
        assert math.isclose(float(coords[0]), 1000.0)
        assert math.isclose(float(coords[1]), 2000.0)
        assert math.isclose(float(coords[2]), 100.0)

    def test_export_to_stringio(self):
        job = _make_job()
        buf = io.StringIO()
        export_landxml(job, buf)
        buf.seek(0)
        text = buf.read()
        assert "<CgPoint" in text
        assert "LandXML" in text


# --- Round-trip tests ---


class TestLandXMLRoundTrip:
    def test_round_trip_file(self, tmp_path: Path):
        job = _make_job()
        out = tmp_path / "round.xml"
        export_landxml(job, out)
        job2 = import_landxml(out)
        assert job2.point_count == 3
        for p_orig in job.points():
            p_new = job2.get_point(p_orig.number)
            assert p_new is not None
            assert math.isclose(p_orig.northing, p_new.northing, abs_tol=0.001)
            assert math.isclose(p_orig.easting, p_new.easting, abs_tol=0.001)
            assert math.isclose(p_orig.elevation, p_new.elevation, abs_tol=0.001)
            assert p_orig.description == p_new.description

    def test_round_trip_stringio(self):
        job = _make_job()
        buf = io.StringIO()
        export_landxml(job, buf)
        buf.seek(0)
        job2 = import_landxml(buf)
        assert job2.point_count == job.point_count


# --- Parcel export tests ---


class TestExportLandXMLParcels:
    def test_parcels_element_present(self, tmp_path: Path):
        job = _make_job()
        parcels = [("Lot1", [1, 2, 3])]
        out = tmp_path / "test.xml"
        export_landxml(job, out, parcels=parcels)
        tree = ET.parse(out)
        root = tree.getroot()
        parcel_elems = root.findall(f".//{{{NS}}}Parcel")
        assert len(parcel_elems) == 1

    def test_parcel_name(self, tmp_path: Path):
        job = _make_job()
        parcels = [("Lot1", [1, 2, 3])]
        out = tmp_path / "test.xml"
        export_landxml(job, out, parcels=parcels)
        tree = ET.parse(out)
        root = tree.getroot()
        parcel = root.find(f".//{{{NS}}}Parcel")
        assert parcel is not None
        assert parcel.get("name") == "Lot1"

    def test_parcel_coordgeom(self, tmp_path: Path):
        job = _make_job()
        parcels = [("Lot1", [1, 2, 3])]
        out = tmp_path / "test.xml"
        export_landxml(job, out, parcels=parcels)
        tree = ET.parse(out)
        root = tree.getroot()
        lines = root.findall(f".//{{{NS}}}Parcels/{{{NS}}}Parcel/{{{NS}}}CoordGeom/{{{NS}}}Line")
        # 3 points = 3 boundary lines (closed polygon: 1->2, 2->3, 3->1)
        assert len(lines) == 3

    def test_multiple_parcels(self, tmp_path: Path):
        job = _make_job()
        parcels = [("Lot1", [1, 2, 3]), ("Lot2", [2, 3])]
        out = tmp_path / "test.xml"
        export_landxml(job, out, parcels=parcels)
        tree = ET.parse(out)
        root = tree.getroot()
        parcel_elems = root.findall(f".//{{{NS}}}Parcel")
        assert len(parcel_elems) == 2


# --- Alignment export tests ---


class TestExportLandXMLAlignments:
    def _make_tangent_alignment(self):
        t = Tangent(
            start_station=0.0,
            length=200.0,
            azimuth=math.radians(45.0),
            start_point=Point(northing=1000.0, easting=2000.0),
        )
        return HorizontalAlignment([t])

    def _make_curve_alignment(self):
        t = Tangent(
            start_station=0.0,
            length=100.0,
            azimuth=math.radians(0.0),
            start_point=Point(northing=1000.0, easting=2000.0),
        )
        c = CircularCurve(
            start_station=100.0,
            length=math.radians(30.0) * 500.0,
            radius=500.0,
            delta=math.radians(30.0),
            direction="R",
            pc_point=Point(northing=1100.0, easting=2000.0),
            center_point=Point(northing=1100.0, easting=2500.0),
            start_azimuth=0.0,
        )
        return HorizontalAlignment([t, c])

    def test_alignment_element_present(self, tmp_path: Path):
        job = _make_job()
        ha = self._make_tangent_alignment()
        out = tmp_path / "test.xml"
        export_landxml(job, out, alignments=[("Main", ha)])
        tree = ET.parse(out)
        root = tree.getroot()
        aligns = root.findall(f".//{{{NS}}}Alignment")
        assert len(aligns) == 1

    def test_alignment_attributes(self, tmp_path: Path):
        job = _make_job()
        ha = self._make_tangent_alignment()
        out = tmp_path / "test.xml"
        export_landxml(job, out, alignments=[("Main", ha)])
        tree = ET.parse(out)
        root = tree.getroot()
        align = root.find(f".//{{{NS}}}Alignment")
        assert align is not None
        assert align.get("name") == "Main"
        assert math.isclose(float(align.get("length")), 200.0, abs_tol=0.01)
        assert math.isclose(float(align.get("staStart")), 0.0)

    def test_tangent_as_line(self, tmp_path: Path):
        job = _make_job()
        ha = self._make_tangent_alignment()
        out = tmp_path / "test.xml"
        export_landxml(job, out, alignments=[("Main", ha)])
        tree = ET.parse(out)
        root = tree.getroot()
        lines = root.findall(f".//{{{NS}}}Line")
        assert len(lines) == 1
        line = lines[0]
        assert math.isclose(float(line.get("length")), 200.0, abs_tol=0.01)

    def test_curve_element(self, tmp_path: Path):
        job = _make_job()
        ha = self._make_curve_alignment()
        out = tmp_path / "test.xml"
        export_landxml(job, out, alignments=[("CurveAlign", ha)])
        tree = ET.parse(out)
        root = tree.getroot()
        curves = root.findall(f".//{{{NS}}}Curve")
        assert len(curves) == 1
        curve = curves[0]
        assert curve.get("rot") == "cw"
        assert math.isclose(float(curve.get("radius")), 500.0, abs_tol=0.01)

    def test_alignment_with_tangent_and_curve(self, tmp_path: Path):
        job = _make_job()
        ha = self._make_curve_alignment()
        out = tmp_path / "test.xml"
        export_landxml(job, out, alignments=[("Mixed", ha)])
        tree = ET.parse(out)
        root = tree.getroot()
        coord_geom = root.find(f".//{{{NS}}}Alignment/{{{NS}}}CoordGeom")
        assert coord_geom is not None
        # Should have 1 Line + 1 Curve
        assert len(coord_geom.findall(f"{{{NS}}}Line")) == 1
        assert len(coord_geom.findall(f"{{{NS}}}Curve")) == 1
