# Unit tests for brillouinview module

import pytest
import numpy as np
from scipy.special import wofz

from brillouinview.fitting_functions import gaussian, lorentzian, voigt


def test_gaussian():
    # Test the Gaussian fitting function
    # Function reference: 
    x = np.array([0, 1, 2])
    amp = 1
    mean = 1
    stddev = 1
    expected = amp * np.exp(-(x - mean)**2 / (2 * stddev**2))
    result = gaussian(x, amp, mean, stddev)
    np.testing.assert_array_almost_equal(result, expected)

def test_lorentzian():
    # Test the Lorentzian fitting function
    # Function reference: 
    x = np.array([0, 1, 2])
    amp = 1
    mean = 1
    gamma = 1
    expected = amp * (gamma**2) / ((x - mean)**2 + gamma**2)
    result = lorentzian(x, amp, mean, gamma)
    np.testing.assert_array_almost_equal(result, expected)

def test_voigt():
    # Test the Voigt fitting function
    # Function reference: 
    x = np.array([0, 1, 2])
    amp = 1
    mean = 1
    stddev = 1
    gamma = 1
    z = (x - mean + 1j * gamma) / (stddev * np.sqrt(2))
    denominator = stddev * np.sqrt(2 * np.pi)
    wofz_result = wofz(z)
    expected = amp * np.real(wofz_result / denominator)
    result = voigt(x, amp, mean, stddev, gamma)
    np.testing.assert_array_almost_equal(result, expected)


    