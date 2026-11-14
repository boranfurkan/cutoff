import numpy as np

from scoring import model


def test_fit_recovers_line():
    slope, intercept = model.fit([0, 1, 2], [1, 3, 5])
    assert np.allclose(slope, [2.0]) and np.allclose(intercept, [1.0])


def test_predict():
    assert np.allclose(model.predict([3], np.array([2.0]), np.array([1.0])), [7.0])
