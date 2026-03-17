"""Tests for the alignment module."""

import math

import pytest

from cogokit.core.point import Point
from cogokit.surveying.alignment import (
    Alignment,
    CircularCurve,
    GradeBreak,
    HorizontalAlignment,
    Spiral,
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


# ---------------------------------------------------------------------------
# Spiral element: entry (tangent → curve)
# ---------------------------------------------------------------------------

class TestEntrySpiralElement:
    """Point computation for a right entry spiral heading north."""

    @pytest.fixture()
    def sp(self):
        return Spiral(
            start_station=0.0,
            length=200.0,
            radius=500.0,
            direction="R",
            start_azimuth=0.0,
            start_point=Point(northing=1000.0, easting=5000.0),
            entry=True,
        )

    def test_start(self, sp):
        pt = sp.point_at(0.0)
        assert math.isclose(pt.northing, 1000.0, abs_tol=TOL)
        assert math.isclose(pt.easting, 5000.0, abs_tol=TOL)

    def test_end_matches_solver(self, sp):
        """End coordinates should match the standalone spiral() solver."""
        from cogokit.solvers.horizontal_curve import spiral as spiral_params

        params = spiral_params(200.0, 500.0)
        pt = sp.point_at(200.0)
        # az=0 (north), direction R: N = start_N + X, E = start_E + Y
        assert math.isclose(pt.northing, 1000.0 + params.X, abs_tol=0.001)
        assert math.isclose(pt.easting, 5000.0 + params.Y, abs_tol=0.001)

    def test_midpoint_between_start_and_end(self, sp):
        """Midpoint should be between start and end coordinates."""
        pt_mid = sp.point_at(100.0)
        pt_end = sp.point_at(200.0)
        assert 1000.0 < pt_mid.northing < pt_end.northing
        assert 5000.0 < pt_mid.easting < pt_end.easting

    def test_end_azimuth(self, sp):
        theta_s = 200.0 / (2.0 * 500.0)  # = 0.2 rad
        assert math.isclose(sp.end_azimuth, 0.2, abs_tol=TOL)


class TestEntrySpiralLeft:
    """Left entry spiral should deflect to the left (negative easting offset)."""

    def test_left_deflection(self):
        sp = Spiral(
            start_station=0.0,
            length=200.0,
            radius=500.0,
            direction="L",
            start_azimuth=0.0,
            start_point=Point(northing=1000.0, easting=5000.0),
            entry=True,
        )
        pt = sp.point_at(200.0)
        # Left spiral heading north deflects west (easting decreases)
        assert pt.easting < 5000.0
        assert pt.northing > 1000.0


# ---------------------------------------------------------------------------
# Spiral element: exit (curve → tangent)
# ---------------------------------------------------------------------------

class TestExitSpiralElement:
    """Exit spiral should produce same total deflection as entry."""

    def test_exit_total_deflection(self):
        """Total displacement should be same magnitude as entry spiral."""
        entry = Spiral(
            start_station=0.0, length=200.0, radius=500.0,
            direction="R", start_azimuth=0.0,
            start_point=Point(northing=0.0, easting=0.0), entry=True,
        )
        exit_sp = Spiral(
            start_station=0.0, length=200.0, radius=500.0,
            direction="R", start_azimuth=0.0,
            start_point=Point(northing=0.0, easting=0.0), entry=False,
        )
        pt_entry = entry.point_at(200.0)
        pt_exit = exit_sp.point_at(200.0)
        # Same arc length, same total deflection angle theta_s
        dist_entry = math.hypot(pt_entry.northing, pt_entry.easting)
        dist_exit = math.hypot(pt_exit.northing, pt_exit.easting)
        assert math.isclose(dist_entry, dist_exit, rel_tol=0.01)

    def test_exit_azimuth_change(self):
        """Exit spiral should deflect by theta_s."""
        sp = Spiral(
            start_station=0.0, length=200.0, radius=500.0,
            direction="R", start_azimuth=0.5,
            start_point=Point(northing=0.0, easting=0.0), entry=False,
        )
        theta_s = 200.0 / (2.0 * 500.0)
        assert math.isclose(sp.end_azimuth, 0.5 + theta_s, abs_tol=TOL)


# ---------------------------------------------------------------------------
# SCS transition: Tangent → Spiral → Curve → Spiral → Tangent (continuity)
# ---------------------------------------------------------------------------

class TestSCSContinuity:
    """Verify coordinate continuity at all junctions of a symmetric SCS."""

    @pytest.fixture()
    def elements(self):
        R = 500.0
        Ls = 200.0
        theta_s = Ls / (2.0 * R)  # 0.2 rad
        delta_curve = math.radians(30.0)  # circular curve central angle

        # Tangent 1: north from (1000, 5000), length 300
        t1 = Tangent(
            start_station=0.0, length=300.0, azimuth=0.0,
            start_point=Point(northing=1000.0, easting=5000.0),
        )

        # Entry spiral: starts at tangent 1 end
        ts_start = t1.point_at(t1.end_station)
        entry_sp = Spiral(
            start_station=300.0, length=Ls, radius=R,
            direction="R", start_azimuth=0.0,
            start_point=ts_start, entry=True,
        )

        # Circular curve: starts at entry spiral end
        pc = entry_sp.point_at(entry_sp.end_station)
        az_at_pc = entry_sp.end_azimuth
        # Center is R to the right of PC along perpendicular
        center_n = pc.northing - R * math.sin(az_at_pc)
        center_e = pc.easting + R * math.cos(az_at_pc)
        # Wait, for right curve: center is to the right
        # Right of azimuth az: perpendicular direction = az + pi/2
        # actually, the center of a right curve is to the RIGHT of the direction of travel
        # Right direction relative to az: (-sin(az), cos(az)) in (N, E)
        center_n = pc.northing + R * (-math.sin(az_at_pc))
        center_e = pc.easting + R * math.cos(az_at_pc)
        # Hmm let me be more careful. For azimuth az:
        # Forward: (cos(az), sin(az)) in (N, E)
        # Right: (-sin(az), cos(az)) in (N, E)
        # Wait that's not right either. Let me think:
        # azimuth 0 = north. Right of north = east.
        # Forward (N, E) = (1, 0). Right should be (0, 1).
        # (-sin(0), cos(0)) = (0, 1) ✓
        # azimuth pi/2 = east. Right of east = south.
        # (-sin(pi/2), cos(pi/2)) = (-1, 0) ✓
        # So right-perpendicular = (-sin(az), cos(az)) is correct.
        center = Point(
            northing=pc.northing + R * (-math.sin(az_at_pc)),
            easting=pc.easting + R * math.cos(az_at_pc),
        )
        curve = CircularCurve(
            start_station=entry_sp.end_station, length=R * delta_curve,
            radius=R, delta=delta_curve, direction="R",
            pc_point=pc, center_point=center, start_azimuth=az_at_pc,
        )

        # Exit spiral: starts at curve end
        pt_sta = curve.end_station
        sc_start = curve.point_at(pt_sta)
        az_at_sc = az_at_pc + delta_curve  # right curve adds delta
        exit_sp = Spiral(
            start_station=pt_sta, length=Ls, radius=R,
            direction="R", start_azimuth=az_at_sc,
            start_point=sc_start, entry=False,
        )

        # Tangent 2: starts at exit spiral end
        st_start = exit_sp.point_at(exit_sp.end_station)
        az_t2 = az_at_sc + theta_s  # exit spiral adds theta_s
        t2 = Tangent(
            start_station=exit_sp.end_station, length=300.0,
            azimuth=az_t2, start_point=st_start,
        )

        return [t1, entry_sp, curve, exit_sp, t2]

    def test_tangent_to_entry_spiral(self, elements):
        t1, entry_sp = elements[0], elements[1]
        pt_a = t1.point_at(t1.end_station)
        pt_b = entry_sp.point_at(entry_sp.start_station)
        assert math.isclose(pt_a.northing, pt_b.northing, abs_tol=0.01)
        assert math.isclose(pt_a.easting, pt_b.easting, abs_tol=0.01)

    def test_entry_spiral_to_curve(self, elements):
        entry_sp, curve = elements[1], elements[2]
        pt_a = entry_sp.point_at(entry_sp.end_station)
        pt_b = curve.point_at(curve.start_station)
        assert math.isclose(pt_a.northing, pt_b.northing, abs_tol=0.01)
        assert math.isclose(pt_a.easting, pt_b.easting, abs_tol=0.01)

    def test_curve_to_exit_spiral(self, elements):
        curve, exit_sp = elements[2], elements[3]
        pt_a = curve.point_at(curve.end_station)
        pt_b = exit_sp.point_at(exit_sp.start_station)
        assert math.isclose(pt_a.northing, pt_b.northing, abs_tol=0.01)
        assert math.isclose(pt_a.easting, pt_b.easting, abs_tol=0.01)

    def test_exit_spiral_to_tangent(self, elements):
        exit_sp, t2 = elements[3], elements[4]
        pt_a = exit_sp.point_at(exit_sp.end_station)
        pt_b = t2.point_at(t2.start_station)
        assert math.isclose(pt_a.northing, pt_b.northing, abs_tol=0.01)
        assert math.isclose(pt_a.easting, pt_b.easting, abs_tol=0.01)

    def test_alignment_traversal(self, elements):
        """Full alignment should be traversable without errors."""
        ha = HorizontalAlignment(elements)
        start = ha.station_to_point(0.0)
        end = ha.station_to_point(ha.elements[-1].end_station)
        assert start.northing < end.northing  # progressed northward


# ---------------------------------------------------------------------------
# Standalone spiral: Tangent → Spiral → Tangent
# ---------------------------------------------------------------------------

class TestStandaloneSpiralTransition:
    """A single spiral between two tangents."""

    def test_continuity(self):
        sp = Spiral(
            start_station=200.0, length=150.0, radius=400.0,
            direction="R", start_azimuth=0.0,
            start_point=Point(northing=1200.0, easting=5000.0),
            entry=True,
        )
        end_pt = sp.point_at(sp.end_station)
        end_az = sp.end_azimuth

        t2 = Tangent(
            start_station=sp.end_station, length=200.0,
            azimuth=end_az, start_point=end_pt,
        )
        pt_a = sp.point_at(sp.end_station)
        pt_b = t2.point_at(t2.start_station)
        assert math.isclose(pt_a.northing, pt_b.northing, abs_tol=0.001)
        assert math.isclose(pt_a.easting, pt_b.easting, abs_tol=0.001)


# ---------------------------------------------------------------------------
# Station / offset through spiral
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Asymmetric SCS: different entry/exit spiral lengths
# ---------------------------------------------------------------------------

class TestAsymmetricSCS:
    """SCS with different entry and exit spiral lengths."""

    def test_asymmetric_junction_continuity(self):
        R = 500.0
        Ls1 = 80.0   # shorter entry spiral
        Ls2 = 120.0   # longer exit spiral
        delta_c = math.radians(15)

        t1 = Tangent(
            start_station=0.0, length=200.0, azimuth=0.0,
            start_point=Point(northing=0.0, easting=0.0),
        )
        sp_entry = Spiral(
            start_station=200.0, length=Ls1, radius=R,
            direction="R", start_azimuth=0.0,
            start_point=t1.point_at(200.0), entry=True,
        )
        sp_end = sp_entry.point_at(sp_entry.end_station)
        curve_az = sp_entry.azimuth_at(sp_entry.end_station)
        center = Point(
            northing=sp_end.northing + R * (-math.sin(curve_az)),
            easting=sp_end.easting + R * math.cos(curve_az),
        )
        curve = CircularCurve(
            start_station=sp_entry.end_station, length=R * delta_c,
            radius=R, delta=delta_c, direction="R",
            pc_point=sp_end, center_point=center, start_azimuth=curve_az,
        )
        curve_end = curve.point_at(curve.end_station)
        curve_end_az = curve_az + delta_c
        sp_exit = Spiral(
            start_station=curve.end_station, length=Ls2, radius=R,
            direction="R", start_azimuth=curve_end_az,
            start_point=curve_end, entry=False,
        )

        # Tangent → entry spiral
        pt1 = t1.point_at(200.0)
        pt2 = sp_entry.point_at(200.0)
        assert math.isclose(pt1.northing, pt2.northing, abs_tol=TOL)
        assert math.isclose(pt1.easting, pt2.easting, abs_tol=TOL)

        # Entry spiral → curve
        pt3 = sp_entry.point_at(sp_entry.end_station)
        pt4 = curve.point_at(curve.start_station)
        assert math.isclose(pt3.northing, pt4.northing, abs_tol=TOL)
        assert math.isclose(pt3.easting, pt4.easting, abs_tol=TOL)

        # Curve → exit spiral
        pt5 = curve.point_at(curve.end_station)
        pt6 = sp_exit.point_at(sp_exit.start_station)
        assert math.isclose(pt5.northing, pt6.northing, abs_tol=TOL)
        assert math.isclose(pt5.easting, pt6.easting, abs_tol=TOL)


# ---------------------------------------------------------------------------
# Reverse spiral: direction change at inflection
# ---------------------------------------------------------------------------

class TestReverseSpiralDirection:
    """Exit spiral (R) → Entry spiral (L) with continuity at inflection."""

    def test_reverse_spiral_continuity(self):
        R = 500.0
        Ls = 100.0
        sp_exit_r = Spiral(
            start_station=0.0, length=Ls, radius=R,
            direction="R", start_azimuth=0.0,
            start_point=Point(northing=0.0, easting=0.0), entry=False,
        )
        exit_end = sp_exit_r.point_at(sp_exit_r.end_station)
        exit_end_az = sp_exit_r.azimuth_at(sp_exit_r.end_station)

        sp_entry_l = Spiral(
            start_station=sp_exit_r.end_station, length=Ls, radius=R,
            direction="L", start_azimuth=exit_end_az,
            start_point=exit_end, entry=True,
        )

        # Continuity at inflection point
        pt1 = sp_exit_r.point_at(sp_exit_r.end_station)
        pt2 = sp_entry_l.point_at(sp_entry_l.start_station)
        assert math.isclose(pt1.northing, pt2.northing, abs_tol=TOL)
        assert math.isclose(pt1.easting, pt2.easting, abs_tol=TOL)

    def test_reverse_spiral_deflects_opposite(self):
        """Left spiral after right should offset to the left."""
        R = 500.0
        Ls = 100.0
        sp_exit_r = Spiral(
            start_station=0.0, length=Ls, radius=R,
            direction="R", start_azimuth=0.0,
            start_point=Point(northing=0.0, easting=0.0), entry=False,
        )
        exit_end = sp_exit_r.point_at(sp_exit_r.end_station)
        exit_end_az = sp_exit_r.azimuth_at(sp_exit_r.end_station)

        sp_entry_l = Spiral(
            start_station=sp_exit_r.end_station, length=Ls, radius=R,
            direction="L", start_azimuth=exit_end_az,
            start_point=exit_end, entry=True,
        )

        # End of right spiral was offsetting east; left spiral should offset west
        l_end = sp_entry_l.point_at(sp_entry_l.end_station)
        tangent_end = Point(
            northing=exit_end.northing + Ls * math.cos(exit_end_az),
            easting=exit_end.easting + Ls * math.sin(exit_end_az),
        )
        # Left curve should deflect to the left (lower easting than straight)
        assert l_end.easting < tangent_end.easting


# ---------------------------------------------------------------------------
# Station / offset through spiral
# ---------------------------------------------------------------------------

class TestSpiralStationOffset:
    """Project a point onto a spiral element."""

    def test_point_on_spiral(self):
        sp = Spiral(
            start_station=0.0, length=200.0, radius=500.0,
            direction="R", start_azimuth=0.0,
            start_point=Point(northing=1000.0, easting=5000.0),
            entry=True,
        )
        ha = HorizontalAlignment([sp])
        # Get a point on the spiral at station 100
        pt_on = sp.point_at(100.0)
        sta, off = ha.point_to_station_offset(pt_on)
        assert math.isclose(sta, 100.0, abs_tol=0.1)
        assert math.isclose(off, 0.0, abs_tol=0.1)

    def test_point_offset_from_spiral(self):
        sp = Spiral(
            start_station=0.0, length=200.0, radius=500.0,
            direction="R", start_azimuth=0.0,
            start_point=Point(northing=1000.0, easting=5000.0),
            entry=True,
        )
        ha = HorizontalAlignment([sp])
        # Point slightly to the right of the spiral midpoint
        pt_on = sp.point_at(100.0)
        # Azimuth at station 100
        az = sp.azimuth_at(100.0)
        # Offset 10 units to the right: (-sin(az), cos(az))
        offset_pt = Point(
            northing=pt_on.northing + 10.0 * (-math.sin(az)),
            easting=pt_on.easting + 10.0 * math.cos(az),
        )
        sta, off = ha.point_to_station_offset(offset_pt)
        assert math.isclose(sta, 100.0, abs_tol=0.5)
        assert math.isclose(off, 10.0, abs_tol=0.5)
