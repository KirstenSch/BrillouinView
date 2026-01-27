from dataclasses import dataclass
from pathlib import Path
import numpy as np
from uncertainties import ufloat

@dataclass
class ExperimentSetup:
    scattering_angle: float = None
    scattering_angle_unc: float = None
    laser_wavelength: float = None
    laser_wavelength_unc: float = None
    spacing: float = None
    spacing_unc: float = None
    calibration_value: float = None
    calibration_value_unc: float = None
    calibration_factor: float = None
    calibration_factor_unc: float = None
    calibration_file_path: Path = Path()
    calibration_peak_number: int = None
    calibration_peak_function: str = "" # e.g., "Gaussian", "Lorentzian"
    calibration_peak_parameters: list = None  # e.g., [amplitude, center, width]

# Parameters for calibration that can be actively modified by the user or by loading from a file
@dataclass
class ExperimentSetupPublic:
    scattering_angle: float = None
    scattering_angle_unc: float = None
    laser_wavelength: float = None
    laser_wavelength_unc: float = None
    spacing: float = None
    spacing_unc: float = None
    calibration_value: float = None
    calibration_value_unc: float = None
    calibration_factor: float = None
    calibration_factor_unc: float = None


def calculate_channel_bshift_factor(exp_setup: ExperimentSetupPublic, OD: int = 1) -> ufloat:
    # Calculate the Factor to be multiplied with the Brillouin Shift in Channels to get the Shift as a Frequency
    # OD: Order of Diffraction
    # calibration_value: Calibration Value in Channels
    # spacing: Mirror Spacing in meters
    # Returns: calibration_factor in Hz/Channel
    
    calibration_value = ufloat(exp_setup.calibration_value, exp_setup.calibration_value_unc)
    spacing = ufloat(exp_setup.spacing, exp_setup.spacing_unc)
    
    speed_of_light = 299792458 # Speed of light in m/s
    calibration_factor = speed_of_light * OD / (2 * spacing * calibration_value)
    
    return calibration_factor
    
