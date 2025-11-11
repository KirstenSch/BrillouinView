# Unit tests for brillouinview module

import pytest
import numpy as np

from src.fitting_functions import gaussian


def test_gaussian():

    x = np.array([0, 1, 2])
    amp = 1
    mean = 1
    stddev = 1
    expected = amp * np.exp(-(x - mean)**2 / (2 * stddev**2))
    result = gaussian(x, amp, mean, stddev)
    np.testing.assert_array_almost_equal(result, expected)

