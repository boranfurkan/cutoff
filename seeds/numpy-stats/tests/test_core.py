import math

import numpy as np

from stats import core


def test_clean_marks_missing():
    out = core.clean([1, None, 3])
    assert out.dtype == np.float64
    assert math.isnan(out[1])


def test_summary():
    s = core.summary([2, None, 4, 5])
    assert s == {"count": 3, "mean": 11 / 3, "span": 3.0, "product": 40.0, "all_positive": True}


def test_cumulative_growth():
    assert np.allclose(core.cumulative_growth([0.1, 0.2]), [1.1, 1.32])


def test_area_under():
    assert core.area_under([0, 1, 2], dx=2.0) == 4.0


def test_known_sensors():
    assert core.known_sensors([1, 2, 9], [1, 2, 3]).tolist() == [True, True, False]


def test_stack_rows():
    assert core.stack_rows([1, 2], [3, 4]).shape == (2, 2)


def test_upper_bound():
    assert core.upper_bound() == float("inf")
