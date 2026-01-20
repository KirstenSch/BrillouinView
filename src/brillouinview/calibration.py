from dataclasses import dataclass
from pathlib import Path
import numpy as np

@dataclass
class ExperimentSetup:
    scattering_angle: float = None
    scattering_angle_unc: float = None
    laser_wavelength: float = None
    laser_wavelength_unc: float = None
    spacing: float = None
    spacing_unc: float = None
    calibration_factor: float = None
    calibration_factor_unc: float = None
    calibration_file_path: Path = Path()
    calibration_peak_number: int = None
    calibration_peak_function: str = "" # e.g., "Gaussian", "Lorentzian"
    calibration_peak_parameters: list = None  # e.g., [amplitude, center, width]


@dataclass
class ExperimentSetupPublic:
    # Parameters for calibration that can be actively modified by the user or by loading from a file
    scattering_angle: float = None
    scattering_angle_unc: float = None
    laser_wavelength: float = None
    laser_wavelength_unc: float = None
    spacing: float = None
    spacing_unc: float = None
    calibration_factor: float = None
    calibration_factor_unc: float = None

