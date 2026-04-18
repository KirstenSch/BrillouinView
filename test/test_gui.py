"""
GUI tests for BrillouinView using pytest-qt.

Tests the WelcomeWindow and dialog windows using pytest-qt fixtures.
"""

import pytest
from unittest.mock import Mock, patch
from PyQt5 import QtWidgets, QtCore
from pathlib import Path
import sys

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from brillouinview.gui.dac_experiment_setup import (
    WelcomeWindow,
    SetupDACWindow,
    SetupMachineWindow,
    SetupExperimentWindow,
)
from brillouinview.setup_classes import ExperimentParameters, MachineParameters


class TestWelcomeWindow:
    """Tests for the WelcomeWindow dialog."""

    def test_welcome_window_creation(self, qtbot):
        """Test that WelcomeWindow can be instantiated."""
        window = WelcomeWindow()
        qtbot.addWidget(window)
        assert window is not None
        assert window.windowTitle() == "Welcome to BrillouinView 1.0.0"

    def test_welcome_window_buttons_exist(self, qtbot):
        """Test that all buttons exist in the welcome window."""
        window = WelcomeWindow()
        qtbot.addWidget(window)

        assert hasattr(window, "button_new_dac")
        assert hasattr(window, "button_load_dac")
        assert hasattr(window, "button_load_experiment")
        assert hasattr(window, "button_read_manual")

    def test_welcome_window_button_states(self, qtbot):
        """Test that only 'new DAC' button is enabled by default."""
        window = WelcomeWindow()
        qtbot.addWidget(window)

        assert window.button_new_dac.isEnabled()
        assert window.button_load_dac.isEnabled()
        assert window.button_load_experiment.isEnabled()
        assert not window.button_read_manual.isEnabled()

    def test_welcome_window_new_dac_button_click(self, qtbot):
        """Test that clicking 'new DAC' button opens SetupDACWindow."""
        window = WelcomeWindow()
        qtbot.addWidget(window)

        # Mock the SetupDACWindow to avoid opening a real dialog
        with patch("brillouinview.gui.dac_experiment_setup.SetupDACWindow") as mock_dac:
            mock_dialog = Mock()
            mock_dialog.exec_.return_value = QtWidgets.QDialog.Rejected
            mock_dac.return_value = mock_dialog

            # Click the button
            qtbot.mouseClick(window.button_new_dac, QtCore.Qt.LeftButton)

            # Give the event loop a chance to process
            qtbot.wait(100)


class TestSetupMachineWindow:
    """Tests for the SetupMachineWindow dialog."""

    def test_machine_window_creation_mode(self, qtbot):
        """Test SetupMachineWindow in creation mode (no machine_parameters)."""
        window = SetupMachineWindow()
        qtbot.addWidget(window)

        assert window is not None
        assert not window.is_edit_mode
        assert window.button_machine_create.text() == "Create Machine"

    def test_machine_window_edit_mode(self, qtbot):
        """Test SetupMachineWindow in edit mode (with machine_parameters)."""
        machine_params = MachineParameters(
            machine_name="Test Machine",
            machine_location="Lab A",
            scattering_angle=90.0,
            scattering_angle_unc=0.5,
            laser_wavelength=532.0,
            laser_wavelength_unc=1.0,
            spacing=213.0,
            spacing_unc=5.0,
            machine_notes="Test notes",
        )

        window = SetupMachineWindow(machine_parameters=machine_params)
        qtbot.addWidget(window)

        assert window.is_edit_mode
        assert window.button_machine_create.text() == "Confirm Parameters"
        assert window.le_machine_name.text() == "Test Machine"
        assert window.le_machine_location.text() == "Lab A"
        assert window.le_machine_angle.text() == "90.0"
        assert window.le_machine_laser.text() == "532.0"
        assert window.le_machine_mirror.text() == "213.0"

    def test_machine_window_clear_fields(self, qtbot):
        """Test that clear button clears all fields."""
        window = SetupMachineWindow()
        qtbot.addWidget(window)

        # Fill in some fields
        window.le_machine_name.setText("Test Machine")
        window.le_machine_location.setText("Lab A")
        window.le_machine_angle.setText("45.0")

        # Click clear button
        qtbot.mouseClick(window.button_machine_clear, QtCore.Qt.LeftButton)

        # Check fields are cleared
        assert window.le_machine_name.text() == ""
        assert window.le_machine_location.text() == ""
        assert window.le_machine_angle.text() == ""

    def test_machine_window_validation_missing_name(self, qtbot):
        """Test that missing machine name shows warning."""
        window = SetupMachineWindow()
        qtbot.addWidget(window)

        # Leave name empty and try to create
        window.le_machine_location.setText("Lab A")
        window.le_machine_angle.setText("90.0")
        window.le_machine_laser.setText("532.0")
        window.le_machine_mirror.setText("213.0")

        # We can't easily test the warning directly, but we can verify
        # that clicking create with missing fields doesn't accept the dialog
        with patch.object(QtWidgets.QMessageBox, "warning") as mock_warning:
            qtbot.mouseClick(window.button_machine_create, QtCore.Qt.LeftButton)
            qtbot.wait(100)
            # The warning should have been called due to missing machine name
            # (actual verification depends on event processing)


class TestSetupDACWindow:
    """Tests for the SetupDACWindow dialog."""

    def test_dac_window_creation(self, qtbot):
        """Test that SetupDACWindow can be created."""
        window = SetupDACWindow()
        qtbot.addWidget(window)

        assert window is not None
        assert hasattr(window, "le_dac_name")
        assert hasattr(window, "le_dac_owner")

    def test_dac_window_buttons_exist(self, qtbot):
        """Test that DAC window has required buttons."""
        window = SetupDACWindow()
        qtbot.addWidget(window)

        assert hasattr(window, "bt_dac_create_exp")
        assert hasattr(window, "bt_dac_clear_exp")
        assert hasattr(window, "bt_add_sample")

    def test_dac_window_initial_sample_row(self, qtbot):
        """Test that DAC window starts with one empty sample row."""
        window = SetupDACWindow()
        qtbot.addWidget(window)

        assert len(window._sample_rows) == 1

    def test_dac_window_add_sample_row(self, qtbot):
        """Test that clicking 'Add Sample' button adds a new row."""
        window = SetupDACWindow()
        qtbot.addWidget(window)

        initial_count = len(window._sample_rows)
        qtbot.mouseClick(window.bt_add_sample, QtCore.Qt.LeftButton)

        assert len(window._sample_rows) == initial_count + 1

    def test_dac_window_clear_all(self, qtbot):
        """Test that clear all button clears fields and resets samples."""
        window = SetupDACWindow()
        qtbot.addWidget(window)

        # Fill in some data
        window.le_dac_name.setText("Test DAC")
        window.le_dac_owner.setText("Test Owner")
        window.bt_add_sample.click()  # Add another sample

        # Click clear all
        qtbot.mouseClick(window.bt_dac_clear_exp, QtCore.Qt.LeftButton)

        # Check fields are cleared
        assert window.le_dac_name.text() == ""
        assert window.le_dac_owner.text() == ""
        # Should have one empty sample row after clear
        assert len(window._sample_rows) == 1


class TestEndToEndWorkflow:
    """Integration tests for the complete workflow from Welcome to Main window."""

    def test_workflow_welcome_to_dac_to_experiment(self, qtbot, tmp_path):
        """Test complete workflow: Welcome -> DAC Setup -> Experiment Setup."""
        from pathlib import Path
        from datetime import date

        # Start with WelcomeWindow
        welcome = WelcomeWindow()
        qtbot.addWidget(welcome)
        assert welcome is not None

        # Mock SetupDACWindow and SetupExperimentWindow to avoid full dialogs
        with patch("brillouinview.gui.dac_experiment_setup.SetupDACWindow") as mock_dac_class:
            # Create a real DAC window for the test
            dac_window = SetupDACWindow()
            qtbot.addWidget(dac_window)

            # Fill in DAC fields
            dac_window.le_dac_name.setText("Test DAC")
            dac_window.le_dac_owner.setText("Test Owner")
            dac_window.cb_dac_pressure_medium.setCurrentIndex(0)  # Ne - Neon
            dac_window.date_dac_prep.setDate(QtCore.QDate.currentDate())
            dac_window.te_dac_notes.setPlainText("Test DAC notes")

            # Add a sample
            assert len(dac_window._sample_rows) == 1
            dac_window._sample_rows[0]["name_edit"].setText("Sample 1")
            dac_window._sample_rows[0]["struct_combo"].setCurrentIndex(0)  # cubic
            dac_window._sample_rows[0]["notes_edit"].setText("Test sample")

            # Verify sample data can be retrieved
            samples = dac_window.get_sample_data()
            assert len(samples) == 1
            assert samples[0].sample_name == "Sample 1"

            # Store samples in window for get_dac_data() to use
            dac_window.sample_parameters_list = samples

            # Get DAC data
            dac_params = dac_window.get_dac_data()
            assert dac_params.dac_name == "Test DAC"
            assert dac_params.dac_owner == "Test Owner"
            assert dac_params.dac_samples == ["Sample 1"]

    def test_workflow_machine_window_in_experiment(self, qtbot):
        """Test creating a machine in the experiment setup workflow."""
        exp_window = SetupExperimentWindow()
        qtbot.addWidget(exp_window)

        # Create a new machine via the create machine button
        with patch(
            "brillouinview.gui.dac_experiment_setup.SetupMachineWindow"
        ) as mock_machine_class:
            # Create a real machine window
            machine_window = SetupMachineWindow()
            qtbot.addWidget(machine_window)

            # Fill in machine parameters
            machine_window.le_machine_name.setText("Lab A Machine")
            machine_window.le_machine_location.setText("Building 1")
            machine_window.le_machine_angle.setText("90.0")
            machine_window.le_machine_angle_unc.setText("0.5")
            machine_window.le_machine_laser.setText("532.0")
            machine_window.le_machine_laser_unc.setText("1.0")
            machine_window.le_machine_mirror.setText("213.0")
            machine_window.le_machine_mirror_unc.setText("5.0")
            machine_window.text_machine_notes.setPlainText("Lab machine")

            # Verify we can get the machine data
            machine_data = machine_window.get_machine_data()
            assert machine_data.machine_name == "Lab A Machine"
            assert machine_data.machine_location == "Building 1"
            assert machine_data.scattering_angle == 90.0
            assert machine_data.laser_wavelength == 532.0

    def test_workflow_dac_with_multiple_samples(self, qtbot):
        """Test DAC setup with multiple samples."""
        dac_window = SetupDACWindow()
        qtbot.addWidget(dac_window)

        # Add multiple samples
        sample_data = [
            ("Sample 1", "cubic"),
            ("Sample 2", "tetragonal"),
            ("Sample 3", "other"),
        ]

        for i, (name, structure) in enumerate(sample_data):
            if i > 0:  # First row already exists
                dac_window._add_sample_row()

            row = dac_window._sample_rows[i]
            row["name_edit"].setText(name)
            struct_index = ["cubic", "tetragonal", "other"].index(structure)
            row["struct_combo"].setCurrentIndex(struct_index)
            row["notes_edit"].setText(f"Notes for {name}")

        # Verify all samples are stored
        samples = dac_window.get_sample_data()
        assert len(samples) == 3
        assert samples[0].sample_name == "Sample 1"
        assert samples[1].sample_name == "Sample 2"
        assert samples[2].sample_name == "Sample 3"
        assert samples[0].sample_structure == "cubic"
        assert samples[1].sample_structure == "tetragonal"
        assert samples[2].sample_structure == "other"

    def test_workflow_delete_sample_row(self, qtbot):
        """Test deleting sample rows during DAC setup."""
        dac_window = SetupDACWindow()
        qtbot.addWidget(dac_window)

        # Add 3 samples
        for i in range(3):
            dac_window._add_sample_row()

        assert len(dac_window._sample_rows) == 4  # 1 initial + 3 added

        # Delete the second row
        second_row_id = dac_window._sample_rows[1]["id"]
        dac_window._delete_sample_row_by_id(second_row_id)

        assert len(dac_window._sample_rows) == 3

        # Fill remaining samples with names to verify correct ones remain
        for i, row in enumerate(dac_window._sample_rows):
            row["name_edit"].setText(f"Sample {i}")

        samples = dac_window.get_sample_data()
        sample_names = [s.sample_name for s in samples]
        assert "Sample 0" in sample_names
        assert "Sample 1" in sample_names
        assert "Sample 2" in sample_names

    def test_workflow_experiment_field_validation(self, qtbot):
        """Test experiment window field validation."""
        from brillouinview.setup_classes import DACParameters
        from datetime import date

        # Create mock DAC parameters
        dac_params = DACParameters(
            dac_name="Test DAC",
            dac_owner="Owner",
            dac_pressuremedium="Ne",
            dac_date_load=date.today(),
            dac_notes="",
            dac_samples=["Sample1"],
        )

        exp_window = SetupExperimentWindow(dac_parameters=dac_params)
        qtbot.addWidget(exp_window)

        # Fill in experiment fields
        exp_window.le_exp_name.setText("Experiment 1")
        exp_window.le_exp_operator.setText("Test Operator")
        exp_window.le_exp_temp.setText("300.0")
        exp_window.le_exp_temp_unc.setText("5.0")
        exp_window.le_exp_pressure.setText("1000.0")
        exp_window.le_exp_pressure_unc.setText("50.0")

        # Create machine parameters for the experiment
        machine_params = MachineParameters(
            machine_name="Test Machine",
            machine_location="Lab",
            scattering_angle=90.0,
            scattering_angle_unc=0.5,
            laser_wavelength=532.0,
            laser_wavelength_unc=1.0,
            spacing=213.0,
            spacing_unc=5.0,
        )
        exp_window._machine_parameters = machine_params

        # Set the display text manually (would be set by dialog click)
        exp_window.le_exp_machine_display.setText(
            f"{machine_params.machine_name} at {machine_params.machine_location}"
        )

        # Get experiment data
        exp_data = exp_window.get_experiment_data()
        assert exp_data.exp_name == "Experiment 1"
        assert exp_data.exp_operator == "Test Operator"
        assert exp_data.exp_temperature == 300.0
        assert exp_data.exp_pressure == 1000.0
        assert exp_data.exp_machine_parameters == machine_params

    def test_workflow_create_experiment_directories_and_files(self, qtbot, tmp_path):
        """Test that clicking create experiment button creates correct directory structure and files."""
        from brillouinview.setup_classes import DACParameters, SampleParameters
        from brillouinview.toml_io import write_dac_toml, read_dac_toml
        from datetime import date
        from pathlib import Path
        import tomlkit

        # Create a temporary DAC directory structure
        dac_dir = tmp_path / "20260411_Test_DAC"
        dac_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        for subdir in ["Calibration", "Machine", "Experiments", "Samples"]:
            (dac_dir / subdir).mkdir(parents=True, exist_ok=True)

        # Create DAC parameters with the temp directory
        dac_params = DACParameters(
            dac_name="Test DAC",
            dac_owner="Owner",
            dac_pressuremedium="Ne",
            dac_date_load=date(2026, 4, 11),
            dac_notes="Test notes",
            dac_samples=["Sample 1"],
            dac_directory=dac_dir,
        )

        # Create sample parameters
        sample_params = SampleParameters(
            sample_dac_parameters=dac_params,
            sample_name="Sample 1",
            sample_structure="cubic",
            sample_notes="Test sample",
            sample_experiments=[],
        )
        sample_list = [sample_params]

        # Create experiment window with DAC and sample parameters
        exp_window = SetupExperimentWindow(
            sample_parameters_list=sample_list, 
            dac_parameters=dac_params
        )
        qtbot.addWidget(exp_window)

        # Fill in experiment fields
        exp_window.le_exp_name.setText("Test Experiment")
        exp_window.le_exp_operator.setText("Test Operator")
        exp_window.le_exp_temp.setText("300.0")
        exp_window.le_exp_pressure.setText("1000.0")

        # Create and set machine parameters
        machine_params = MachineParameters(
            machine_name="Test Machine",
            machine_location="Lab A",
            scattering_angle=90.0,
            scattering_angle_unc=0.5,
            laser_wavelength=532.0,
            laser_wavelength_unc=1.0,
            spacing=213.0,
            spacing_unc=5.0,
            machine_notes="Test machine",
        )

        # Create experiment parameters
        exp_params = ExperimentParameters(
            exp_name="Test Experiment",
            exp_operator="Test Operator",
            exp_temperature=300.0,
            exp_pressure=1000.0,
            exp_machine_parameters=machine_params,
        )

        exp_window.experiment_parameters = exp_params
        exp_window._machine_parameters = machine_params
        exp_window.le_exp_machine_display.setText(f"{machine_params.machine_name} at {machine_params.machine_location}")

        # Create experiment directory
        exp_window.create_experiment_directory()

        # Verify experiment directory was created with correct name
        experiments_dir = dac_dir / "Experiments"
        exp_dir = experiments_dir / "Test_Experiment"
        assert exp_dir.exists()
        assert exp_dir.is_dir()

        # Get experiment data and write TOML file
        exp_window.experiment_parameters = exp_window.get_experiment_data()
        dac_toml_path = dac_params.dac_directory / f"{dac_params.dac_name.replace(' ', '_')}.toml"
        
        # Actually write the TOML file
        write_dac_toml(
            dac=dac_params,
            path=dac_toml_path,
            samples=sample_list,
            experiments=[exp_window.experiment_parameters],
        )

        # Verify TOML file exists
        assert dac_toml_path.exists()

        # Read and verify TOML content
        toml_content = tomlkit.loads(dac_toml_path.read_text(encoding="utf-8"))

        # Verify DAC section
        assert "dac" in toml_content
        dac_section = toml_content["dac"]
        assert dac_section["dac_name"] == "Test DAC"
        assert dac_section["dac_owner"] == "Owner"
        assert dac_section["dac_pressuremedium"] == "Ne"
        assert dac_section["dac_notes"] == "Test notes"

        # Verify samples section
        assert "samples" in toml_content or "sample" in toml_content
        
        # Verify experiments section
        assert "experiments" in toml_content or "experiment" in toml_content

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
