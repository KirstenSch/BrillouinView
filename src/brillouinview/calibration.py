from dataclasses import dataclass
from pathlib import Path
import numpy as np

@dataclass
class ExperimentSetup:
    scattering_angle: float = 45.0
    scattering_angle_unc: float = 0.1
    laser_wavelength: float = 532.0
    laser_wavelength_unc: float = 0.5
    spacing: float = 5.0
    spacing_unc: float = 0.1
    calibration_factor: float = 468.75
    calibration_factor_unc: float = np.nan
    calibration_file_path: Path = Path()
    calibration_peak_number: int = np.nan
    calibration_peak_function: str = "" # e.g., "Gaussian", "Lorentzian"
