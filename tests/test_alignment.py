"""Tests for the alignment module."""

import math

import pytest

from cogopro.core.point import Point
from cogopro.surveying.alignment import (
    Alignment,
    CircularCurve,
    GradeBreak,
    HorizontalAlignment,
    Tangent,
    VerticalProfile,
)

TOL = 1e-6


# ---------------------------------------------------------------------------
# Horizontal: single tangent
# ---------------------------------------------------------------------------

class TestSingleTangent:
    """station_to_point at start, middle, and end of a single tangent."""

    @pytest.fixture()
    def ha(self):
        t = Tangent(
            start_station=0.0,
            length=500.0,
            azimuth=0.0,  # due north
            start_point=Point(northing=1000.0, easting=5000.0),
        )
        return HorizontalAlignment([t])

    def test_start(self, ha):
        pt = ha.station_to_point(0.0)
        assert math.isclose(pt.northing, 1000.0, abs_tol=TOL)
        assert math.isclose(pt.easting, 5000.0, abs_tol=TOL)

    def test_middle(self, ha):
        pt = ha.station_to_point(250.0)
        assert math.isclose(pt.northing, 1250.0, abs_tol=TOL)
        assert math.isclose(pt.easting, 5000.0, abs_tol=TOL)

    def test_end(self, ha):
        pt = ha.station_to_point(500.0)
        assert math.isclose(pt.northing, 1500.0, abs_tol=TOL)
        assert math.isclose(pt.easting, 5000.0, abs_tol=TOL)


# ---------------------------------------------------------------------------
# Horizontal: tangent + curve + tangent (continuity)
# ---------------------------------------------------------------------------

class TestTangentCurveTangent:
    """Verify continuity at PC and PT for a right-turning 90-degree curve."""

    @pytest.fixture()
    def ha(self):
        R = 100.0
        delta = math.pi / 2  # 90 degrees
        arc_len = R * delta

        # Tangent 1: north from (1000, 5000)
        t1 = Tangent(
            start_station=0.0,
            length=200.0,
            azimuth=0.0,
            start_point=Point(northing=1000.0, easting=5000.0),
        )
        # PC at (1200, 5000); center 100 east at (1200, 5100)
        curve = CircularCurve(
            start_station=200.0,
            length=arc_len,
            radius=R,
            delta=delta,
            direction="R",
            pc_point=Point(northing=1200.0, easting=5000.0),
            center_point=Point(northing=1200.0, easting=5100.0),
            start_azimuth=0.0,
        )
        # PT at (1300, 5100), now heading east
        pt_sta = 200.0 + arc_len
        t2 = Tangent(
            start_station=pt_sta,
            length=200.0,
            azimuth=math.pi / 2,
            start_point=Point(northing=1300.0, easting=5100.0),
        )
        return HorizontalAlignment([t1, curve, t2])

    def test_continuity_at_pc(self, ha):
        pt_t1 = ha.elements[0].point_at(200.0)
        pt_curve = ha.elements[1].point_at(200.0)
        assert math.isclose(pt_t1.northing, pt_curve.northing, abs_tol=TOL)
        assert math.isclose(pt_t1.easting, pt_curve.easting, abs_tol=TOL)

    def test_continuity_at_pt(self, ha):
        pt_sta = ha.elements[1].end_station
        pt_curve = ha.elements[1].point_at(pt_sta)
        pt_t2 = ha.elements[2].point_at(pt_sta)
        assert math.isclose(pt_curve.northing, pt_t2.northing, abs_tol=TOL)
        assert math.isclose(pt_curve.easting, pt_t2.easting, abs_tol=TOL)

    def test_curve_midpoint(self, ha):
        """Midpoint of a 90-degree right curve from north heading."""
        mid_sta = 200.0 + 100.0 * (math.pi / 4)
        pt = ha.station_to_point(mid_sta)
        # At 45-degree sweep from center (1200, 5100)
        # radial az = 270deg + 45deg = 315deg = -45deg
        # N = 1200 + 100*cos(315deg) = 1200 + 70.711
        # E = 5100 + 100*sin(315deg) = 5100 - 70.711
        expected_n = 1200.0 + 100.0 * math.cos(math.radians(315))
        expected_e = 5100.0 + 100.0 * math.sin(math.radians(315))
        assert math.isclose(pt.northing, expected_n, abs_tol=TOL)
        assert math.isclose(pt.easting, expected_e, abs_tol=TOL)


# ---------------------------------------------------------------------------
# point_to_station_offset
# ---------------------------------------------------------------------------

class TestStationOffset:
    """Project points onto a single northward tangent."""

    @pytest.fixture()
    def ha(self):
        t = Tangent(
            start_station=0.0,
            length=500.0,
            azimuth=0.0,
            start_point=Point(northing=1000.0, easting=5000.0),
        )
        return HorizontalAlignment([t])

    def test_point_on_centerline(self, ha):
        pt = Point(northing=1250.0, easting=5000.0)
        sta, off = ha.point_to_station_offset(pt)
        assert math.isclose(sta, 250.0, abs_tol=TOL)
        assert math.isclose(off, 0.0, abs_tol=TOL)

    def test_point_offset_right(self, ha):
        # 10 units east of the alignment at station 250 (right of north)
        pt = Point(northing=1250.0, easting=5010.0)
        sta, off = ha.point_to_station_offset(pt)
        assert math.isclose(sta, 250.0, abs_tol=TOL)
        assert math.isclose(off, 10.0, abs_tol=TOL)

    def test_point_offset_left(self, ha):
        # 15 units west = left of north
        pt = Point(northing=1250.0, easting=4985.0)
        sta, off = ha.point_to_station_offset(pt)
        assert math.isclose(sta, 250.0, abs_tol=TOL)
        assert math.isclose(off, -15.0, abs_tol=TOL)


# ---------------------------------------------------------------------------
# Vertical profile: grade only
# ---------------------------------------------------------------------------

class TestVerticalGradeOnly:
    """Elevation on a simple two-break profile (no vertical curves)."""

    @pytest.fixture()
    def vp(self):
        return VerticalProfile([
            GradeBreak(station=0.0, elevation=100.0),
            GradeBreak(station=500.0, elevation=110.0),
        ])

    def test_start(self, vp):
        assert math.isclose(vp.elevation_at(0.0), 100.0, abs_tol=TOL)

    def test_middle(self, vp):
        # Grade = 0.02; at sta 250 -> 100 + 0.02*250 = 105
        assert math.isclose(vp.elevation_at(250.0), 105.0, abs_tol=TOL)

    def test_end(self, vp):
        assert math.isclose(vp.elevation_at(500.0), 110.0, abs_tol=TOL)


# ---------------------------------------------------------------------------
# Vertical profile: with vertical curve
# ---------------------------------------------------------------------------

class TestVerticalCurveSection:
    """Crest curve: G1=+2 %, G2=-2 %, L=200 at PVI station 300."""

    @pytest.fixture()
    def vp(self):
        return VerticalProfile([
            GradeBreak(station=0.0, elevation=100.0),
            GradeBreak(station=300.0, elevation=106.0, curve_length=200.0),
            GradeBreak(station=600.0, elevation=100.0),
        ])

    def test_on_tangent_before_curve(self, vp):
        # Before BVC (sta 200): tangent grade +2 %
        assert math.isclose(vp.elevation_at(100.0), 102.0, abs_tol=TOL)

    def test_at_bvc(self, vp):
        # BVC at sta 200, elev = 106 - 0.02*100 = 104
        assert math.isclose(vp.elevation_at(200.0), 104.0, abs_tol=TOL)

    def test_at_pvi_on_curve(self, vp):
        # x=100 from BVC
        # elev = 104 + 0.02*100 + ((-0.04)/(400))*10000 = 106 - 1 = 105
        assert math.isclose(vp.elevation_at(300.0), 105.0, abs_tol=TOL)

    def test_at_evc(self, vp):
        # x=200: 104 + 0.02*200 + ((-0.04)/400)*40000 = 104 + 4 - 4 = 104
        assert math.isclose(vp.elevation_at(400.0), 104.0, abs_tol=TOL)

    def test_on_tangent_after_curve(self, vp):
        # After EVC (sta 400): tangent grade -2 %
        # At sta 500: 106 + (-0.02)*(500-300) = 106 - 4 = 102
        assert math.isclose(vp.elevation_at(500.0), 102.0, abs_tol=TOL)


# ---------------------------------------------------------------------------
# Combined 3-D alignment
# ---------------------------------------------------------------------------

class TestCombinedAlignment:
    """point_at_station returns correct N, E, Z."""

    @pytest.fixture()
    def alignment(self):
        ha = HorizontalAlignment([
            Tangent(
                start_station=0.0,
                length=500.0,
                azimuth=0.0,
                start_point=Point(northing=1000.0, easting=5000.0),
            )
        ])
        vp = VerticalProfile([
            GradeBreak(station=0.0, elevation=100.0),
            GradeBreak(station=500.0, elevation=110.0),
        ])
        return Alignment(ha, vp)

    def test_point_at_station(self, alignment):
        pt = alignment.point_at_station(250.0)
        assert math.isclose(pt.northing, 1250.0, abs_tol=TOL)
        assert math.isclose(pt.easting, 5000.0, abs_tol=TOL)
        assert math.isclose(pt.elevation, 105.0, abs_tol=TOL)

    def test_station_offset(self, alignment):
        # Query a point offset 10 east at station 250
        pt = Point(northing=1250.0, easting=5010.0)
        sta, off, design_z = alignment.station_offset(pt)
        assert math.isclose(sta, 250.0, abs_tol=TOL)
        assert math.isclose(off, 10.0, abs_tol=TOL)
        assert math.isclose(design_z, 105.0, abs_tol=TOL)
