from dataclasses import dataclass

@dataclass
class ExperimentSetup:
    scattering_angle: float = 45.0
    scattering_angle_unc: float = 0.1
    laser_wavelength: float = 532.0
    laser_wavelength_unc: float = 0.5
    spacing: float = 5.0
    spacing_unc: float = 0.1
    calibration_factor: float = 468.75
    calibration_factor_unc: float = 1.0

   