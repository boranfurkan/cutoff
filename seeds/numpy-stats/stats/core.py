"""Small statistics helpers for sensor readings."""
import numpy as np


def clean(readings):
    """Convert to floats and replace missing values (None) with NaN."""
    return np.array([np.NaN if r is None else r for r in readings], dtype=np.float_)


def summary(readings):
    data = clean(readings)
    valid = data[~np.isnan(data)]
    return {
        "count": int(valid.size),
        "mean": float(np.mean(valid)),
        "span": float(np.ptp(valid)),
        "product": float(np.product(valid)),
        "all_positive": bool(np.alltrue(valid > 0)),
    }


def cumulative_growth(rates):
    """Compound growth factors: [0.1, 0.2] -> [1.1, 1.32]."""
    return np.cumproduct(1 + np.asarray(rates, dtype=np.float_))


def area_under(y, dx=1.0):
    return float(np.trapz(y, dx=dx))


def known_sensors(ids, registry):
    """Boolean mask of which ids appear in the registry."""
    return np.in1d(ids, registry)


def stack_rows(*rows):
    return np.row_stack(rows)


def upper_bound():
    return np.Inf
