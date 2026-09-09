"""Tests for cross-section analysis and earthwork volume computations."""

import math

import pytest

from cogokit.surveying.cross_sections import (
    CrossSection,
    CrossSectionPoint,
    DesignTemplate,
    average_end_area,
    compute_earthwork,
    mass_haul,
    prismoidal_volume,
    section_area,
)


# ---------------------------------------------------------------------------
# section_area tests
# ---------------------------------------------------------------------------


def test_simple_rectangular_cut():
    """Flat ground 2m above flat design → pure cut area.

    Ground at elev 102, design template flat at elev 0 (relative),
    design CL at 100 → design absolute = 100.
    Offsets: -10 to +10 → width 20, height 2 → area = 40.
    """
    ground = CrossSection(
        station=0.0,
        points=[
            CrossSectionPoint(-10.0, 102.0),
            CrossSectionPoint(0.0, 102.0),
            CrossSectionPoint(10.0, 102.0),
        ],
        centerline_elevation=102.0,
    )
    template = DesignTemplate(
        points=[
            CrossSectionPoint(-10.0, 0.0),
            CrossSectionPoint(0.0, 0.0),
            CrossSectionPoint(10.0, 0.0),
        ]
    )
    cut, fill = section_area(ground, template, design_cl_elevation=100.0)
    assert math.isclose(cut, 40.0, abs_tol=1e-6)
    assert math.isclose(fill, 0.0, abs_tol=1e-6)


def test_simple_rectangular_fill():
    """Flat ground 3m below flat design → pure fill area.

    Ground at elev 97, design CL at 100 → fill height 3, width 20 → area 60.
    """
    ground = CrossSection(
        station=0.0,
        points=[
            CrossSectionPoint(-10.0, 97.0),
            CrossSectionPoint(0.0, 97.0),
            CrossSectionPoint(10.0, 97.0),
        ],
        centerline_elevation=97.0,
    )
    template = DesignTemplate(
        points=[
            CrossSectionPoint(-10.0, 0.0),
            CrossSectionPoint(0.0, 0.0),
            CrossSectionPoint(10.0, 0.0),
        ]
    )
    cut, fill = section_area(ground, template, design_cl_elevation=100.0)
    assert math.isclose(cut, 0.0, abs_tol=1e-6)
    assert math.isclose(fill, 60.0, abs_tol=1e-6)


def test_mixed_cut_fill_section():
    """Ground crosses design template — produces both cut and fill.

    Design is flat at absolute elevation 100 from offset -10 to +10.
    Ground goes from 102 (at -10) linearly to 98 (at +10).
    At offset -10: diff = +2 (cut)
    At offset +10: diff = -2 (fill)
    Zero crossing at offset 0.

    Left half (-10 to 0): triangle area = 0.5 * 10 * 2 = 10 (cut)
    Right half (0 to +10): triangle area = 0.5 * 10 * 2 = 10 (fill)
    """
    ground = CrossSection(
        station=0.0,
        points=[
            CrossSectionPoint(-10.0, 102.0),
            CrossSectionPoint(10.0, 98.0),
        ],
    )
    template = DesignTemplate(
        points=[
            CrossSectionPoint(-10.0, 0.0),
            CrossSectionPoint(10.0, 0.0),
        ]
    )
    cut, fill = section_area(ground, template, design_cl_elevation=100.0)
    assert math.isclose(cut, 10.0, abs_tol=1e-6)
    assert math.isclose(fill, 10.0, abs_tol=1e-6)


def test_sloped_design_template():
    """Design template with side slopes.

    Ground flat at 105. Template: CL at 0, slopes down 1:1 to ±5.
    Design CL elev = 100. So design absolute: 100 at CL, 95 at ±5.
    Cut heights: 10 at ±5, 5 at CL.
    Area = 2 * (0.5 * (10 + 5) * 5) = 75.
    """
    ground = CrossSection(
        station=0.0,
        points=[
            CrossSectionPoint(-5.0, 105.0),
            CrossSectionPoint(0.0, 105.0),
            CrossSectionPoint(5.0, 105.0),
        ],
    )
    template = DesignTemplate(
        points=[
            CrossSectionPoint(-5.0, -5.0),
            CrossSectionPoint(0.0, 0.0),
            CrossSectionPoint(5.0, -5.0),
        ]
    )
    cut, fill = section_area(ground, template, design_cl_elevation=100.0)
    assert math.isclose(cut, 75.0, abs_tol=1e-6)
    assert math.isclose(fill, 0.0, abs_tol=1e-6)


# ---------------------------------------------------------------------------
# average_end_area tests
# ---------------------------------------------------------------------------


def test_average_end_area_identical_sections():
    """Two identical cut sections 100m apart.

    Area = 40 each. Volume = ((40 + 40) / 2) * 100 = 4000.
    """
    cut_vol, fill_vol = average_end_area(40.0, 0.0, 40.0, 0.0, 100.0)
    assert math.isclose(cut_vol, 4000.0, abs_tol=1e-6)
    assert math.isclose(fill_vol, 0.0, abs_tol=1e-6)


def test_average_end_area_different_sections():
    """Two different sections 50m apart.

    Cut areas 20 and 40 → cut volume = ((20 + 40) / 2) * 50 = 1500.
    Fill areas 10 and 30 → fill volume = ((10 + 30) / 2) * 50 = 1000.
    """
    cut_vol, fill_vol = average_end_area(20.0, 10.0, 40.0, 30.0, 50.0)
    assert math.isclose(cut_vol, 1500.0, abs_tol=1e-6)
    assert math.isclose(fill_vol, 1000.0, abs_tol=1e-6)


def test_average_end_area_fill_only():
    """Two fill sections."""
    cut_vol, fill_vol = average_end_area(0.0, 25.0, 0.0, 35.0, 80.0)
    assert math.isclose(cut_vol, 0.0, abs_tol=1e-6)
    assert math.isclose(fill_vol, 2400.0, abs_tol=1e-6)


# ---------------------------------------------------------------------------
# prismoidal_volume tests
# ---------------------------------------------------------------------------


def test_prismoidal_volume_uniform():
    """Uniform cut area = 30 throughout, distance = 60.

    V = (60/6) * (30 + 4*30 + 30) = 10 * 180 = 1800.
    """
    cut_vol, fill_vol = prismoidal_volume(30.0, 0.0, 30.0, 0.0, 30.0, 0.0, 60.0)
    assert math.isclose(cut_vol, 1800.0, abs_tol=1e-6)
    assert math.isclose(fill_vol, 0.0, abs_tol=1e-6)


def test_prismoidal_volume_varying():
    """Varying areas: ends 10 and 40, mid 25, distance 120.

    V = (120/6) * (10 + 4*25 + 40) = 20 * 150 = 3000.
    """
    cut_vol, fill_vol = prismoidal_volume(10.0, 5.0, 25.0, 10.0, 40.0, 15.0, 120.0)
    assert math.isclose(cut_vol, 3000.0, abs_tol=1e-6)
    # Fill: (120/6) * (5 + 4*10 + 15) = 20 * 60 = 1200
    assert math.isclose(fill_vol, 1200.0, abs_tol=1e-6)


# ---------------------------------------------------------------------------
# compute_earthwork tests
# ---------------------------------------------------------------------------


def test_earthwork_three_sections():
    """Three sections in pure cut, 100m apart.

    Section 0 (sta 0): ground at 105, design at 100 → cut area = 100 (width 20, h 5)
    Section 1 (sta 100): ground at 104, design at 100 → cut area = 80 (width 20, h 4)
    Section 2 (sta 200): ground at 103, design at 100 → cut area = 60 (width 20, h 3)
    """
    sections = [
        CrossSection(
            station=0.0,
            points=[
                CrossSectionPoint(-10.0, 105.0),
                CrossSectionPoint(0.0, 105.0),
                CrossSectionPoint(10.0, 105.0),
            ],
        ),
        CrossSection(
            station=100.0,
            points=[
                CrossSectionPoint(-10.0, 104.0),
                CrossSectionPoint(0.0, 104.0),
                CrossSectionPoint(10.0, 104.0),
            ],
        ),
        CrossSection(
            station=200.0,
            points=[
                CrossSectionPoint(-10.0, 103.0),
                CrossSectionPoint(0.0, 103.0),
                CrossSectionPoint(10.0, 103.0),
            ],
        ),
    ]
    template = DesignTemplate(
        points=[
            CrossSectionPoint(-10.0, 0.0),
            CrossSectionPoint(0.0, 0.0),
            CrossSectionPoint(10.0, 0.0),
        ]
    )
    design_elevs = [100.0, 100.0, 100.0]

    results = compute_earthwork(sections, template, design_elevs)

    assert len(results) == 2

    # Segment 0→100: cut_vol = ((100 + 80) / 2) * 100 = 9000
    assert math.isclose(results[0]["cut_volume"], 9000.0, abs_tol=1e-3)
    assert math.isclose(results[0]["fill_volume"], 0.0, abs_tol=1e-3)
    assert results[0]["station_from"] == 0.0
    assert results[0]["station_to"] == 100.0

    # Segment 100→200: cut_vol = ((80 + 60) / 2) * 100 = 7000
    assert math.isclose(results[1]["cut_volume"], 7000.0, abs_tol=1e-3)
    assert math.isclose(results[1]["fill_volume"], 0.0, abs_tol=1e-3)

    # Cumulative
    assert math.isclose(results[1]["cumulative_cut"], 16000.0, abs_tol=1e-3)
    assert math.isclose(results[1]["cumulative_fill"], 0.0, abs_tol=1e-3)


def test_earthwork_cut_to_fill_transition():
    """Sections transition from cut to fill.

    Section 0 (sta 0): ground 105, design 100 → cut only (area=100, w=20, h=5)
    Section 1 (sta 100): ground 100, design 100 → zero area
    Section 2 (sta 200): ground 97, design 100 → fill only (area=60, w=20, h=3)
    """
    sections = [
        CrossSection(
            station=0.0,
            points=[
                CrossSectionPoint(-10.0, 105.0),
                CrossSectionPoint(10.0, 105.0),
            ],
        ),
        CrossSection(
            station=100.0,
            points=[
                CrossSectionPoint(-10.0, 100.0),
                CrossSectionPoint(10.0, 100.0),
            ],
        ),
        CrossSection(
            station=200.0,
            points=[
                CrossSectionPoint(-10.0, 97.0),
                CrossSectionPoint(10.0, 97.0),
            ],
        ),
    ]
    template = DesignTemplate(
        points=[
            CrossSectionPoint(-10.0, 0.0),
            CrossSectionPoint(10.0, 0.0),
        ]
    )
    design_elevs = [100.0, 100.0, 100.0]

    results = compute_earthwork(sections, template, design_elevs)
    assert len(results) == 2

    # Segment 0→100: cut = ((100+0)/2)*100 = 5000, fill = 0
    assert math.isclose(results[0]["cut_volume"], 5000.0, abs_tol=1e-3)
    assert math.isclose(results[0]["fill_volume"], 0.0, abs_tol=1e-3)

    # Segment 100→200: cut = 0, fill = ((0+60)/2)*100 = 3000
    assert math.isclose(results[1]["cut_volume"], 0.0, abs_tol=1e-3)
    assert math.isclose(results[1]["fill_volume"], 3000.0, abs_tol=1e-3)


# ---------------------------------------------------------------------------
# mass_haul tests
# ---------------------------------------------------------------------------


def test_mass_haul_ordinate_signs():
    """Mass haul: net cut makes ordinate positive, net fill makes it negative.

    Using the cut-to-fill transition earthwork from above.
    """
    sections = [
        CrossSection(
            station=0.0,
            points=[
                CrossSectionPoint(-10.0, 105.0),
                CrossSectionPoint(10.0, 105.0),
            ],
        ),
        CrossSection(
            station=100.0,
            points=[
                CrossSectionPoint(-10.0, 100.0),
                CrossSectionPoint(10.0, 100.0),
            ],
        ),
        CrossSection(
            station=200.0,
            points=[
                CrossSectionPoint(-10.0, 97.0),
                CrossSectionPoint(10.0, 97.0),
            ],
        ),
    ]
    template = DesignTemplate(
        points=[
            CrossSectionPoint(-10.0, 0.0),
            CrossSectionPoint(10.0, 0.0),
        ]
    )
    design_elevs = [100.0, 100.0, 100.0]

    earthwork_results = compute_earthwork(sections, template, design_elevs)
    mh = mass_haul(earthwork_results)

    assert len(mh) == 3
    # First station: ordinate = 0
    assert mh[0] == (0.0, 0.0)
    # After first segment (pure cut 5000): ordinate = +5000
    assert mh[1][0] == 100.0
    assert mh[1][1] > 0  # positive (net cut)
    assert math.isclose(mh[1][1], 5000.0, abs_tol=1e-3)
    # After second segment (pure fill 3000): ordinate = 5000 - 3000 = 2000
    assert mh[2][0] == 200.0
    assert math.isclose(mh[2][1], 2000.0, abs_tol=1e-3)


def test_mass_haul_empty():
    """Empty earthwork produces empty mass haul."""
    assert mass_haul([]) == []


def test_mass_haul_balanced():
    """When cut equals fill, mass haul returns to zero."""
    # Two segments: first all cut, second equal fill
    earthwork = [
        {
            "station_from": 0.0,
            "station_to": 100.0,
            "cut_volume": 5000.0,
            "fill_volume": 0.0,
            "cumulative_cut": 5000.0,
            "cumulative_fill": 0.0,
        },
        {
            "station_from": 100.0,
            "station_to": 200.0,
            "cut_volume": 0.0,
            "fill_volume": 5000.0,
            "cumulative_cut": 5000.0,
            "cumulative_fill": 5000.0,
        },
    ]
    mh = mass_haul(earthwork)
    assert len(mh) == 3
    assert math.isclose(mh[0][1], 0.0, abs_tol=1e-6)
    assert math.isclose(mh[1][1], 5000.0, abs_tol=1e-6)
    assert math.isclose(mh[2][1], 0.0, abs_tol=1e-6)


# ---------------------------------------------------------------------------
# sorted_points property
# ---------------------------------------------------------------------------


def test_sorted_points():
    """Points are returned sorted by offset."""
    cs = CrossSection(
        station=50.0,
        points=[
            CrossSectionPoint(5.0, 100.0),
            CrossSectionPoint(-5.0, 101.0),
            CrossSectionPoint(0.0, 100.5),
        ],
    )
    sp = cs.sorted_points
    offsets = [p.offset for p in sp]
    assert offsets == [-5.0, 0.0, 5.0]


# ---------------------------------------------------------------------------
# interpolate_surface tests
# ---------------------------------------------------------------------------


from cogokit.surveying.cross_sections import interpolate_surface


def _make_sections():
    """Build three flat sections for interpolation tests.

    Station 0: flat at elevation 100
    Station 100: flat at elevation 104
    Station 200: flat at elevation 108
    Each has offsets at -10, 0, +10 (flat profile per section).
    """
    return [
        CrossSection(
            station=0.0,
            points=[
                CrossSectionPoint(-10.0, 100.0),
                CrossSectionPoint(0.0, 100.0),
                CrossSectionPoint(10.0, 100.0),
            ],
        ),
        CrossSection(
            station=100.0,
            points=[
                CrossSectionPoint(-10.0, 104.0),
                CrossSectionPoint(0.0, 104.0),
                CrossSectionPoint(10.0, 104.0),
            ],
        ),
        CrossSection(
            station=200.0,
            points=[
                CrossSectionPoint(-10.0, 108.0),
                CrossSectionPoint(0.0, 108.0),
                CrossSectionPoint(10.0, 108.0),
            ],
        ),
    ]


def test_interpolate_surface_exact_point():
    """Query at an exact known station/offset returns measured value."""
    sections = _make_sections()
    elev = interpolate_surface(sections, station=100.0, offset=0.0)
    assert math.isclose(elev, 104.0, abs_tol=1e-9)


def test_interpolate_surface_midpoint_station():
    """Midpoint between two sections (flat profiles) → linear blend."""
    sections = _make_sections()
    # Midpoint between sta 0 (elev 100) and sta 100 (elev 104) → 102
    elev = interpolate_surface(sections, station=50.0, offset=0.0)
    assert math.isclose(elev, 102.0, abs_tol=1e-9)


def test_interpolate_surface_non_measured_offset():
    """Interpolation at a non-measured offset within a section."""
    # Section with sloping profile: -10→100, 0→102, 10→104
    sections = [
        CrossSection(
            station=0.0,
            points=[
                CrossSectionPoint(-10.0, 100.0),
                CrossSectionPoint(0.0, 102.0),
                CrossSectionPoint(10.0, 104.0),
            ],
        ),
        CrossSection(
            station=100.0,
            points=[
                CrossSectionPoint(-10.0, 100.0),
                CrossSectionPoint(0.0, 102.0),
                CrossSectionPoint(10.0, 104.0),
            ],
        ),
    ]
    # Offset 5 is between 0→102 and 10→104, so elev = 103
    elev = interpolate_surface(sections, station=0.0, offset=5.0)
    assert math.isclose(elev, 103.0, abs_tol=1e-9)


def test_interpolate_surface_bilinear():
    """Both station and offset interpolated (bilinear)."""
    # sta 0: flat at 100; sta 100: sloping -10→100, 0→104, 10→108
    sections = [
        CrossSection(
            station=0.0,
            points=[
                CrossSectionPoint(-10.0, 100.0),
                CrossSectionPoint(0.0, 100.0),
                CrossSectionPoint(10.0, 100.0),
            ],
        ),
        CrossSection(
            station=100.0,
            points=[
                CrossSectionPoint(-10.0, 100.0),
                CrossSectionPoint(0.0, 104.0),
                CrossSectionPoint(10.0, 108.0),
            ],
        ),
    ]
    # At sta 0, offset 5 → 100 (flat)
    # At sta 100, offset 5 → 106 (midway between 104 and 108)
    # At sta 50 (midpoint), blend → (100 + 106) / 2 = 103
    elev = interpolate_surface(sections, station=50.0, offset=5.0)
    assert math.isclose(elev, 103.0, abs_tol=1e-9)


def test_interpolate_surface_clamp_before_first():
    """Station before first section clamps to first section."""
    sections = _make_sections()
    # sta -50 should clamp to sta 0 → elev 100
    elev = interpolate_surface(sections, station=-50.0, offset=0.0)
    assert math.isclose(elev, 100.0, abs_tol=1e-9)


def test_interpolate_surface_clamp_after_last():
    """Station after last section clamps to last section."""
    sections = _make_sections()
    # sta 250 should clamp to sta 200 → elev 108
    elev = interpolate_surface(sections, station=250.0, offset=0.0)
    assert math.isclose(elev, 108.0, abs_tol=1e-9)


def test_interpolate_surface_two_sections():
    """Works with exactly two sections."""
    sections = [
        CrossSection(
            station=0.0,
            points=[
                CrossSectionPoint(-5.0, 100.0),
                CrossSectionPoint(5.0, 100.0),
            ],
        ),
        CrossSection(
            station=50.0,
            points=[
                CrossSectionPoint(-5.0, 110.0),
                CrossSectionPoint(5.0, 110.0),
            ],
        ),
    ]
    elev = interpolate_surface(sections, station=25.0, offset=0.0)
    assert math.isclose(elev, 105.0, abs_tol=1e-9)


def test_interpolate_surface_fewer_than_two_sections():
    """Raises ValueError if fewer than 2 sections provided."""
    with pytest.raises(ValueError):
        interpolate_surface([], station=0.0, offset=0.0)
    with pytest.raises(ValueError):
        interpolate_surface(
            [CrossSection(station=0.0, points=[CrossSectionPoint(0.0, 100.0)])],
            station=0.0,
            offset=0.0,
        )
