"""Tests for IFC 4X3 import/export."""

from __future__ import annotations

import pytest

ifcopenshell = pytest.importorskip("ifcopenshell")

from cogokit.core.crs import CRS
from cogokit.core.job import Job
from cogokit.core.point import Point
from cogokit.io.ifc import export_ifc, import_ifc
from cogokit.surveying.alignment import (
    CircularCurve,
    HorizontalAlignment,
    Tangent,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_job(*points: Point, name: str = "TestJob") -> Job:
    """Create a Job pre-populated with the given points."""
    job = Job(name=name)
    for pt in points:
        job.add_point(pt)
    return job


# ---------------------------------------------------------------------------
# Phase 1: Points export/import
# ---------------------------------------------------------------------------


class TestExportCreatesValidIfc:
    """Exported file should exist and be parseable by ifcopenshell."""

    def test_file_exists(self, tmp_path):
        job = _make_job(Point(100.0, 200.0, 50.0, number=1))
        dest = tmp_path / "test.ifc"
        export_ifc(job, dest)
        assert dest.exists()

    def test_file_parseable(self, tmp_path):
        job = _make_job(Point(100.0, 200.0, 50.0, number=1))
        dest = tmp_path / "test.ifc"
        export_ifc(job, dest)
        model = ifcopenshell.open(str(dest))
        assert model.schema_identifier.startswith("IFC4X3")


class TestExportPointCoordinates:
    """Verify coordinate mapping: Point(N, E, Z) -> IFC(X=E, Y=N, Z=Z)."""

    def test_coordinate_order(self, tmp_path):
        job = _make_job(Point(100.0, 200.0, 50.0, number=1))
        dest = tmp_path / "test.ifc"
        export_ifc(job, dest)

        model = ifcopenshell.open(str(dest))
        annotations = model.by_type("IfcAnnotation")
        assert len(annotations) == 1

        ann = annotations[0]
        coords = ann.Representation.Representations[0].Items[0].Coordinates
        # IFC: (X=Easting, Y=Northing, Z=Elevation)
        assert coords == (200.0, 100.0, 50.0)

    def test_point_metadata(self, tmp_path):
        job = _make_job(Point(0.0, 0.0, 0.0, number=42, description="CP"))
        dest = tmp_path / "test.ifc"
        export_ifc(job, dest)

        model = ifcopenshell.open(str(dest))
        ann = model.by_type("IfcAnnotation")[0]
        assert ann.Name == "42"
        assert ann.Description == "CP"
        assert ann.ObjectType == "SurveyPoint"


class TestRoundTripPoints:
    """Export then import should preserve point data."""

    def test_single_point(self, tmp_path):
        original = Point(1000.0, 2000.0, 300.0, number=1, description="BM")
        job = _make_job(original)
        dest = tmp_path / "roundtrip.ifc"
        export_ifc(job, dest)

        imported = import_ifc(dest)
        pts = list(imported.points())
        assert len(pts) == 1
        assert pts[0] == original

    def test_multiple_points(self, tmp_path):
        points = [
            Point(100.0, 200.0, 10.0, number=1, description="A"),
            Point(300.0, 400.0, 20.0, number=2, description="B"),
            Point(500.0, 600.0, 30.0, number=3, description="C"),
        ]
        job = _make_job(*points)
        dest = tmp_path / "roundtrip_multi.ifc"
        export_ifc(job, dest)

        imported = import_ifc(dest)
        imported_pts = sorted(imported.points(), key=lambda p: p.number)
        assert len(imported_pts) == 3
        for orig, imp in zip(points, imported_pts):
            assert orig == imp

    def test_zero_elevation(self, tmp_path):
        original = Point(100.0, 200.0, 0.0, number=1)
        job = _make_job(original)
        dest = tmp_path / "zero_elev.ifc"
        export_ifc(job, dest)

        imported = import_ifc(dest)
        pts = list(imported.points())
        assert len(pts) == 1
        assert pts[0].elevation == 0.0


class TestEmptyJob:
    """Empty job should produce valid IFC with no points."""

    def test_empty_export(self, tmp_path):
        job = Job(name="Empty")
        dest = tmp_path / "empty.ifc"
        export_ifc(job, dest)
        assert dest.exists()

        model = ifcopenshell.open(str(dest))
        assert len(model.by_type("IfcAnnotation")) == 0
        assert len(model.by_type("IfcProject")) == 1


class TestImportNonexistentFile:
    """Importing a missing file should raise FileNotFoundError."""

    def test_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            import_ifc(tmp_path / "does_not_exist.ifc")


# ---------------------------------------------------------------------------
# Phase 2: Georeferencing (CRS)
# ---------------------------------------------------------------------------


class TestExportWithCrs:
    """CRS information should be written as IfcProjectedCRS + IfcMapConversion."""

    def test_utm_crs_export(self, tmp_path):
        job = _make_job(Point(100.0, 200.0, 0.0, number=1))
        crs = CRS.utm(zone=17, hemisphere="N")
        dest = tmp_path / "crs.ifc"
        export_ifc(job, dest, crs=crs)

        model = ifcopenshell.open(str(dest))
        ifc_crs_list = model.by_type("IfcProjectedCRS")
        assert len(ifc_crs_list) == 1
        assert ifc_crs_list[0].Name == "EPSG:32617"
        assert ifc_crs_list[0].MapProjection == "UTM"
        assert ifc_crs_list[0].MapZone == "17N"

    def test_utm_crs_roundtrip(self, tmp_path):
        job = _make_job(Point(100.0, 200.0, 0.0, number=1))
        crs = CRS.utm(zone=17, hemisphere="N")
        dest = tmp_path / "crs_rt.ifc"
        export_ifc(job, dest, crs=crs)

        imported = import_ifc(dest)
        assert imported.crs is not None
        assert imported.crs.kind == "utm"
        assert imported.crs.zone == 17
        assert imported.crs.hemisphere == "N"

    def test_utm_south_hemisphere(self, tmp_path):
        job = _make_job(Point(100.0, 200.0, 0.0, number=1))
        crs = CRS.utm(zone=33, hemisphere="S")
        dest = tmp_path / "crs_south.ifc"
        export_ifc(job, dest, crs=crs)

        imported = import_ifc(dest)
        assert imported.crs is not None
        assert imported.crs.zone == 33
        assert imported.crs.hemisphere == "S"


# ---------------------------------------------------------------------------
# Phase 3: Alignment export
# ---------------------------------------------------------------------------


class TestExportAlignment:
    """Alignment elements should be written as IfcAlignment entities."""

    def _make_alignment(self) -> HorizontalAlignment:
        tangent = Tangent(
            start_station=0.0,
            length=100.0,
            azimuth=0.0,
            start_point=Point(0.0, 0.0),
        )
        curve = CircularCurve(
            start_station=100.0,
            length=50.0,
            radius=200.0,
            delta=0.25,
            direction="R",
            pc_point=Point(100.0, 0.0),
            center_point=Point(100.0, 200.0),
            start_azimuth=0.0,
        )
        return HorizontalAlignment([tangent, curve])

    def test_alignment_export(self, tmp_path):
        job = Job(name="AlignTest")
        dest = tmp_path / "align.ifc"
        align = self._make_alignment()
        export_ifc(job, dest, alignments=[("TestAlign", align)])

        model = ifcopenshell.open(str(dest))
        alignments = model.by_type("IfcAlignment")
        assert len(alignments) == 1
        assert alignments[0].Name == "TestAlign"

    def test_alignment_segments(self, tmp_path):
        job = Job(name="AlignTest")
        dest = tmp_path / "align_seg.ifc"
        align = self._make_alignment()
        export_ifc(job, dest, alignments=[("TestAlign", align)])

        model = ifcopenshell.open(str(dest))
        segments = model.by_type("IfcAlignmentSegment")
        assert len(segments) == 2

        # Check design parameters
        params = [s.DesignParameters for s in segments]
        types = [p.PredefinedType for p in params]
        assert "LINE" in types
        assert "CIRCULARARC" in types


# ---------------------------------------------------------------------------
# Phase 4: Parcel export
# ---------------------------------------------------------------------------


class TestExportParcel:
    """Parcels should be written as IfcAnnotation with polyline geometry."""

    def test_parcel_export(self, tmp_path):
        job = Job(name="ParcelTest")
        boundary = [
            Point(0.0, 0.0, 0.0),
            Point(100.0, 0.0, 0.0),
            Point(100.0, 100.0, 0.0),
            Point(0.0, 100.0, 0.0),
        ]
        dest = tmp_path / "parcel.ifc"
        export_ifc(job, dest, parcels=[("Lot1", boundary)])

        model = ifcopenshell.open(str(dest))
        parcels = [a for a in model.by_type("IfcAnnotation")
                   if a.ObjectType == "Parcel"]
        assert len(parcels) == 1
        assert parcels[0].Name == "Lot1"

    def test_parcel_geometry(self, tmp_path):
        job = Job(name="ParcelTest")
        boundary = [
            Point(0.0, 0.0, 0.0),
            Point(100.0, 0.0, 0.0),
            Point(100.0, 100.0, 0.0),
        ]
        dest = tmp_path / "parcel_geom.ifc"
        export_ifc(job, dest, parcels=[("Tri", boundary)])

        model = ifcopenshell.open(str(dest))
        polylines = model.by_type("IfcPolyline")
        assert len(polylines) == 1
        # Should be closed: 3 boundary points + 1 closing point = 4
        assert len(polylines[0].Points) == 4

    def test_parcel_too_few_points_skipped(self, tmp_path):
        job = Job(name="ParcelTest")
        boundary = [Point(0.0, 0.0, 0.0), Point(100.0, 0.0, 0.0)]
        dest = tmp_path / "parcel_skip.ifc"
        export_ifc(job, dest, parcels=[("TooSmall", boundary)])

        model = ifcopenshell.open(str(dest))
        parcels = [a for a in model.by_type("IfcAnnotation")
                   if a.ObjectType == "Parcel"]
        assert len(parcels) == 0


# ---------------------------------------------------------------------------
# Job metadata
# ---------------------------------------------------------------------------


class TestJobMetadata:
    """Job name and description should be preserved."""

    def test_project_name(self, tmp_path):
        job = Job(name="MySurvey", description="Test project")
        dest = tmp_path / "meta.ifc"
        export_ifc(job, dest)

        imported = import_ifc(dest)
        assert imported.name == "meta"  # from filename stem
        assert imported.description == "Test project"
