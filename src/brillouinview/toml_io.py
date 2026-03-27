"""
toml_io.py
----------
Read/write functions for setup_classes dataclasses using tomlkit.

Supported classes:
  - MachineParameters        → machine_parameters.toml
  - CalibrationParameters    → calibration_parameters.toml
  - DACParameters            → dac_parameters.toml
      embeds: SampleParameters, ExperimentParameters as subtables/array-of-tables

Dependencies:
    pip install tomlkit
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

import tomlkit
from tomlkit import comment, document, nl, table, item
from tomlkit.items import Table

from brillouinview.setup_classes import (
    CalibrationParameters,
    DACParameters,
    ExperimentParameters,
    MachineParameters,
    SampleParameters,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _set(t: Table, key: str, value, inline_comment: str = "") -> None:
    """Add a key to a tomlkit table. None values are written as commented-out
    placeholders so the file remains self-documenting."""
    if value is None:
        t.add(comment(f" {key} = <not set>"))
    else:
        if isinstance(value, Path):
            value = str(value)
        # date: pass the plain Python date object — tomlkit serialises it natively
        t.add(key, value)
        if inline_comment:
            t[key].comment(inline_comment)


def _get(d: dict, key: str, type_=None, default=None):
    """Safely retrieve a value from a parsed TOML dict, with optional casting."""
    val = d.get(key, default)
    if val is None:
        return default
    if type_ is Path:
        return Path(val)
    if type_ is date and not isinstance(val, date):
        # tomlkit usually returns date objects directly; handle string fallback
        from datetime import date as dt
        return dt.fromisoformat(str(val))
    if type_ is float and val is not None:
        return float(val)
    if type_ is int and val is not None:
        return int(val)
    return val


# ---------------------------------------------------------------------------
# MachineParameters
# ---------------------------------------------------------------------------

def machine_to_toml(params: MachineParameters) -> tomlkit.TOMLDocument:
    doc = document()
    doc.add(comment("MachineParameters — instrument configuration"))
    doc.add(nl())

    t = table()
    _set(t, "machine_name",     params.machine_name)
    _set(t, "machine_location", params.machine_location)
    _set(t, "machine_notes",    params.machine_notes)
    t.add(nl())
    _set(t, "scattering_angle",     params.scattering_angle,     "degrees")
    _set(t, "scattering_angle_unc", params.scattering_angle_unc, "degrees, 1-sigma")
    _set(t, "laser_wavelength",     params.laser_wavelength,     "nm")
    _set(t, "laser_wavelength_unc", params.laser_wavelength_unc, "nm, 1-sigma")
    _set(t, "spacing",              params.spacing,              "mm")
    _set(t, "spacing_unc",          params.spacing_unc,          "mm, 1-sigma")

    doc.add("machine", t)
    return doc


def machine_from_toml(doc: tomlkit.TOMLDocument) -> MachineParameters:
    d = doc["machine"]
    return MachineParameters(
        machine_name      = _get(d, "machine_name"),
        machine_location  = _get(d, "machine_location"),
        machine_notes     = _get(d, "machine_notes"),
        scattering_angle     = _get(d, "scattering_angle",     float),
        scattering_angle_unc = _get(d, "scattering_angle_unc", float),
        laser_wavelength     = _get(d, "laser_wavelength",     float),
        laser_wavelength_unc = _get(d, "laser_wavelength_unc", float),
        spacing              = _get(d, "spacing",              float),
        spacing_unc          = _get(d, "spacing_unc",          float),
    )


def write_machine_toml(params: MachineParameters, path: Path) -> None:
    path = Path(path)
    path.write_text(tomlkit.dumps(machine_to_toml(params)), encoding="utf-8")


def read_machine_toml(path: Path) -> MachineParameters:
    doc = tomlkit.loads(Path(path).read_text(encoding="utf-8"))
    return machine_from_toml(doc)


# ---------------------------------------------------------------------------
# CalibrationParameters
# ---------------------------------------------------------------------------

def calibration_to_toml(params: CalibrationParameters) -> tomlkit.TOMLDocument:
    doc = document()
    doc.add(comment("CalibrationParameters — peak calibration result"))
    doc.add(nl())

    t = table()
    _set(t, "calibration_file_path",    params.calibration_file_path, "path to raw calibration file")
    t.add(nl())
    _set(t, "calibration_value",        params.calibration_value,     "calibrated value")
    _set(t, "calibration_value_unc",    params.calibration_value_unc, "1-sigma")
    _set(t, "calibration_factor",       params.calibration_factor)
    _set(t, "calibration_factor_unc",   params.calibration_factor_unc, "1-sigma")
    t.add(nl())
    _set(t, "calibration_peak_number",   params.calibration_peak_number)
    _set(t, "calibration_peak_function", params.calibration_peak_function,
         "e.g. Gaussian, Lorentzian")
    _set(t, "calibration_peak_parameters", params.calibration_peak_parameters,
         "[amplitude, center, width]")

    doc.add("calibration", t)
    return doc


def calibration_from_toml(doc: tomlkit.TOMLDocument) -> CalibrationParameters:
    d = doc["calibration"]
    return CalibrationParameters(
        calibration_value          = _get(d, "calibration_value",        float),
        calibration_value_unc      = _get(d, "calibration_value_unc",    float),
        calibration_factor         = _get(d, "calibration_factor",       float),
        calibration_factor_unc     = _get(d, "calibration_factor_unc",   float),
        calibration_file_path      = _get(d, "calibration_file_path",    Path, Path()),
        calibration_peak_number    = _get(d, "calibration_peak_number",  int),
        calibration_peak_function  = _get(d, "calibration_peak_function", default=""),
        calibration_peak_parameters= list(d["calibration_peak_parameters"])
                                     if d.get("calibration_peak_parameters") else None,
    )


def write_calibration_toml(params: CalibrationParameters, path: Path) -> None:
    path = Path(path)
    path.write_text(tomlkit.dumps(calibration_to_toml(params)), encoding="utf-8")


def read_calibration_toml(path: Path) -> CalibrationParameters:
    doc = tomlkit.loads(Path(path).read_text(encoding="utf-8"))
    return calibration_from_toml(doc)


# ---------------------------------------------------------------------------
# ExperimentParameters  (used as subtable inside DACParameters)
# ---------------------------------------------------------------------------

def _experiment_to_table(params: ExperimentParameters) -> Table:
    t = table()
    _set(t, "exp_name",        params.exp_name)
    _set(t, "exp_operator",    params.exp_operator)
    _set(t, "exp_notes",       params.exp_notes)
    _set(t, "exp_date_start",  params.exp_date_start)
    _set(t, "exp_date_end",    params.exp_date_end)
    t.add(nl())
    _set(t, "exp_temperature",     params.exp_temperature,     "K")
    _set(t, "exp_temperature_unc", params.exp_temperature_unc, "K, 1-sigma")
    _set(t, "exp_pressure",        params.exp_pressure,        "GPa")
    _set(t, "exp_pressure_unc",    params.exp_pressure_unc,    "GPa, 1-sigma")
    t.add(nl())
    _set(t, "calibration_factor",     params.calibration_factor)
    _set(t, "calibration_factor_unc", params.calibration_factor_unc, "1-sigma")

    # Nested MachineParameters as a sub-table
    if params.exp_machine_parameters is not None:
        mt = table()
        mp = params.exp_machine_parameters
        _set(mt, "machine_name",         mp.machine_name)
        _set(mt, "machine_location",     mp.machine_location)
        _set(mt, "machine_notes",        mp.machine_notes)
        _set(mt, "scattering_angle",     mp.scattering_angle,     "degrees")
        _set(mt, "scattering_angle_unc", mp.scattering_angle_unc, "degrees, 1-sigma")
        _set(mt, "laser_wavelength",     mp.laser_wavelength,     "nm")
        _set(mt, "laser_wavelength_unc", mp.laser_wavelength_unc, "nm, 1-sigma")
        _set(mt, "spacing",              mp.spacing,              "mm")
        _set(mt, "spacing_unc",          mp.spacing_unc,          "mm, 1-sigma")
        t.add("machine", mt)

    return t


def _experiment_from_dict(d: dict) -> ExperimentParameters:
    machine = None
    if "machine" in d:
        m = d["machine"]
        machine = MachineParameters(
            machine_name         = _get(m, "machine_name"),
            machine_location     = _get(m, "machine_location"),
            machine_notes        = _get(m, "machine_notes"),
            scattering_angle     = _get(m, "scattering_angle",     float),
            scattering_angle_unc = _get(m, "scattering_angle_unc", float),
            laser_wavelength     = _get(m, "laser_wavelength",     float),
            laser_wavelength_unc = _get(m, "laser_wavelength_unc", float),
            spacing              = _get(m, "spacing",              float),
            spacing_unc          = _get(m, "spacing_unc",          float),
        )
    return ExperimentParameters(
        exp_machine_parameters = machine,
        exp_name               = _get(d, "exp_name"),
        exp_operator           = _get(d, "exp_operator"),
        exp_notes              = _get(d, "exp_notes"),
        exp_date_start         = _get(d, "exp_date_start",         date),
        exp_date_end           = _get(d, "exp_date_end",           date),
        exp_temperature        = _get(d, "exp_temperature",        float),
        exp_temperature_unc    = _get(d, "exp_temperature_unc",    float),
        exp_pressure           = _get(d, "exp_pressure",           float),
        exp_pressure_unc       = _get(d, "exp_pressure_unc",       float),
        calibration_factor     = _get(d, "calibration_factor",     float),
        calibration_factor_unc = _get(d, "calibration_factor_unc", float),
    )


# ---------------------------------------------------------------------------
# SampleParameters  (used as subtable inside DACParameters)
# ---------------------------------------------------------------------------

def _sample_to_table(params: SampleParameters) -> Table:
    t = table()
    _set(t, "sample_name",      params.sample_name)
    _set(t, "sample_structure", params.sample_structure)
    _set(t, "sample_notes",     params.sample_notes)
    _set(t, "sample_files",
         [str(f) for f in params.sample_files] if params.sample_files else None)
    # sample_experiments are written as a nested array-of-tables
    if params.sample_experiments:
        exps = tomlkit.aot()
        for exp in params.sample_experiments:
            if isinstance(exp, ExperimentParameters):
                exps.append(_experiment_to_table(exp))
            else:
                # already a dict (e.g. re-serialising)
                exps.append(item(exp))
        t.add("experiments", exps)
    return t


def _sample_from_dict(d: dict) -> SampleParameters:
    exps = None
    if "experiments" in d:
        exps = [_experiment_from_dict(e) for e in d["experiments"]]
    files = None
    if d.get("sample_files"):
        files = [Path(f) for f in d["sample_files"]]
    return SampleParameters(
        sample_dac_parameters = None,   # back-filled by caller if needed
        sample_name           = _get(d, "sample_name"),
        sample_structure      = _get(d, "sample_structure"),
        sample_notes          = _get(d, "sample_notes"),
        sample_experiments    = exps,
        sample_files          = files,
    )


# ---------------------------------------------------------------------------
# DACParameters  (top-level, embeds samples + experiments)
# ---------------------------------------------------------------------------

def dac_to_toml(
    dac: DACParameters,
    samples: Optional[list[SampleParameters]] = None,
    experiments: Optional[list[ExperimentParameters]] = None,
) -> tomlkit.TOMLDocument:
    """
    Serialise DACParameters into a single TOML document.

    `samples` and `experiments` can be supplied separately or taken from
    dac.dac_samples / dac.dac_experiments if those lists contain dataclass
    instances.
    """
    doc = document()
    doc.add(comment("DACParameters — diamond anvil cell configuration"))
    doc.add(nl())

    t = table()
    _set(t, "dac_name",           dac.dac_name)
    _set(t, "dac_pressuremedium", dac.dac_pressuremedium)
    _set(t, "dac_date_load",      dac.dac_date_load)
    _set(t, "dac_owner",          dac.dac_owner)
    _set(t, "dac_notes",          dac.dac_notes)
    doc.add("dac", t)
    doc.add(nl())

    # Samples as array-of-tables  [[samples]]
    sample_list = samples or (
        [s for s in dac.dac_samples if isinstance(s, SampleParameters)]
        if dac.dac_samples else []
    )
    if sample_list:
        doc.add(comment(" Samples embedded in this DAC run"))
        aot_samples = tomlkit.aot()
        for s in sample_list:
            aot_samples.append(_sample_to_table(s))
        doc.add("samples", aot_samples)
        doc.add(nl())

    # Experiments as array-of-tables  [[experiments]]
    exp_list = experiments or (
        [e for e in dac.dac_experiments if isinstance(e, ExperimentParameters)]
        if dac.dac_experiments else []
    )
    if exp_list:
        doc.add(comment(" Experiments performed in this DAC run"))
        aot_exp = tomlkit.aot()
        for e in exp_list:
            aot_exp.append(_experiment_to_table(e))
        doc.add("experiments", aot_exp)

    return doc


def dac_from_toml(doc: tomlkit.TOMLDocument) -> tuple[DACParameters, list, list]:
    """
    Parse a TOML document into (DACParameters, [SampleParameters], [ExperimentParameters]).

    The lists are also stored inside dac.dac_samples and dac.dac_experiments.
    """
    d = doc["dac"]
    dac = DACParameters(
        dac_name           = _get(d, "dac_name"),
        dac_pressuremedium = _get(d, "dac_pressuremedium"),
        dac_date_load      = _get(d, "dac_date_load", date),
        dac_owner          = _get(d, "dac_owner"),
        dac_notes          = _get(d, "dac_notes"),
    )

    samples = []
    if "samples" in doc:
        for s in doc["samples"]:
            sp = _sample_from_dict(s)
            sp.sample_dac_parameters = dac
            samples.append(sp)

    experiments = []
    if "experiments" in doc:
        for e in doc["experiments"]:
            experiments.append(_experiment_from_dict(e))

    dac.dac_samples     = samples     or None
    dac.dac_experiments = experiments or None
    return dac, samples, experiments


def write_dac_toml(
    dac: DACParameters,
    path: Path,
    samples: Optional[list[SampleParameters]] = None,
    experiments: Optional[list[ExperimentParameters]] = None,
) -> None:
    path = Path(path)
    path.write_text(
        tomlkit.dumps(dac_to_toml(dac, samples, experiments)), encoding="utf-8"
    )


def read_dac_toml(path: Path) -> tuple[DACParameters, list, list]:
    doc = tomlkit.loads(Path(path).read_text(encoding="utf-8"))
    return dac_from_toml(doc)