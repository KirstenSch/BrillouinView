# Unit tests for brillouinview module

import pytest
import numpy as np
from scipy.special import wofz
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from uncertainties import ufloat
from numpy.testing import assert_allclose

from brillouinview.fitting_algorithm import voigt, pseudo_voigt, gaussian, lorentzian
# Test reading calibration settings from a file
from brillouinview.gui.app import BrillouinViewApp
from brillouinview.setup_classes import ExperimentParameters
from brillouinview.io_fileparsing import read_ghost_file
from brillouinview.fitting_algorithm import fit_peaks, gaussian


from brillouinview.fitting_algorithm import fit_peaks

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

def test_voigt_reduces_to_gaussian_when_gamma_zero():
    x = np.linspace(-10, 10, 401)
    amplitude = 3.5
    center = 0.7
    sigma = 0.9
    gamma = 0.0

    v = voigt(x, amplitude, center, sigma, gamma)
    g = gaussian(x, amplitude, center, sigma)

    assert v.shape == x.shape
    assert_allclose(v, g, rtol=1e-7, atol=1e-9)


def test_voigt_reduces_to_lorentzian_when_sigma_zero():
    x = np.linspace(-10, 10, 401)
    amplitude = 2.2
    center = -1.5
    sigma = 0.0
    gamma = 0.8

    v = voigt(x, amplitude, center, sigma, gamma)
    l = lorentzian(x, amplitude, center, gamma)

    assert v.shape == x.shape
    assert_allclose(v, l, rtol=1e-7, atol=1e-9)


def test_voigt_center_value_equals_amplitude():
    # ensure center is exactly a sample point
    x = np.linspace(-5, 5, 501)
    amplitude = 4.0
    center = 1.0
    sigma = 0.6
    gamma = 0.4

    v = voigt(x, amplitude, center, sigma, gamma)
    # find index exactly at center
    idx = np.where(np.isclose(x, center))[0]
    assert idx.size == 1
    assert_allclose(v[idx[0]], amplitude, rtol=1e-8, atol=1e-10)


@pytest.mark.parametrize("eta,expected_func", [
    (0.0, gaussian),
    (1.0, lorentzian),
])
def test_pseudo_voigt_extremes_equal_components(eta, expected_func):
    x = np.linspace(-8, 8, 401)
    amplitude = 1.7
    center = -0.3
    sigma = 0.5
    gamma = 0.9

    pv = pseudo_voigt(x, amplitude, center, sigma, gamma, eta=eta)
    comp = expected_func(x, amplitude, center, sigma) if expected_func is gaussian else expected_func(x, amplitude, center, gamma)

    assert pv.shape == x.shape
    assert_allclose(pv, comp, rtol=1e-7, atol=1e-9)


def test_pseudo_voigt_without_eta_center_value_equals_amplitude():
    x = np.linspace(-6, 6, 601)
    amplitude = 2.5
    center = 0.0
    sigma = 0.4
    gamma = 0.6

    pv = pseudo_voigt(x, amplitude, center, sigma, gamma)  # eta estimated internally
    idx = np.where(np.isclose(x, center))[0]
    assert idx.size == 1
    assert_allclose(pv[idx[0]], amplitude, rtol=1e-8, atol=1e-10)
def test_calibration_settings_read_txt():
    # Create a temporary calibration file
    temp_file = Path("test/files/calibration_settings_old.txt")
    experimental_setup = experiment_setup_calibration(temp_file)
    assert isinstance(experimental_setup, ExperimentParameters)
    assert experimental_setup.scattering_angle == 50.1
    assert experimental_setup.scattering_angle_unc == None
    assert experimental_setup.laser_wavelength == 532.2
    assert experimental_setup.laser_wavelength_unc == None
    assert experimental_setup.spacing == 5.0         
    assert experimental_setup.spacing_unc == None
    assert experimental_setup.calibration_value == 468.75         
    assert experimental_setup.calibration_value_unc == None


def test_calibration_settings_read_yaml():
    # Create a temporary calibration file
    temp_file = Path("test/files/calibration_settings.yaml")
    experimental_setup = experiment_setup_calibration(temp_file)
    assert isinstance(experimental_setup, ExperimentParameters)
    assert experimental_setup.scattering_angle == 90.0
    assert experimental_setup.scattering_angle_unc == 1.0
    assert experimental_setup.laser_wavelength == 532.0
    assert experimental_setup.laser_wavelength_unc == 0.1
    assert experimental_setup.spacing == 0.85         
    assert experimental_setup.spacing_unc == 0.02
    assert experimental_setup.calibration_value == 123.45         
    assert experimental_setup.calibration_value_unc == 0.67


def test_read_ghost_file():
    # Read legacy Ghost Spectrum file and check header + data
    ghost_file = Path("test/files/calibration.DAT")
    df, header = read_ghost_file(ghost_file)

    # basic types
    assert hasattr(df, "shape")
    assert isinstance(header, dict)

    # header contents parsed correctly
    assert header.get("file_type") == "Ghost Spectrum File"
    assert header.get("Scan number") == 29
    assert header.get("Wavelength") == 532
    assert header.get("Sample") is None
    assert header.get("Mirror sp.") == 15
    assert abs(header.get("Ch. duration") - 0.029) < 1e-12

    # data contents
    assert "intensity" in df.columns
    assert int(df["intensity"].iloc[0]) == 23221
    assert int(df["intensity"].iloc[1]) == 27014
    assert len(df) > 100


def test_real_calibration_fit(tmp_path):
    # Test fitting on real calibration data
    ghost_file = Path("test/files/calibration.DAT")
    df, header = read_ghost_file(ghost_file)

    # Fit five peaks 
    results = fit_peaks(df, n_peaks=5, column="intensity")

    # Step 4: Create data from the combined fit_peaks output
    y_fitted = results['fitted_curve']
    fitted_params = sorted(results['params'], key=lambda p: p['center'])

    # Step 5: Plot both input and fit_peaks output
    fig1, (ax2, ax3) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Main comparison plot
    ax2.plot(list(df.index), list(df['intensity']), 'b-', linewidth=2, alpha=0.7, label='Input data')
    ax2.plot(results['x_values'], y_fitted, 'r--', linewidth=2, label='Fitted output')
    
    # Plot individual fitted dips
    baseline = results['baseline']
    x = results['x_values']
      # baseline is first param 
    for i, peak in enumerate(fitted_params, 1):
        individual_fit = baseline.nominal_value + gaussian(x, peak['amplitude'].nominal_value, peak['center'].nominal_value, peak['sigma'].nominal_value)
        ax2.plot(x, individual_fit, linestyle=':', linewidth=1.5, 
                label=f'Fitted dip {i} (center={peak["center"]:.2f})')

    ax2.axhline(y=baseline.nominal_value, color='gray', linestyle='--', alpha=0.3, label='Baseline')
    ax2.set_xlabel('X')
    ax2.set_ylabel('Intensity')
    ax2.set_title(f'Step 5: Input vs Fitted Output (R² = {results["r_squared"]:.4f})')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Residuals
    ax3.plot(results['x_values'], results['residuals'], 'g-', alpha=0.6, linewidth=1)
    ax3.axhline(y=0, color='k', linestyle='--', alpha=0.3)
    ax3.set_xlabel('X')
    ax3.set_ylabel('Residuals')
    ax3.set_title('Fitting Residuals')
    ax3.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(tmp_path / 'calibration_real_data_fit.png', dpi=150)
    plt.close()

    # Check that we found five peaks
    assert len(results["params"]) == 5

    # Check R² value
    assert results["r_squared"] > 0.95


def test_two_random_dips_workflow(tmp_path):
        """Complete workflow: generate random dips, fit, compare parameters."""
        np.random.seed(123)  # For reproducibility
        
        # Step 1: Generate two random Gaussian dips with negative amplitude
        x = np.linspace(0, 10, 500)
        baseline = 100  # Raised baseline
        
        # Random parameters for two dips
        amp1 = -np.random.uniform(20, 40)  # Negative amplitude (dip depth)
        center1 = np.random.uniform(2, 4)
        sigma1 = np.random.uniform(0.3, 0.6)
        
        amp2 = -np.random.uniform(25, 45)
        center2 = np.random.uniform(6, 8)
        sigma2 = np.random.uniform(0.4, 0.7)
        
        true_params = [
            (amp1, center1, sigma1),
            (amp2, center2, sigma2)
        ]
        
        # Create combined function with raised baseline
        y_input = baseline + gaussian(x, amp1, center1, sigma1) + gaussian(x, amp2, center2, sigma2)

        # Ensure all values are positive
        assert np.all(y_input > 0), "All values should be positive with raised baseline"
        
        # Step 2: Plot the input data
        fig1, ax1 = plt.subplots(figsize=(10, 6))
        ax1.plot(x, y_input, 'b-', linewidth=2, label='Input: Combined dips')
        ax1.axhline(y=baseline, color='gray', linestyle='--', alpha=0.5, label='Baseline')
        
        # Plot individual input dips
        ax1.plot(x, baseline + gaussian(x, amp1, center1, sigma1), 'g--', 
                alpha=0.6, label=f'Dip 1 (center={center1:.2f})')
        ax1.plot(x, baseline + gaussian(x, amp2, center2, sigma2), 'orange', 
                linestyle='--', alpha=0.6, label=f'Dip 2 (center={center2:.2f})')
        
        ax1.set_xlabel('X')
        ax1.set_ylabel('Intensity')
        ax1.set_title('Step 2: Input Data - Two Random Dips on Raised Baseline')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(tmp_path / 'step2_input_data.png', dpi=150)
        plt.close()
        
        # Step 3: Use combined data as input for fit_peaks
        df = pd.DataFrame({'intensities': y_input}, index=x)
        results = fit_peaks(df, n_peaks=2)
        
        # Step 4: Create data from the combined fit_peaks output
        y_fitted = results['fitted_curve']
        fitted_params = sorted(results['params'], key=lambda p: p['center'])
        
        # Step 5: Plot both input and fit_peaks output
        fig2, (ax2, ax3) = plt.subplots(2, 1, figsize=(12, 10))
        
        # Main comparison plot
        ax2.plot(x, y_input, 'b-', linewidth=2, alpha=0.7, label='Input data')
        ax2.plot(results['x_values'], y_fitted, 'r--', linewidth=2, label='Fitted output')
        
        # Plot individual fitted dips
        for i, peak in enumerate(fitted_params, 1):
            individual_fit = baseline + gaussian(x, peak['amplitude'].nominal_value, peak['center'].nominal_value, peak['sigma'].nominal_value)
            ax2.plot(x, individual_fit, linestyle=':', linewidth=1.5, 
                    label=f'Fitted dip {i} (center={peak["center"].nominal_value:.2f})')

        ax2.axhline(y=baseline, color='gray', linestyle='--', alpha=0.3, label='Baseline')
        ax2.set_xlabel('X')
        ax2.set_ylabel('Intensity')
        ax2.set_title(f'Step 5: Input vs Fitted Output (R² = {results["r_squared"]:.4f})')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Residuals
        ax3.plot(results['x_values'], results['residuals'], 'g-', alpha=0.6, linewidth=1)
        ax3.axhline(y=0, color='k', linestyle='--', alpha=0.3)
        ax3.set_xlabel('X')
        ax3.set_ylabel('Residuals')
        ax3.set_title('Fitting Residuals')
        ax3.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(tmp_path / 'step5_comparison.png', dpi=150)
        plt.close()
        
        # Step 6: Compare parameters - they should be close
        print("\n" + "="*60)
        print("Parameter Comparison:")
        print("="*60)
        
        # Sort true params by center for comparison
        true_params_sorted = sorted(true_params, key=lambda p: p[1])
        
        for i, (true, fitted) in enumerate(zip(true_params_sorted, fitted_params), 1):
            true_amp, true_center, true_sigma = true
            
            print(f"\nDip {i}:")
            print(f"  Center:    True={true_center:.3f}, Fitted={fitted['center']:.3f}, "
                  f"Error={abs(fitted['center'] - true_center):.3f}")
            print(f"  Amplitude: True={true_amp:.3f}, Fitted={fitted['amplitude']:.3f}, "
                  f"Error={abs(fitted['amplitude'] - true_amp):.3f}")
            print(f"  Sigma:     True={true_sigma:.3f}, Fitted={fitted['sigma']:.3f}, "
                  f"Error={abs(fitted['sigma'] - true_sigma):.3f}")
            
            # Assertions - parameters should be close
            assert abs(fitted['center'] - true_center) < 0.2, \
                f"Center mismatch for dip {i}: {fitted['center']:.3f} vs {true_center:.3f}"
            assert abs(fitted['amplitude'] - true_amp) < 5.0, \
                f"Amplitude mismatch for dip {i}: {fitted['amplitude']:.3f} vs {true_amp:.3f}"
            assert abs(fitted['sigma'] - true_sigma) < 0.2, \
                f"Sigma mismatch for dip {i}: {fitted['sigma']:.3f} vs {true_sigma:.3f}"
        
        # Overall fit quality
        assert results['r_squared'] > 0.99, \
            f"R² too low: {results['r_squared']:.4f}, should be > 0.99"
        
        print(f"\nR² = {results['r_squared']:.6f}")
        print("="*60)
        print("✓ All parameters match within tolerance!")

def test_calculation_calibration_factor():
    exp_setup_test = ExperimentParameters()
    exp_setup_test.calibration_value = 400.0
    exp_setup_test.calibration_value_unc = 4.0
    exp_setup_test.spacing = 300e-6
    exp_setup_test.spacing_unc = 3e-6
    OD = 1

    calibration_factor = BrillouinViewApp.calculate_channel_bshift_factor(exp_setup_test, OD)

    assert calibration_factor.nominal_value > 0
    assert calibration_factor.std_dev > 0
    
    expected_value_external = 1.249135241e9
    
    # Assert both nominal values are close to expected_value_external
    assert abs(calibration_factor.nominal_value - expected_value_external) / expected_value_external < 1e-6  # relative tolerance