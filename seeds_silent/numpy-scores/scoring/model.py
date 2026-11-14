"""Tiny linear scoring model."""
import numpy as np


def fit(xs, ys):
    """Least-squares line through the points; returns (slope, intercept) arrays of shape (1,)."""
    a = np.vstack([xs, np.ones(len(xs))]).T
    coef, *_ = np.linalg.lstsq(a, np.asarray(ys, dtype=float), rcond=None)
    return coef[:1], coef[1:]


def predict(xs, slope, intercept):
    return np.asarray(xs) * slope + intercept


def describe(slope, intercept):
    """Human-readable summary of the fitted line."""
    return f"y = {float(slope):.2f}x + {float(intercept):.2f}"


def bucket(score, edges):
    """Index of the bucket a score falls into."""
    return int(np.searchsorted(edges, [score]))
