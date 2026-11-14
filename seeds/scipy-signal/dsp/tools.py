"""Signal processing helpers."""
import numpy as np
from scipy import integrate, signal
from scipy.misc import derivative


def energy(samples, dt):
    return float(integrate.simps(np.square(samples), dx=dt))


def running_integral(samples, dt):
    return integrate.cumtrapz(samples, dx=dt, initial=0)


def area(samples, dt):
    return float(integrate.trapz(samples, dx=dt))


def window(n, std):
    return signal.gaussian(n, std)


def slope(f, x):
    return float(derivative(f, x, dx=1e-6))


def smooth(samples, n=5):
    return signal.convolve(samples, signal.hann(n) / signal.hann(n).sum(), mode="same")
