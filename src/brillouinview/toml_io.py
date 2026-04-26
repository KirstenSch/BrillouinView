"""
toml_io.py
----------
Read/write functions for setup_classes dataclasses using tomlkit.

File layouts
------------
machine_parameters.toml
    [machine]

calibration_parameters.toml
    [calibration]

dac_run.toml  — normalized, no duplication
    [dac]
    [[samples]]          each carries sample_experiments = ["run_001", ...]
    [machine]            defined once
    [[experiments]]      each carries exp_machine = "CARS-001"

    On read, string references are resolved to live object references:
      exp_machine  → MachineParameters object
      sample_experiments → list[ExperimentParameters] objects

All Path fields are stored and returned as absolute paths.

Dependencies
------------
    pip install tomlkit
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

import tomlkit
from tomlkit import comment, document, nl, table
from tomlkit.items import Table

try:
    from PyQt5 import QtWidgets
    HAS_QT = True
except ImportError:
    HAS_QT = False

from brillouinview.setup_classes import (
    CalibrationParameters,
    DACParameters,
    ExperimentParameters,
    MachineParameters,
    SampleParameters,
)


# ---------------------------------------------------------------------------
# File handling utilities
# ---------------------------------------------------------------------------

def handle_file_overwrite(file_path: Path, parent_widget=None) -> tuple[bool, Path]:
    """
    Notify user that file will be updated/created and proceed.
    
    If file exists, shows a notification that it will be overwritten.
    
    Parameters
    ----------
    file_path : Path
        The target file path
    parent_widget : QWidget, optional
        Parent widget for notification dialog (if using Qt)
    
    Returns
    -------
    tuple[bool, Path]
        (True, file_path) - always proceeds with write
    
    Examples
    --------
    >>> proceed, path = handle_file_overwrite(Path("data.toml"))
    >>> if proceed:
    ...     write_machine_toml(params, path)
    """
    file_path = Path(file_path)
    
    # If file exists, show notification
    if file_path.exists():
        if HAS_QT and parent_widget is not None:
            dialog = QtWidgets.QMessageBox(parent_widget)
            dialog.setWindowTitle("File Updated")
            dialog.setText(f"File updated:\n\n{file_path}")
            dialog.setIcon(QtWidgets.QMessageBox.Information)
            dialog.exec_()
        else:
            print(f"File updated: {file_path}")
    
    return True, file_path


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _set(t: Table, key: str, value, inline_comment: str = "") -> None:
    """Add a key to a tomlkit table.
    - None  → commented-out placeholder (keeps file self-documenting)
    - Path  → stored as absolute POSIX string
    - date  → passed as-is (tomlkit serialises Python date natively)
    """
    if value is None:
        t.add(comment(f" {key} = <not set>"))
        return
    if isinstance(value, Path):
        value = str(value.resolve())
    t.add(key, value)
    if inline_comment:
        t[key].comment(inline_comment)


def _get(d: dict, key: str, type_=None, default=None):
    """Retrieve and optionally cast a value from a parsed TOML dict."""
    val = d.get(key, default)
    if val is None:
        return default
    if type_ is Path:
        return Path(val).resolve()
    if type_ is date and not isinstance(val, date):
        return date.fromisoformat(str(val))
    if type_ is float:
        return float(val)
    if type_ is int:
        return int(val)
    return val


# ---------------------------------------------------------------------------
# MachineParameters — standalone file
# ---------------------------------------------------------------------------

def _machine_to_table(params: MachineParameters) -> Table:
    t = table()
    _set(t, "machine_name",         params.machine_name)
    _set(t, "machine_location",     params.machine_location)
    _set(t, "machine_notes",        params.machine_notes)
    t.add(nl())
    _set(t, "scattering_angle",     params.scattering_angle,     "degrees")
    _set(t, "scattering_angle_unc", params.scattering_angle_unc, "degrees, 1-sigma")
    _set(t, "laser_wavelength",     params.laser_wavelength,     "nm")
    _set(t, "laser_wavelength_unc", params.laser_wavelength_unc, "nm, 1-sigma")
    _set(t, "spacing",              params.spacing,              "mm")
    _set(t, "spacing_unc",          params.spacing_unc,          "mm, 1-sigma")
    return t


def _machine_from_dict(d: dict) -> MachineParameters:
    return MachineParameters(
        machine_name         = _get(d, "machine_name"),
        machine_location     = _get(d, "machine_location"),
        machine_notes        = _get(d, "machine_notes"),
        scattering_angle     = _get(d, "scattering_angle",     float),
        scattering_angle_unc = _get(d, "scattering_angle_unc", float),
        laser_wavelength     = _get(d, "laser_wavelength",     float),
        laser_wavelength_unc = _get(d, "laser_wavelength_unc", float),
        spacing              = _get(d, "spacing",              float),
        spacing_unc          = _get(d, "spacing_unc",          float),
    )


def machine_to_toml(params: MachineParameters) -> tomlkit.TOMLDocument:
    doc = document()
    doc.add(comment("MachineParameters — instrument configuration"))
    doc.add(nl())
    doc.add("machine", _machine_to_table(params))
    return doc


def machine_from_toml(doc: tomlkit.TOMLDocument) -> MachineParameters:
    return _machine_from_dict(doc["machine"])


def write_machine_toml(params: MachineParameters, path: Path, parent_widget=None) -> bool:
    """
    Write machine parameters to TOML file with overwrite protection.
    
    Parameters
    ----------
    params : MachineParameters
        Machine parameters to write
    path : Path
        Target file path
    parent_widget : QWidget, optional
        Parent widget for overwrite confirmation dialog
    
    Returns
    -------
    bool
        True if file was written successfully, False if cancelled or failed
    """
    proceed, final_path = handle_file_overwrite(Path(path), parent_widget)
    if proceed:
        Path(final_path).write_text(tomlkit.dumps(machine_to_toml(params)), encoding="utf-8")
        return True
    return False


def read_machine_toml(path: Path) -> MachineParameters:
    return machine_from_toml(tomlkit.loads(Path(path).read_text(encoding="utf-8")))


# ---------------------------------------------------------------------------
# CalibrationParameters — standalone file
# ---------------------------------------------------------------------------

def calibration_to_toml(params: CalibrationParameters) -> tomlkit.TOMLDocument:
    doc = document()
    doc.add(comment("CalibrationParameters — peak calibration result"))
    doc.add(nl())

    t = table()
    _set(t, "calibration_file_path",       params.calibration_file_path,
         "absolute path to raw calibration file")
    t.add(nl())
    _set(t, "calibration_value",           params.calibration_value,      "calibrated value")
    _set(t, "calibration_value_unc",       params.calibration_value_unc,  "1-sigma")
    _set(t, "calibration_factor",          params.calibration_factor)
    _set(t, "calibration_factor_unc",      params.calibration_factor_unc, "1-sigma")
    t.add(nl())
    _set(t, "calibration_peak_number",     params.calibration_peak_number)
    _set(t, "calibration_peak_function",   params.calibration_peak_function,
         "e.g. Gaussian, Lorentzian")
    _set(t, "calibration_peak_parameters", params.calibration_peak_parameters,
         "[amplitude, center, width]")

    doc.add("calibration", t)
    return doc


def calibration_from_toml(doc: tomlkit.TOMLDocument) -> CalibrationParameters:
    d = doc["calibration"]
    return CalibrationParameters(
        calibration_value           = _get(d, "calibration_value",          float),
        calibration_value_unc       = _get(d, "calibration_value_unc",      float),
        calibration_factor          = _get(d, "calibration_factor",         float),
        calibration_factor_unc      = _get(d, "calibration_factor_unc",     float),
        calibration_file_path       = _get(d, "calibration_file_path",      Path, Path().resolve()),
        calibration_peak_number     = _get(d, "calibration_peak_number",    int),
        calibration_peak_function   = _get(d, "calibration_peak_function",  default=""),
        calibration_peak_parameters = list(d["calibration_peak_parameters"])
                                      if d.get("calibration_peak_parameters") else None,
    )


def write_calibration_toml(params: CalibrationParameters, path: Path, parent_widget=None) -> bool:
    """
    Write calibration parameters to TOML file with overwrite protection.
    
    Parameters
    ----------
    params : CalibrationParameters
        Calibration parameters to write
    path : Path
        Target file path
    parent_widget : QWidget, optional
        Parent widget for overwrite confirmation dialog
    
    Returns
    -------
    bool
        True if file was written successfully, False if cancelled or failed
    """
    proceed, final_path = handle_file_overwrite(Path(path), parent_widget)
    if proceed:
        Path(final_path).write_text(tomlkit.dumps(calibration_to_toml(params)), encoding="utf-8")
        return True
    return False


def read_calibration_toml(path: Path) -> CalibrationParameters:
    return calibration_from_toml(tomlkit.loads(Path(path).read_text(encoding="utf-8")))


# ---------------------------------------------------------------------------
# DAC run file — normalized layout
#
# Structure written:
#   [dac]
#   [[samples]]        sample_experiments = ["run_001", "run_002", ...]
#   [machine]
#   [[experiments]]    exp_machine = "CARS-001"
#
# On read, string references are resolved:
#   exp_machine        → MachineParameters object (from [machine])
#   sample_experiments → list[ExperimentParameters] (looked up by exp_name)
# ---------------------------------------------------------------------------

def _experiment_to_table(exp: ExperimentParameters) -> Table:
    """Serialize one experiment. Machine is stored as a name reference only."""
    t = table()
    _set(t, "exp_name",     exp.exp_name)
    _set(t, "exp_machine",  exp.exp_machine_parameters.machine_name
                            if exp.exp_machine_parameters else None,
         "→ machine.machine_name")
    _set(t, "exp_operator", exp.exp_operator)
    _set(t, "exp_notes",    exp.exp_notes)
    _set(t, "exp_date_start",  exp.exp_date_start)
    _set(t, "exp_date_end",    exp.exp_date_end)
    t.add(nl())
    _set(t, "exp_temperature",     exp.exp_temperature,     "K")
    _set(t, "exp_temperature_unc", exp.exp_temperature_unc, "K, 1-sigma")
    _set(t, "exp_pressure",        exp.exp_pressure,        "GPa")
    _set(t, "exp_pressure_unc",    exp.exp_pressure_unc,    "GPa, 1-sigma")
    t.add(nl())
    _set(t, "calibration_factor",     exp.calibration_factor)
    _set(t, "calibration_factor_unc", exp.calibration_factor_unc, "1-sigma")
    return t


def _sample_to_table(sample: SampleParameters) -> Table:
    """Serialize one sample. Experiments stored as list of name strings."""
    t = table()
    _set(t, "sample_name",      sample.sample_name)
    _set(t, "sample_structure", sample.sample_structure)
    _set(t, "sample_notes",     sample.sample_notes)

    # Experiment references — names only, no duplication
    if sample.sample_experiments:
        names = []
        for e in sample.sample_experiments:
            if isinstance(e, ExperimentParameters):
                names.append(e.exp_name)
            else:
                names.append(str(e))   # already a name string
        _set(t, "sample_experiments", names, "→ experiments[*].exp_name")
    else:
        t.add(comment(" sample_experiments = <not set>"))

    return t


def dac_to_toml(
    dac: DACParameters,
    machine: Optional[list[MachineParameters]] = None,
    samples: Optional[list[SampleParameters]] = None,
    experiments: Optional[list[ExperimentParameters]] = None,
) -> tomlkit.TOMLDocument:
    """
    Serialise a full DAC run into a normalized TOML document.

    Layout: [dac] → [[samples]] → [machine] → [[experiments]]

    Parameters
    ----------
    dac:         DACParameters
    machine:     MachineParameters  (written once, referenced by name)
    samples:     list of SampleParameters  (experiment refs stored as names)
    experiments: list of ExperimentParameters  (machine ref stored as name)
    """
    doc = document()
    doc.add(comment("DAC run file — normalized layout"))
    doc.add(comment("Machine and experiments are defined once and referenced by name."))
    doc.add(nl())

    # [dac]
    t = table()
    _set(t, "dac_name",           dac.dac_name)
    _set(t, "dac_pressuremedium", dac.dac_pressuremedium)
    _set(t, "dac_date_load",      dac.dac_date_load)
    _set(t, "dac_owner",          dac.dac_owner)
    _set(t, "dac_notes",          dac.dac_notes)
    
    # Sample references — names only, no duplication
    if dac.dac_samples:
        names = []
        for s in dac.dac_samples:
            if isinstance(s, SampleParameters):
                names.append(s.sample_name)
            else:
                names.append(str(s))   # already a name string
        _set(t, "dac_samples", names, "→ samples[*].sample_name")
    else:
        t.add(comment(" dac_samples = <not set>"))
    
    doc.add("dac", t)
    doc.add(nl())

    # [[samples]]
    sample_list = samples or []
    if sample_list:
        doc.add(comment(" Samples — experiment membership stored as name references"))
        aot = tomlkit.aot()
        for s in sample_list:
            aot.append(_sample_to_table(s))
        doc.add("samples", aot)
        doc.add(nl())

    # [machine]
    machine_list = machine or []
    if machine_list:
        doc.add(comment(" Machine — defined once, referenced by exp_machine in each experiment"))
        aot = tomlkit.aot()
        for m in machine_list:  # though we expect only one machine, we allow a list for future extensibility
            aot.append(_machine_to_table(m))
        doc.add("machine", aot)
        doc.add(nl())

    # [[experiments]]
    exp_list = experiments or []
    if exp_list:
        doc.add(comment(" Experiments — machine stored as name reference only"))
        aot = tomlkit.aot()
        for e in exp_list:
            aot.append(_experiment_to_table(e))
        doc.add("experiments", aot)

    return doc


def dac_from_toml(
    doc: tomlkit.TOMLDocument,
) -> tuple[DACParameters, list[MachineParameters], list[SampleParameters], list[ExperimentParameters]]:
    """
    Parse a normalized DAC TOML document.

    Returns
    -------
    (DACParameters, MachineParameters, [SampleParameters], [ExperimentParameters])

    References are resolved:
      - Each ExperimentParameters gets the live MachineParameters object.
      - Each SampleParameters gets a list of live ExperimentParameters objects
        (matched by exp_name) and the live DACParameters object.
    """
    # DAC
    d = doc["dac"]
    dac = DACParameters(
        dac_name           = _get(d, "dac_name"),
        dac_pressuremedium = _get(d, "dac_pressuremedium"),
        dac_date_load      = _get(d, "dac_date_load", date),
        dac_owner          = _get(d, "dac_owner"),
        dac_notes          = _get(d, "dac_notes"),
    )

    # Machine
    machines: list[MachineParameters] = []
    for m in doc.get("machine", []):
        machine = _machine_from_dict(m)
        machines.append(machine)

    # Build lookup for machine → resolution by machine_name
    machine_by_name: dict[str, MachineParameters] = {
        m.machine_name: m for m in machines if m.machine_name
    }

    # Experiments — resolve exp_machine name → object
    experiments: list[ExperimentParameters] = []
    for e in doc.get("experiments", []):
        exp_machine_name = _get(e, "exp_machine")
        resolved_machine = machine_by_name.get(exp_machine_name) if exp_machine_name else None
        exp = ExperimentParameters(
            exp_machine_parameters = resolved_machine,
            exp_name               = _get(e, "exp_name"),
            exp_operator           = _get(e, "exp_operator"),
            exp_notes              = _get(e, "exp_notes"),
            exp_date_start         = _get(e, "exp_date_start",         date),
            exp_date_end           = _get(e, "exp_date_end",           date),
            exp_temperature        = _get(e, "exp_temperature",        float),
            exp_temperature_unc    = _get(e, "exp_temperature_unc",    float),
            exp_pressure           = _get(e, "exp_pressure",           float),
            exp_pressure_unc       = _get(e, "exp_pressure_unc",       float),
            calibration_factor     = _get(e, "calibration_factor",     float),
            calibration_factor_unc = _get(e, "calibration_factor_unc", float),
        )
        experiments.append(exp)

    # Build lookup for sample → experiment resolution
    exp_by_name: dict[str, ExperimentParameters] = {
        e.exp_name: e for e in experiments if e.exp_name
    }

    # Samples — resolve sample_experiments name list → objects
    samples: list[SampleParameters] = []
    for s in doc.get("samples", []):
        exp_names = list(s.get("sample_experiments") or [])
        resolved_exps = [exp_by_name[n] for n in exp_names if n in exp_by_name]
        sample = SampleParameters(
            sample_dac_parameters = dac,        # back-linked to parent DAC
            sample_name           = _get(s, "sample_name"),
            sample_structure      = _get(s, "sample_structure"),
            sample_notes          = _get(s, "sample_notes"),
            sample_experiments    = resolved_exps or None,
        )
        samples.append(sample)

    # Build lookup for dac → sample resolution
    sample_by_name: dict[str, SampleParameters] = {
        s.sample_name: s for s in samples if s.sample_name
    }

    # Resolve dac_samples name list → objects
    dac_sample_names = list(d.get("dac_samples") or [])
    resolved_samples = [sample_by_name[n] for n in dac_sample_names if n in sample_by_name]
    dac.dac_samples     = resolved_samples or None
    dac.dac_experiments = experiments or None

    return dac, machines, samples, experiments


def write_dac_toml(
    dac: DACParameters,
    path: Path,
    machine: Optional[list[MachineParameters]] = None,
    samples: Optional[list[SampleParameters]] = None,
    experiments: Optional[list[ExperimentParameters]] = None,
    parent_widget=None,
) -> bool:
    """
    Write DAC parameters to TOML file with overwrite protection.
    
    Parameters
    ----------
    dac : DACParameters
        DAC parameters to write
    path : Path
        Target file path
    machine : list[MachineParameters], optional
        Machine parameters list
    samples : list[SampleParameters], optional
        Sample parameters list
    experiments : list[ExperimentParameters], optional
        Experiment parameters list
    parent_widget : QWidget, optional
        Parent widget for overwrite confirmation dialog
    
    Returns
    -------
    bool
        True if file was written successfully, False if cancelled or failed
    """
    proceed, final_path = handle_file_overwrite(Path(path), parent_widget)
    if proceed:
        Path(final_path).write_text(
            tomlkit.dumps(dac_to_toml(dac, machine, samples, experiments)),
            encoding="utf-8",
        )
        return True
    return False


def read_dac_toml(
    path: Path,
) -> tuple[DACParameters, list[MachineParameters], list[SampleParameters], list[ExperimentParameters]]:
    return dac_from_toml(tomlkit.loads(Path(path).read_text(encoding="utf-8")))


# ---------------------------------------------------------------------------
# DAC run file — update with new parameters
# ---------------------------------------------------------------------------

def _handle_machine_changes(
    existing_machines: list[MachineParameters],
    new_machines: list[MachineParameters],
) -> None:
    """
    Handle changes to existing machines.
    
    Placeholder for future implementation to detect and process
    modifications to existing machine parameters.
    
    TODO: Implement in next task
    """
    pass


def _get_dac_name(dac_params: Optional[DACParameters]) -> Optional[str]:
    """Safely extract dac_name from DACParameters without triggering circular reference."""
    return dac_params.dac_name if dac_params else None


def _handle_sample_changes(
    existing_samples: list[SampleParameters],
    new_samples: list[SampleParameters],
) -> bool:
    """
    Handle changes to existing samples.
    
    For each new sample matching an existing sample by name:
    - If sample_experiments differ, combine the lists (avoiding duplicates by exp_name)
    - If other fields differ, abort the entire sample update procedure
    - If identical, pass silently
    
    Returns
    -------
    bool
        True if all checks passed, False if inconsistencies detected (abort procedure)
    """
    # Build lookup for existing samples by name
    existing_by_name: dict[str, SampleParameters] = {
        s.sample_name: s for s in existing_samples if s.sample_name
    }
    
    # Check each new sample against existing ones
    for new_sample in new_samples:
        if not new_sample.sample_name:
            continue
        
        existing_sample = existing_by_name.get(new_sample.sample_name)
        if not existing_sample:
            continue  # No existing sample with this name, already handled as new
        
        # Check if any non-experiment fields differ
        if (new_sample.sample_structure != existing_sample.sample_structure or
            new_sample.sample_notes != existing_sample.sample_notes or
            _get_dac_name(new_sample.sample_dac_parameters) != _get_dac_name(existing_sample.sample_dac_parameters)):
            
            print(f"✗ Sample '{new_sample.sample_name}': inconsistencies detected, aborting update:")
            if new_sample.sample_structure != existing_sample.sample_structure:
                print(f"  sample_structure: '{existing_sample.sample_structure}' → '{new_sample.sample_structure}'")
            if new_sample.sample_notes != existing_sample.sample_notes:
                print(f"  sample_notes: '{existing_sample.sample_notes}' → '{new_sample.sample_notes}'")
            if _get_dac_name(new_sample.sample_dac_parameters) != _get_dac_name(existing_sample.sample_dac_parameters):
                new_dac_name = _get_dac_name(new_sample.sample_dac_parameters)
                existing_dac_name = _get_dac_name(existing_sample.sample_dac_parameters)
                print(f"  sample_dac_parameters: '{existing_dac_name}' → '{new_dac_name}'")
            return False  # Abort entire sample update procedure
        
        # Handle sample_experiments - combine only if no inconsistencies found
        if new_sample.sample_experiments or existing_sample.sample_experiments:
            existing_exps = existing_sample.sample_experiments or []
            new_exps = new_sample.sample_experiments or []
            
            # Combine lists, avoiding duplicates by experiment name
            existing_exp_names = {
                e.exp_name for e in existing_exps 
                if hasattr(e, 'exp_name') and e.exp_name
            }
            combined = list(existing_exps)
            for exp in new_exps:
                exp_name = exp.exp_name if hasattr(exp, 'exp_name') else None
                if exp_name and exp_name not in existing_exp_names:
                    combined.append(exp)
                elif not exp_name:
                    combined.append(exp)
            
            existing_sample.sample_experiments = combined if combined else None
            if new_exps:
                print(f"✓ Sample '{new_sample.sample_name}': merged experiments (now {len(combined)} total)")
    
    return True  # All checks passed


def _handle_experiment_changes(
    existing_experiments: list[ExperimentParameters],
    new_experiments: list[ExperimentParameters],
) -> None:
    """
    Handle changes to existing experiments.
    
    Placeholder for future implementation to detect and process
    modifications to existing experiment parameters.
    
    TODO: Implement in next task
    """
    pass


def update_dac_toml(
    path: Path,
    machine: Optional[list[MachineParameters]] = None,
    samples: Optional[list[SampleParameters]] = None,
    experiments: Optional[list[ExperimentParameters]] = None,
    parent_widget=None,
) -> bool:
    """
    Update a DAC TOML file by comparing input parameters with existing file.
    
    Behavior:
        - Appends new machines, samples, experiments (matched by name)
        - Detects changes to existing items for future handling
        - Overwrites file if changes were made
        - Informs user of updates via print statements (or Qt dialog if parent_widget provided)
    
    Parameters
    ----------
    path : Path
        Path to existing DAC TOML file
    machine : list[MachineParameters], optional
        New/updated machine parameters
    samples : list[SampleParameters], optional
        New/updated sample parameters
    experiments : list[ExperimentParameters], optional
        New/updated experiment parameters
    parent_widget : QWidget, optional
        Parent widget for notification dialogs (if using Qt)
    
    Returns
    -------
    bool
        True if file was updated successfully, False if no changes or error occurred
    
    Examples
    --------
    >>> path = Path("dac_run.toml")
    >>> new_machines = [MachineParameters(...)]
    >>> updated = update_dac_toml(path, machine=new_machines)
    >>> if updated:
    ...     print("DAC file updated successfully")
    """
    path = Path(path)
    
    # Validate file exists
    if not path.exists():
        print(f"File does not exist: {path}")
        return False
    
    # Read existing file
    try:
        existing_dac, existing_machines, existing_samples, existing_experiments = read_dac_toml(path)
    except Exception as e:
        print(f"Error reading TOML file: {e}")
        return False
    
    # Track if any changes were made
    changes_made = False
    
    # Update machines
    if machine:
        existing_machine_names = {m.machine_name for m in existing_machines if m.machine_name}
        new_machines_list = [
            m for m in machine 
            if m.machine_name and m.machine_name not in existing_machine_names
        ]
        if new_machines_list:
            existing_machines.extend(new_machines_list)
            changes_made = True
            print(f"✓ Added {len(new_machines_list)} new machine(s): {', '.join(m.machine_name for m in new_machines_list)}")
        
        # Check for changed machines
        _handle_machine_changes(existing_machines, machine)
    
    # Update samples
    if samples:
        existing_sample_names = {s.sample_name for s in existing_samples if s.sample_name}
        new_samples_list = [
            s for s in samples 
            if s.sample_name and s.sample_name not in existing_sample_names
        ]
        if new_samples_list:
            existing_samples.extend(new_samples_list)
            changes_made = True
            print(f"✓ Added {len(new_samples_list)} new sample(s): {', '.join(s.sample_name for s in new_samples_list)}")
        
        # Check for changed samples
        if not _handle_sample_changes(existing_samples, samples):
            print("✗ Sample update aborted due to inconsistencies")
            return False
    
    # Update experiments
    if experiments:
        existing_exp_names = {e.exp_name for e in existing_experiments if e.exp_name}
        new_experiments_list = [
            e for e in experiments 
            if e.exp_name and e.exp_name not in existing_exp_names
        ]
        if new_experiments_list:
            existing_experiments.extend(new_experiments_list)
            changes_made = True
            print(f"✓ Added {len(new_experiments_list)} new experiment(s): {', '.join(e.exp_name for e in new_experiments_list)}")
        
        # Check for changed experiments
        _handle_experiment_changes(existing_experiments, experiments)
    
    # Write back if changes were made
    if changes_made:
        try:
            write_dac_toml(
                existing_dac,
                path,
                machine=existing_machines,
                samples=existing_samples,
                experiments=existing_experiments,
            )
            print(f"✓ File updated: {path}")
            return True
        except Exception as e:
            print(f"✗ Error writing TOML file: {e}")
            return False
    else:
        print("ℹ No changes detected")
        return False