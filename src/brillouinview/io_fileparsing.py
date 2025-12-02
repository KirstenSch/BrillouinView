from brillouinview.calibration import ExperimentSetup
from pathlib import Path
from yaml import safe_load

def experiment_setup_calibration(file_path: Path) -> ExperimentSetup:
    scattering_angle = 0.0
    laser_wavelength = 0.0
    spacing = 0.0
    calibration_factor = 0.0
    scattering_angle_unc = 0.0
    laser_wavelength_unc = 0.0
    spacing_unc = 0.0
    calibration_factor_unc = 0.0

    with open(file_path) as f:
        dict = safe_load(f)

    if file_path.suffix in ['.yaml', '.yml']:
        try:
            sub_dict = dict['experimental settings']['calibration_settings']
            scattering_angle = sub_dict['scattering_angle']
            scattering_angle_unc = sub_dict['scattering_angle_unc']
            laser_wavelength = sub_dict['wavelength']
            laser_wavelength_unc = sub_dict['wavelength_unc']
            spacing = sub_dict['spacing']
            spacing_unc = sub_dict['spacing_unc']        
            if 'calibration_factor' in sub_dict:
                calibration_factor = sub_dict['calibration_factor']

            if 'calibration_factor_unc' in sub_dict:
                calibration_factor_unc = sub_dict['calibration_factor_unc']
        
        except ValueError as e:
            raise ValueError(f"Error reading calibration settings from {file_path}: {e} \n. Please enter values manually.") from e

    if file_path.suffix == '.txt':
        # read der older txt format
        try:
            scattering_angle = dict['para_theta']
            laser_wavelength = dict['para_lambda']
            spacing = dict['para_PS']
            if "average_BS_shift" in dict:
                calibration_factor = dict['average_BS_shift']
            else:
                calibration_factor = 0.0

        except ValueError as e:
            raise ValueError(f"Error reading calibration settings from {file_path}: {e} \n. Please enter values manually.") from e
            
        
    return ExperimentSetup(
        scattering_angle = scattering_angle,
        scattering_angle_unc = scattering_angle_unc,
        laser_wavelength = laser_wavelength,
        laser_wavelength_unc = laser_wavelength_unc,
        spacing = spacing,
        spacing_unc = spacing_unc,
        calibration_factor = calibration_factor,
        calibration_factor_unc = calibration_factor_unc
    )