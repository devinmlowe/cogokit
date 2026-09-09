"""Tests for State Plane zone lookup."""


import pytest


class TestGetZone:
    """Test zone lookup by EPSG code."""

    def test_lookup_california_zone5(self):
        from cogokit.geodetic.state_plane import get_zone

        zone = get_zone(26945)
        assert zone.name == "NAD83 / California zone 5"
        assert zone.state == "CA"
        assert zone.proj_def.proj_type == "lcc"

    def test_lookup_new_york_east(self):
        from cogokit.geodetic.state_plane import get_zone

        zone = get_zone(32115)
        assert zone.state == "NY"
        assert zone.proj_def.proj_type == "tmerc"

    def test_lookup_alaska_zone1(self):
        from cogokit.geodetic.state_plane import get_zone

        zone = get_zone(26931)
        assert zone.state == "AK"
        assert zone.proj_def.proj_type == "omerc"

    def test_unknown_epsg_raises(self):
        from cogokit.geodetic.state_plane import get_zone

        with pytest.raises(ValueError, match="Unknown"):
            get_zone(99999)


class TestFindZone:
    """Test zone lookup by state + zone name."""

    def test_find_texas_central(self):
        from cogokit.geodetic.state_plane import find_zone

        zone = find_zone("TX", "Central")
        assert zone.proj_def.proj_type == "lcc"

    def test_find_case_insensitive(self):
        from cogokit.geodetic.state_plane import find_zone

        zone = find_zone("tx", "central")
        assert zone.state == "TX"

    def test_find_not_found_raises(self):
        from cogokit.geodetic.state_plane import find_zone

        with pytest.raises(ValueError, match="not found"):
            find_zone("ZZ", "Nonexistent")


class TestListZones:
    """Test zone listing."""

    def test_list_all(self):
        from cogokit.geodetic.state_plane import list_zones

        zones = list_zones()
        assert len(zones) >= 100  # should be ~122

    def test_list_by_state(self):
        from cogokit.geodetic.state_plane import list_zones

        zones = list_zones(state="CA")
        assert len(zones) == 6  # California has 6 zones

    def test_list_unknown_state(self):
        from cogokit.geodetic.state_plane import list_zones

        zones = list_zones(state="ZZ")
        assert len(zones) == 0


class TestAllZonesParse:
    """Validate that every zone in the database parses without error."""

    def test_all_entries_parse(self):
        from cogokit.geodetic.state_plane import list_zones

        zones = list_zones()
        for zone in zones:
            assert zone.proj_def is not None
            assert zone.proj_def.proj_type in ("tmerc", "lcc", "omerc")
