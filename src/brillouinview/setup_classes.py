from datetime import date
from dataclasses import dataclass
from pathlib import Path

@dataclass
class MachineParameters:
    scattering_angle: float = None
    scattering_angle_unc: float = None
    laser_wavelength: float = None
    laser_wavelength_unc: float = None
    spacing: float = None
    spacing_unc: float = None
    machine_name: str = None
    machine_location: str = None
    machine_notes: str = None

@dataclass
class DACParameters:
    dac_name: str = None
    dac_pressuremedium: str = None
    dac_date_load: date = None
    dac_owner: str = None
    dac_notes: str = None
    dac_samples: list = None
    dac_directory: Path = None

@dataclass
class CalibrationParameters:
    exp_machine_parameters: MachineParameters = None
    calibration_file_path: Path = Path()
    calibration_OD: int = None
    calibration_value: float = None
    calibration_value_unc: float = None
    calibration_factor: float = None
    calibration_factor_unc: float = None
    calibration_file_path: Path = Path()
    calibration_peak_number: int = None
    calibration_peak_function: str = "" # e.g., "Gaussian", "Lorentzian"
    calibration_peak_parameters: list = None  # e.g., [amplitude, center, width]
    machine_spacing: float = None
    machine_spacing_unc: float = None

@dataclass
class ExperimentParameters:
    exp_machine_parameters: MachineParameters = None
    exp_calibration_parameters: CalibrationParameters = None
    exp_name: str = None
    exp_temperature: float = None
    exp_temperature_unc: float = None
    exp_pressure: float = None
    exp_pressure_unc: float = None
    exp_date_start: date = None
    exp_date_end: date = None
    exp_operator: str = None
    exp_notes: str = None
    calibration_factor: float = None
    calibration_factor_unc: float = None

@dataclass
class SampleParameters:
    sample_name: str = None
    sample_structure: str = None
    sample_notes: str = None
    sample_experiments: list = None


@dataclass
class SpectrumParameters:
    spectrum_file_path: Path = Path()
    spectrum_date: date = None
    spectrum_experiment: ExperimentParameters = None
    spectrum_sample: SampleParameters = None
