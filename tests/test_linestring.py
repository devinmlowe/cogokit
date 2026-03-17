"""Tests for LineString core type."""

import pytest

from cogopro.core.linestring import LineString


class TestLineString:
    """Test LineString construction and behavior."""

    def test_construction(self):
        ls = LineString(name="Boundary", point_numbers=(1, 2, 3, 4))
        assert ls.name == "Boundary"
        assert ls.point_numbers == (1, 2, 3, 4)
        assert ls.closed is False

    def test_closed(self):
        ls = LineString(name="Parcel", point_numbers=(1, 2, 3), closed=True)
        assert ls.closed is True

    def test_frozen(self):
        ls = LineString(name="Line", point_numbers=(1, 2))
        with pytest.raises(AttributeError):
            ls.name = "Other"

    def test_len(self):
        ls = LineString(name="L", point_numbers=(10, 20, 30))
        assert len(ls) == 3

    def test_contains(self):
        ls = LineString(name="L", point_numbers=(1, 5, 9))
        assert 5 in ls
        assert 7 not in ls

    def test_equality(self):
        a = LineString(name="A", point_numbers=(1, 2, 3))
        b = LineString(name="A", point_numbers=(1, 2, 3))
        assert a == b

    def test_inequality_different_order(self):
        a = LineString(name="A", point_numbers=(1, 2, 3))
        b = LineString(name="A", point_numbers=(3, 2, 1))
        assert a != b

    def test_empty(self):
        ls = LineString(name="Empty", point_numbers=())
        assert len(ls) == 0
