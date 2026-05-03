from pathlib import Path
from yaml import safe_load
import re
import pandas as pd
from typing import Tuple, Dict, Any

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