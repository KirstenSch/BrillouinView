from brillouinview.calibration import ExperimentSetup, ExperimentSetupPublic
from pathlib import Path
from yaml import safe_load
import re
import pandas as pd
from typing import Tuple, Dict, Any

def experiment_setup_calibration(file_path: Path) -> ExperimentSetup:
    scattering_angle = None
    scattering_angle_unc = None
    laser_wavelength = None
    laser_wavelength_unc = None
    spacing = None
    spacing_unc = None
    calibration_value = None
    calibration_value_unc = None

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
                calibration_value = sub_dict['calibration_factor']

            if 'calibration_factor_unc' in sub_dict:
                calibration_value_unc = sub_dict['calibration_factor_unc']
        
        except ValueError as e:
            raise ValueError(f"Error reading calibration settings from {file_path}: {e} \n. Please enter values manually.") from e

    if file_path.suffix == '.txt':
        # read der older txt format
        try:
            scattering_angle = dict['para_theta']
            laser_wavelength = dict['para_lambda']
            spacing = dict['para_PS']
            if "average_BS_shift" in dict:
                calibration_value = dict['average_BS_shift']

        except ValueError as e:
            raise ValueError(f"Error reading calibration settings from {file_path}: {e} \n. Please enter values manually.") from e
            
    to_return = ExperimentSetupPublic(
        scattering_angle = scattering_angle,
        scattering_angle_unc = scattering_angle_unc,
        laser_wavelength = laser_wavelength,
        laser_wavelength_unc = laser_wavelength_unc,
        spacing = spacing,
        spacing_unc = spacing_unc,
        calibration_value = calibration_value,
        calibration_value_unc = calibration_value_unc
    )

    return to_return

def read_ghost_file(file_path: Path) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Read a legacy "Ghost Spectrum File".
    Returns (dataframe, header_dict).
    Header keys are taken from lines containing ':' (values converted to int/float when possible).
    The first non-':'-line (typically "Ghost Spectrum File") is stored as header['file_type'] if present.
    """
    file_path = Path(file_path)
    num_re = re.compile(r'^\s*[-+]?\d+\s*$')

    with open(file_path, 'r') as f:
        lines = [ln.rstrip('\n') for ln in f]

    # find first numeric data line
    first_num_idx = None
    for i, ln in enumerate(lines):
        if num_re.match(ln):
            first_num_idx = i
            break

    if first_num_idx is None:
        raise ValueError(f"No numeric data found in {file_path}")

    header_lines = lines[:first_num_idx]
    data_lines = [ln for ln in lines[first_num_idx:] if num_re.match(ln)]

    # parse data into dataframe
    data = [int(ln.strip()) for ln in data_lines]
    df = pd.DataFrame({'intensity': data})

    # parse header key:value pairs
    header: Dict[str, Any] = {}
    # capture a possible file-type/title line (first header line without ':')
    if header_lines:
        first_line = header_lines[0].strip()
        if first_line and ':' not in first_line:
            header['file_type'] = first_line

    for ln in header_lines:
        if ':' in ln:
            key, val = ln.split(':', 1)
            key = key.strip()
            val = val.strip()
            if val == '':
                header[key] = None
                continue
            # try to convert to int or float
            try:
                if re.match(r'^-?\d+$', val):
                    header[key] = int(val)
                elif re.match(r'^-?\d+\.\d*$', val):
                    header[key] = float(val)
                else:
                    header[key] = val
            except Exception:
                header[key] = val

    return df, header