import numpy as np

from dsp import tools


def test_energy():
    assert abs(tools.energy([1.0, 1.0, 1.0], 0.5) - 1.0) < 1e-9


def test_running_integral():
    assert np.allclose(tools.running_integral([1.0, 1.0, 1.0], 2.0), [0, 2, 4])


def test_area():
    assert tools.area([0.0, 2.0], 1.0) == 1.0


def test_window():
    w = tools.window(5, 1.0)
    assert len(w) == 5 and w[2] == 1.0


def test_slope():
    assert abs(tools.slope(lambda x: x * x, 3.0) - 6.0) < 1e-4


def test_smooth():
    assert len(tools.smooth(np.ones(9))) == 9
