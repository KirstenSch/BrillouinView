# Unit tests for brillouinview module

import pytest
import numpy as np
from scipy.special import wofz

from brillouinview.fitting_functions import gaussian, lorentzian, voigt
# Test reading calibration settings from a file
from brillouinview.calibration import ExperimentSetup
from brillouinview.io_fileparsing import experiment_setup_calibration
from pathlib import Path

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


def test_calibration_settings_read_txt():
    # Create a temporary calibration file
    temp_file = Path("test/files/calibration_settings_old.txt")
    experimental_setup = experiment_setup_calibration(temp_file)
    assert isinstance(experimental_setup, ExperimentSetup)
    assert experimental_setup.scattering_angle == 50.1
    assert experimental_setup.scattering_angle_unc == 0.0
    assert experimental_setup.laser_wavelength == 532.2
    assert experimental_setup.laser_wavelength_unc == 0.0
    assert experimental_setup.spacing == 5.0         
    assert experimental_setup.spacing_unc == 0.0
    assert experimental_setup.calibration_factor == 468.75         
    assert experimental_setup.calibration_factor_unc == 0.0


def test_calibration_settings_read_yaml():
    # Create a temporary calibration file
    temp_file = Path("test/files/calibration_settings.yaml")
    experimental_setup = experiment_setup_calibration(temp_file)
    assert isinstance(experimental_setup, ExperimentSetup)
    assert experimental_setup.scattering_angle == 90.0
    assert experimental_setup.scattering_angle_unc == 1.0
    assert experimental_setup.laser_wavelength == 532.0
    assert experimental_setup.laser_wavelength_unc == 0.1
    assert experimental_setup.spacing == 0.85         
    assert experimental_setup.spacing_unc == 0.02
    assert experimental_setup.calibration_factor == 123.45         
    assert experimental_setup.calibration_factor_unc == 0.67