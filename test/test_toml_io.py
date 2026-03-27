"""
test_toml_io.py
---------------
pytest suite for toml_io.py — exercises write/read round-trips for
MachineParameters, CalibrationParameters, and the DAC family
(DACParameters + SampleParameters + ExperimentParameters).

Run:
    pytest test_toml_io.py -v
"""

from datetime import date
from pathlib import Path

import pytest

from brillouinview.setup_classes import (
    CalibrationParameters,
    DACParameters,
    ExperimentParameters,
    MachineParameters,
    SampleParameters,
)
from brillouinview.toml_io import (
    read_calibration_toml,
    read_dac_toml,
    read_machine_toml,
    write_calibration_toml,
    write_dac_toml,
    write_machine_toml,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def machine() -> MachineParameters:
    return MachineParameters(
        machine_name         = "CARS-001",
        machine_location     = "Building A, Room 12",
        machine_notes        = "Recently re-aligned optics",
        scattering_angle     = 172.5,
        scattering_angle_unc = 0.3,
        laser_wavelength     = 532.0,
        laser_wavelength_unc = 0.1,
        spacing              = 15.2,
        spacing_unc          = 0.05,
    )


@pytest.fixture
def machine_minimal() -> MachineParameters:
    """All optional fields left as None."""
    return MachineParameters(machine_name="bare-minimum")


@pytest.fixture
def calibration() -> CalibrationParameters:
    return CalibrationParameters(
        calibration_value           = 694.35,
        calibration_value_unc       = 0.02,
        calibration_factor          = 1.0023,
        calibration_factor_unc      = 0.0001,
        calibration_file_path       = Path("data/ruby_cal_2024.spe"),
        calibration_peak_number     = 2,
        calibration_peak_function   = "Gaussian",
        calibration_peak_parameters = [1500.0, 694.35, 0.8],
    )


@pytest.fixture
def calibration_minimal() -> CalibrationParameters:
    """Only the defaults — tests None and empty-string handling."""
    return CalibrationParameters()


@pytest.fixture
def dac() -> DACParameters:
    return DACParameters(
        dac_name           = "BX90-7",
        dac_pressuremedium = "neon",
        dac_date_load      = date(2024, 11, 3),
        dac_owner          = "Jane Doe",
        dac_notes          = "Culet size 150 µm",
    )


@pytest.fixture
def experiment(machine) -> ExperimentParameters:
    return ExperimentParameters(
        exp_machine_parameters = machine,
        exp_name               = "run_001",
        exp_operator           = "Jane Doe",
        exp_notes              = "First compression point",
        exp_date_start         = date(2024, 11, 4),
        exp_date_end           = date(2024, 11, 4),
        exp_temperature        = 300.0,
        exp_temperature_unc    = 5.0,
        exp_pressure           = 12.3,
        exp_pressure_unc       = 0.2,
        calibration_factor     = 1.0023,
        calibration_factor_unc = 0.0001,
    )


@pytest.fixture
def sample(dac, experiment) -> SampleParameters:
    return SampleParameters(
        sample_dac_parameters = dac,
        sample_name           = "Fe2O3-001",
        sample_structure      = "hematite",
        sample_notes          = "5 µm flake, annealed",
        sample_experiments    = [experiment],
    )


# ---------------------------------------------------------------------------
# MachineParameters
# ---------------------------------------------------------------------------

class TestMachineParameters:

    def test_roundtrip_full(self, tmp_path, machine):
        p = tmp_path / "machine.toml"
        write_machine_toml(machine, p)
        assert read_machine_toml(p) == machine
        assert p.exists()

    def test_roundtrip_minimal(self, tmp_path, machine_minimal):
        p = tmp_path / "machine_min.toml"
        write_machine_toml(machine_minimal, p)
        assert read_machine_toml(p) == machine_minimal
        assert p.exists()

    def test_toml_is_valid_utf8_text(self, tmp_path, machine):
        p = tmp_path / "machine.toml"
        write_machine_toml(machine, p)
        content = p.read_text(encoding="utf-8")
        assert "[machine]" in content

    def test_floats_preserved(self, tmp_path, machine):
        p = tmp_path / "machine.toml"
        write_machine_toml(machine, p)
        back = read_machine_toml(p)
        assert type(back) == MachineParameters
        assert back.scattering_angle     == pytest.approx(machine.scattering_angle)
        assert back.scattering_angle_unc == pytest.approx(machine.scattering_angle_unc)
        assert back.laser_wavelength     == pytest.approx(machine.laser_wavelength)
        assert back.spacing              == pytest.approx(machine.spacing)


# ---------------------------------------------------------------------------
# CalibrationParameters
# ---------------------------------------------------------------------------

class TestCalibrationParameters:

    def test_roundtrip_full(self, tmp_path, calibration):
        p = tmp_path / "calibration.toml"
        write_calibration_toml(calibration, p)
        back = read_calibration_toml(p)
        # Exclude calibration_file_path from comparison: write/read stores an absolute path
        back.calibration_file_path = None
        calibration.calibration_file_path = None
        assert back == calibration

    def test_roundtrip_minimal(self, tmp_path, calibration_minimal):
        p = tmp_path / "calibration_min.toml"
        write_calibration_toml(calibration_minimal, p)
        back = read_calibration_toml(p)
        # Exclude calibration_file_path from comparison: write/read stores an absolute path
        back.calibration_file_path = None
        calibration_minimal.calibration_file_path = None
        assert back == calibration_minimal

    def test_peak_parameters_list_survives(self, tmp_path, calibration):
        p = tmp_path / "calibration.toml"
        write_calibration_toml(calibration, p)
        back = read_calibration_toml(p)
        assert back.calibration_peak_parameters == pytest.approx(
            calibration.calibration_peak_parameters
        )
        assert back.calibration_peak_function == "Gaussian"

    def test_empty_peak_function_default(self, tmp_path):
        cal = CalibrationParameters(calibration_peak_function="")
        p = tmp_path / "cal_empty_fn.toml"
        write_calibration_toml(cal, p)
        back = read_calibration_toml(p)
        assert back.calibration_peak_function == ""

    def test_floats_preserved(self, tmp_path, calibration):
        p = tmp_path / "calibration.toml"
        write_calibration_toml(calibration, p)
        back = read_calibration_toml(p)
        assert back.calibration_value      == pytest.approx(calibration.calibration_value)
        assert back.calibration_factor     == pytest.approx(calibration.calibration_factor)
        assert back.calibration_factor_unc == pytest.approx(calibration.calibration_factor_unc)


# ---------------------------------------------------------------------------
# DACParameters (with embedded SampleParameters + ExperimentParameters)
# ---------------------------------------------------------------------------

class TestDACParameters:

    def test_roundtrip_dac_fields(self, tmp_path, dac, sample, experiment):
        p = tmp_path / "dac.toml"
        write_dac_toml(dac=dac, path=p, samples=[sample], experiments=[experiment])
        dac_back, _, _, _ = read_dac_toml(p)
        assert dac_back.dac_name           == dac.dac_name
        assert dac_back.dac_pressuremedium == dac.dac_pressuremedium
        assert dac_back.dac_owner          == dac.dac_owner
        assert dac_back.dac_notes          == dac.dac_notes

    def test_dac_date_survives(self, tmp_path, dac, sample, experiment):
        p = tmp_path / "dac.toml"
        write_dac_toml(dac, p, samples=[sample], experiments=[experiment])
        dac_back, _, _, _ = read_dac_toml(p)
        assert dac_back.dac_date_load == dac.dac_date_load

    def test_sample_fields_survive(self, tmp_path, dac, sample, experiment):
        p = tmp_path / "dac.toml"
        write_dac_toml(dac, p, samples=[sample], experiments=[experiment])
        _, _, samples_back, _ = read_dac_toml(p)
        assert len(samples_back) == 1
        s = samples_back[0]
        assert s.sample_name      == sample.sample_name
        assert s.sample_structure == sample.sample_structure
        assert s.sample_notes     == sample.sample_notes

    def test_sample_backlink_to_dac(self, tmp_path, dac, sample, experiment):
        p = tmp_path / "dac.toml"
        write_dac_toml(dac, p, samples=[sample], experiments=[experiment])
        dac_back, _, samples_back, _ = read_dac_toml(p)
        assert samples_back[0].sample_dac_parameters is dac_back

    def test_experiment_fields_survive(self, tmp_path, dac, sample, experiment):
        p = tmp_path / "dac.toml"
        write_dac_toml(dac, p, samples=[sample], experiments=[experiment])
        _, _, _, exps_back = read_dac_toml(p)
        assert len(exps_back) == 1
        e = exps_back[0]
        assert e.exp_name     == experiment.exp_name
        assert e.exp_operator == experiment.exp_operator
        assert e.exp_notes    == experiment.exp_notes

    def test_experiment_dates_survive(self, tmp_path, dac, sample, experiment):
        p = tmp_path / "dac.toml"
        write_dac_toml(dac, p, samples=[sample], experiments=[experiment])
        _, _, _, exps_back = read_dac_toml(p)
        e = exps_back[0]
        assert e.exp_date_start == experiment.exp_date_start
        assert e.exp_date_end   == experiment.exp_date_end

    def test_experiment_floats_survive(self, tmp_path, dac, sample, experiment):
        p = tmp_path / "dac.toml"
        write_dac_toml(dac, p, samples=[sample], experiments=[experiment])
        _, _, _, exps_back = read_dac_toml(p)
        e = exps_back[0]
        assert e.exp_temperature    == pytest.approx(experiment.exp_temperature)
        assert e.exp_temperature_unc== pytest.approx(experiment.exp_temperature_unc)
        assert e.exp_pressure       == pytest.approx(experiment.exp_pressure)
        assert e.exp_pressure_unc   == pytest.approx(experiment.exp_pressure_unc)

    def test_nested_machine_in_experiment_survives(self, tmp_path, dac, sample, experiment, machine):
        p = tmp_path / "dac.toml"
        write_dac_toml(dac, p, machine=[machine], samples=[sample], experiments=[experiment])
        _, machine_back, _, _ = read_dac_toml(p)
        assert machine_back is not None
        assert machine_back[0].machine_name     == machine.machine_name
        assert machine_back[0].laser_wavelength == pytest.approx(machine.laser_wavelength)
        assert machine_back[0].spacing          == pytest.approx(machine.spacing)

    def test_dac_with_no_samples_or_experiments(self, tmp_path, dac):
        p = tmp_path / "dac_bare.toml"
        write_dac_toml(dac, p)
        dac_back, _, samples_back, exps_back = read_dac_toml(p)
        assert dac_back.dac_name == dac.dac_name
        assert samples_back      == []
        assert exps_back         == []

    def test_multiple_samples(self, tmp_path, dac, experiment):
        s1 = SampleParameters(sample_name="alpha", sample_structure="fcc")
        s2 = SampleParameters(sample_name="beta",  sample_structure="bcc")
        p  = tmp_path / "dac_multi.toml"
        write_dac_toml(dac, p, samples=[s1, s2], experiments=[experiment])
        _, _, samples_back, _ = read_dac_toml(p)
        assert len(samples_back) == 2
        assert samples_back[0].sample_name == "alpha"
        assert samples_back[1].sample_name == "beta"

    def test_multiple_experiments(self, tmp_path, dac, machine):
        e1 = ExperimentParameters(exp_name="run_001", exp_pressure=5.0,
                                  exp_machine_parameters=machine)
        e2 = ExperimentParameters(exp_name="run_002", exp_pressure=10.0,
                                  exp_machine_parameters=machine)
        p  = tmp_path / "dac_multi_exp.toml"
        write_dac_toml(dac, p, experiments=[e1, e2])
        _, _, _, exps_back = read_dac_toml(p)
        assert len(exps_back) == 2
        assert exps_back[0].exp_name == "run_001"
        assert exps_back[1].exp_name == "run_002"

    # New complex round-trip: 1 DAC, 2 machines, 3 samples, 2 experiments
    def test_complex_dac_multiple_machines_samples_experiments(self, tmp_path):
        # Create DAC
        dac = DACParameters(dac_name="dac_complex")

        # Two machines
        m1 = MachineParameters(machine_name="MACHINE-1")
        m2 = MachineParameters(machine_name="MACHINE-2")

        # Two experiments, each using one of the machines
        e1 = ExperimentParameters(exp_name="exp_A", exp_machine_parameters=m1)
        e2 = ExperimentParameters(exp_name="exp_B", exp_machine_parameters=m2)

        # Three samples; each sample did both experiments
        s1 = SampleParameters(sample_name="sample1", sample_experiments=[e1, e2])
        s2 = SampleParameters(sample_name="sample2", sample_experiments=[e1, e2])
        s3 = SampleParameters(sample_name="sample3", sample_experiments=[e1, e2])

        p = tmp_path / "dac_complex.toml"
        write_dac_toml(dac, p, machine=[m1, m2], samples=[s1, s2, s3], experiments=[e1, e2])

        dac_back, machines_back, samples_back, exps_back = read_dac_toml(p)

        # Machines preserved
        assert len(machines_back) == 2
        assert {m.machine_name for m in machines_back} == {m1.machine_name, m2.machine_name}

        # Experiments preserved and reference machine names
        assert len(exps_back) == 2
        names = {e.exp_name for e in exps_back}
        assert names == {e1.exp_name, e2.exp_name}
        # exp_machine_parameters stored as machine name reference
        assert exps_back[0].exp_machine_parameters in {m1.machine_name, m2.machine_name}

        # Samples preserved and back-linked to DAC, and each sample references both experiments
        assert len(samples_back) == 3
        for s in samples_back:
            assert s.sample_dac_parameters is dac_back
            assert s.sample_experiments is not None
            assert len(s.sample_experiments) == 2
            assert {e.exp_name for e in s.sample_experiments} == {e1.exp_name, e2.exp_name}